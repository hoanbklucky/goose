"""
Per-camera image filter layer (no ROS imports, so it can be unit-tested and previewed on saved frames).

Pipeline, all on the gray (mono8) frame, in this order:
  1. despeckle   - removes salt-and-pepper / sensor speckle      (median, or edge-preserving bilateral)
  2. highlights  - finds specular reflections (glare) and flattens them so they stop producing fake features
  3. shadow corr - gentle local illumination correction: divides by a smoothed brightness map (factor clamped,
                   blended with the original) so shadows / uneven light are reduced WITHOUT amplifying noise.
                   norm_mode 'full' (mean/std normalisation) is kept but is aggressive: it amplified wall noise
                   and put halos around dark objects on real frames.

Design rules for a STEREO pair:
  * The SAME parameters are applied to left and right. Different filtering per eye shifts features and
    corrupts disparity.
  * Everything here is local/pixel-wise (no per-frame random choices), so a point seen by both cameras gets
    about the same output value. Global histogram equalisation is deliberately NOT used.
  * Filtering happens BEFORE rectification, so keep kernels small.
  * CPU only; the chain costs roughly 10 ms per 640x480 frame on a desktop CPU (measure on the Rock 5C).
"""
import cv2
import numpy as np


class FilterParams:
    def __init__(self, **kw):
        # --- 1. speckle ---
        self.despeckle = 'median'        # 'off' | 'median' | 'bilateral'
        self.median_ksize = 3            # odd: 3 or 5
        self.bilateral_d = 5
        self.bilateral_sigma_color = 25.0
        self.bilateral_sigma_space = 3.0
        # --- 2. reflections / glare ---
        self.highlight = True
        self.highlight_thresh = 235      # pixels at/above this (0..255) are glare candidates
        self.highlight_min_area = 12     # px; ignore smaller blobs (single hot pixels are speckle, not glare)
        self.highlight_grow = 5          # px kernel to grow the mask, to also cover the glare's soft halo
        self.highlight_fill = 'local'    # 'local' = fill with the surrounding local mean, 'inpaint' = cv2.inpaint (slow)
        # --- 3. shadow / uneven-light correction ---
        self.local_norm = True
        self.norm_mode = 'divide'        # 'divide' = gentle (default); 'full' = mean/std normalisation (aggressive)
        self.norm_strength = 0.5         # 0..1 blend of the corrected image into the original (0 = off)
        self.norm_clamp = 1.6            # correction factor limited to [1/clamp, clamp]
        self.norm_sigma = 25.0           # px. Scale of "illumination"; keep >> texture size (3-8 px)
        self.norm_downscale = 4          # illumination is smooth: estimate at 1/N resolution (big speed-up)
        # only used when norm_mode == 'full'
        self.norm_contrast = True
        self.norm_gain = 0.25
        self.norm_min_std = 20.0
        for k, v in kw.items():
            if not hasattr(self, k):
                raise KeyError(f'unknown filter parameter: {k}')
            setattr(self, k, v)

    def describe(self):
        return ', '.join(f'{k}={v}' for k, v in vars(self).items())

    @classmethod
    def from_node(cls, node, prefix='filter.'):
        """Read every field from ROS parameters named '<prefix><field>' (declares them with defaults).
        dynamic_typing lets a yaml write `norm_sigma: 20` (int) for a float setting without crashing the node."""
        from rcl_interfaces.msg import ParameterDescriptor
        desc = ParameterDescriptor(dynamic_typing=True)
        p = cls()
        for k, default in list(vars(p).items()):
            v = node.declare_parameter(prefix + k, default, desc).value
            setattr(p, k, str(v) if isinstance(default, str) else type(default)(v))
        return p


def _odd(n):
    n = int(n)
    return n if n % 2 == 1 else n + 1


class ImageFilter:
    def __init__(self, params=None):
        self.p = params or FilterParams()
        self.last_glare_frac = 0.0        # fraction of pixels flagged as glare in the last frame (for logging)

    # ---------- stage 1 ----------
    def despeckle(self, g):
        p = self.p
        if p.despeckle == 'median':
            return cv2.medianBlur(g, _odd(p.median_ksize))
        if p.despeckle == 'bilateral':
            return cv2.bilateralFilter(g, int(p.bilateral_d), p.bilateral_sigma_color, p.bilateral_sigma_space)
        return g

    # ---------- stage 2 ----------
    def glare_mask(self, g):
        p = self.p
        m = (g >= p.highlight_thresh).astype(np.uint8)
        if not m.any():
            return None
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        if n <= 1:
            return None
        keep = np.zeros(n, np.uint8)
        keep[1:] = (stats[1:, cv2.CC_STAT_AREA] >= p.highlight_min_area).astype(np.uint8)
        m = keep[lab]
        if not m.any():
            return None
        k = _odd(p.highlight_grow)
        return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))

    def fix_highlights(self, g):
        m = self.glare_mask(g)
        if m is None:
            self.last_glare_frac = 0.0
            return g
        self.last_glare_frac = float(m.mean())
        if self.p.highlight_fill == 'inpaint':
            return cv2.inpaint(g, m, 3, cv2.INPAINT_TELEA)
        ok = (1 - m).astype(np.float32)
        gf = g.astype(np.float32)
        num = self._smooth(gf * ok)
        den = self._smooth(ok)
        fill = num / np.maximum(den, 1e-3)
        out = np.where(m.astype(bool), fill, gf)
        return np.clip(out, 0, 255).astype(np.uint8)

    # ---------- stage 3 ----------
    def _smooth(self, f):
        """Gaussian blur of sigma norm_sigma, computed at reduced resolution then upsampled."""
        p = self.p
        n = max(int(p.norm_downscale), 1)
        if n == 1:
            return cv2.GaussianBlur(f, (0, 0), p.norm_sigma)
        h, w = f.shape
        small = cv2.resize(f, (w // n, h // n), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), p.norm_sigma / n)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

    def illumination_correct(self, g):
        """Gentle shadow / uneven-light correction: out = g * (global_level / local_illumination), factor
        clamped to [1/norm_clamp, norm_clamp] and blended with the original by norm_strength."""
        p = self.p
        f = g.astype(np.float32)
        L = np.maximum(self._smooth(f), 8.0)
        target = float(np.median(L[::8, ::8]))
        factor = np.clip(target / L, 1.0 / p.norm_clamp, p.norm_clamp)
        out = (1.0 - p.norm_strength) * f + p.norm_strength * (f * factor)
        return np.clip(out, 0, 255).astype(np.uint8)

    def local_normalise(self, g):
        p = self.p
        if p.norm_mode != 'full':
            return self.illumination_correct(g)
        f = g.astype(np.float32)
        mean = self._smooth(f)
        d = f - mean
        if p.norm_contrast:
            var = self._smooth(d * d)
            std = np.maximum(np.sqrt(var), p.norm_min_std)
            out = 128.0 + p.norm_gain * 255.0 * d / std
        else:
            out = 128.0 + d
        return np.clip(out, 0, 255).astype(np.uint8)

    def __call__(self, gray):
        g = self.despeckle(gray)
        if self.p.highlight:
            g = self.fix_highlights(g)
        if self.p.local_norm:
            g = self.local_normalise(g)
        return g


def load_filter_yaml(path, section='image_filter'):
    """Read the `image_filter:` section of slam_params.yaml. Returns (FilterParams kwargs, enable, log_period_s).
    Unknown keys raise, so a typo cannot silently do nothing."""
    import yaml
    with open(path) as f:
        sec = dict((yaml.safe_load(f) or {}).get(section, {}) or {})
    enable = bool(sec.pop('enable', True))
    log_period = float(sec.pop('log_period_s', 10.0))
    FilterParams(**sec)            # validates names
    return sec, enable, log_period
