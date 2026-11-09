#!/usr/bin/env python3
"""Tune the camera filter layer on real frames (no ROS needed).

  live, both cameras (stop the ROS camera node first, only one program can open a camera):
      python3 scripts/filter_preview.py --left /dev/cam_left --right /dev/cam_right --params config/slam_params.yaml
  saved images (e.g. from capture_pairs.py):
      python3 scripts/filter_preview.py --image left.png [--image2 right.png] --params config/slam_params.yaml
Shows raw | filtered side by side (top = left camera, bottom = right camera if given), with sliders (drawn by the script, so they show on any desktop theme).
--params   start from the `image_filter:` section of that yaml (otherwise the defaults in image_filter.py).
--save OUT.png   headless: write one comparison image and exit (no display needed).
--ros       take frames from ROS topics instead of a camera (run this on the LAPTOP; needs ROS 2 sourced and the same
            ROS_DOMAIN_ID as the robot). Defaults: /stereo/left/image_raw and /stereo/right/image_raw; change with
            --topic-left / --topic-right. IMPORTANT: set `enable: false` under image_filter: on the robot while tuning,
            otherwise image_raw is already filtered and you would be filtering twice.
--scale X   shrink the preview window (default 0.7; try 0.5 on a small screen). Sliders are in their own small
            'controls' window that you can drag anywhere, so a tall image no longer hides them.
--one-eye   show only the left camera (halves the window height).
Keys: 'd' toggles a DIFF view (third panel = what the despeckle step changed, amplified x8, plus % of pixels it touched),
      'n' toggles synthetic salt-and-pepper speckle on the input so you can watch it being removed,
      'p' prints the current values as an `image_filter:` block to paste into config/slam_params.yaml, 'q' quits.

The script prints which image_filter.py it loaded. It imports from the folder it lives in (../goosebot_hw), NOT from
the colcon-installed package, so a stale copy there is the first thing to check if the picture looks wrong.
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import goosebot_hw.image_filter as imgf  # noqa: E402
from goosebot_hw.image_filter import FilterParams, ImageFilter, load_filter_yaml  # noqa: E402


def grab(cap):
    ok, f = cap.read()
    if not ok:
        raise SystemExit('camera read failed')
    return cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)


def open_cam(dev, w, h):
    cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    if not cap.isOpened():
        raise SystemExit(f'cannot open {dev}')
    return cap


def ros_sources(topic_l, topic_r):
    """Subscribe (best-effort QoS, like the camera node) and return one 'latest gray frame' callable per topic."""
    import threading
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image

    rclpy.init()
    node = rclpy.create_node('filter_preview')
    latest = {}

    def decode(m):
        buf = np.frombuffer(m.data, np.uint8)
        if m.encoding == 'mono8':
            return buf.reshape(m.height, m.step)[:, :m.width].copy()
        if m.encoding in ('bgr8', 'rgb8'):
            im = buf.reshape(m.height, m.step // 3, 3)[:, :m.width]
            return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY if m.encoding == 'bgr8' else cv2.COLOR_RGB2GRAY)
        raise SystemExit(f'unsupported image encoding {m.encoding!r}')

    def sub(topic):
        node.create_subscription(Image, topic, lambda m, t=topic: latest.__setitem__(t, decode(m)),
                                 qos_profile_sensor_data)

    topics = [topic_l] + ([topic_r] if topic_r else [])
    for t in topics:
        sub(t)
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    def getter(t):
        def get():
            t0 = time.time()
            while t not in latest:
                if time.time() - t0 > 10:
                    raise SystemExit(f'no images on {t} after 10 s (check ROS_DOMAIN_ID, `ros2 topic hz {t}`)')
                time.sleep(0.05)
            return latest[t]
        return get
    return [getter(t) for t in topics]


class ControlPanel:
    """Self-drawn sliders (OpenCV only, no Qt widgets), so labels and values always show whatever the desktop theme.
    Click or drag on a bar to set a value."""
    W, ROW, X0, X1 = 640, 26, 215, 500

    def __init__(self, p):
        self.p = p
        self.drag = None
        P = p
        pct = lambda v: f'{v:.2f}'
        self.rows = [
            # label, lo, hi, step, get, set, format
            ('median 0=off / 3 / 5', 0, 5, 1, lambda: P.median_ksize if P.despeckle == 'median' else 0,
             lambda v: (setattr(P, 'despeckle', 'median' if v >= 3 else 'off'), setattr(P, 'median_ksize', max(int(v), 3) | 1)),
             lambda v: 'off' if v < 3 else str(int(v) | 1)),
            ('glare removal', 0, 1, 1, lambda: int(P.highlight), lambda v: setattr(P, 'highlight', bool(v)),
             lambda v: 'on' if v else 'off'),
            ('glare threshold', 0, 255, 1, lambda: P.highlight_thresh, lambda v: setattr(P, 'highlight_thresh', int(v)), str),
            ('glare min area px', 0, 200, 1, lambda: P.highlight_min_area, lambda v: setattr(P, 'highlight_min_area', int(v)), str),
            ('shadow correction', 0, 1, 1, lambda: int(P.local_norm), lambda v: setattr(P, 'local_norm', bool(v)),
             lambda v: 'on' if v else 'off'),
            ('mode 0=divide 1=full', 0, 1, 1, lambda: int(P.norm_mode == 'full'),
             lambda v: setattr(P, 'norm_mode', 'full' if v else 'divide'), lambda v: 'full' if v else 'divide'),
            ('strength', 0.0, 1.0, 0.05, lambda: P.norm_strength, lambda v: setattr(P, 'norm_strength', float(v)), pct),
            ('clamp', 1.0, 4.0, 0.1, lambda: P.norm_clamp, lambda v: setattr(P, 'norm_clamp', float(v)),
             lambda v: f'{v:.1f}'),
            ('sigma px', 3, 80, 1, lambda: P.norm_sigma, lambda v: setattr(P, 'norm_sigma', float(v)),
             lambda v: f'{v:.0f}'),
            ('full mode: gain', 0.0, 0.6, 0.01, lambda: P.norm_gain, lambda v: setattr(P, 'norm_gain', float(v)), pct),
            ('full mode: min std', 0, 40, 1, lambda: P.norm_min_std, lambda v: setattr(P, 'norm_min_std', float(v)),
             lambda v: f'{v:.0f}'),
        ]
        self.H = self.ROW * len(self.rows) + 36

    def draw(self):
        img = np.full((self.H, self.W, 3), 45, np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, 'click / drag a bar to change a value', (10, 18), font, 0.45, (170, 170, 170), 1, cv2.LINE_AA)
        for i, (label, lo, hi, step, get, _set, fmt) in enumerate(self.rows):
            y = 36 + i * self.ROW
            v = min(max(get(), lo), hi)
            frac = (v - lo) / (hi - lo)
            xh = int(self.X0 + frac * (self.X1 - self.X0))
            cv2.putText(img, label, (10, y + 5), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(img, (self.X0, y), (self.X1, y), (110, 110, 110), 3)
            cv2.line(img, (self.X0, y), (xh, y), (235, 160, 40), 3)
            cv2.circle(img, (xh, y), 8, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.putText(img, str(fmt(v)), (self.X1 + 22, y + 5), font, 0.5, (120, 220, 255), 1, cv2.LINE_AA)
        return img

    def _apply(self, i, x):
        label, lo, hi, step, _get, set_, _fmt = self.rows[i]
        frac = min(max((x - self.X0) / (self.X1 - self.X0), 0.0), 1.0)
        v = lo + round(frac * (hi - lo) / step) * step
        set_(round(v, 6))

    def mouse(self, event, x, y, flags, _param=None):
        row = int((y - 36 + self.ROW / 2) // self.ROW)
        if event == cv2.EVENT_LBUTTONDOWN and 0 <= row < len(self.rows) and x >= self.X0 - 15:
            self.drag = row
            self._apply(row, x)
        elif event == cv2.EVENT_MOUSEMOVE and self.drag is not None and flags & cv2.EVENT_FLAG_LBUTTON:
            self._apply(self.drag, x)
        elif event == cv2.EVENT_LBUTTONUP:
            self.drag = None


def add_speckle(g, frac=0.01):
    """Synthetic salt-and-pepper noise: `frac` of the pixels set to 0 or 255 (random each call)."""
    r = np.random.random(g.shape)
    out = g.copy()
    out[r < frac / 2] = 0
    out[r > 1 - frac / 2] = 255
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--left'); ap.add_argument('--right')
    ap.add_argument('--image'); ap.add_argument('--image2')
    ap.add_argument('--params', help='yaml with an image_filter: section (config/slam_params.yaml)')
    ap.add_argument('--width', type=int, default=640); ap.add_argument('--height', type=int, default=480)
    ap.add_argument('--save')
    ap.add_argument('--diff', action='store_true', help='start with the despeckle diff panel on')
    ap.add_argument('--add-noise', action='store_true', help='start with synthetic speckle added to the input')
    ap.add_argument('--ros', action='store_true', help='read frames from ROS topics (run on the laptop)')
    ap.add_argument('--topic-left', default='/stereo/left/image_raw')
    ap.add_argument('--topic-right', default='/stereo/right/image_raw')
    ap.add_argument('--scale', type=float, default=0.7, help='display scale of the preview window')
    ap.add_argument('--one-eye', action='store_true', help='show only the left camera')
    a = ap.parse_args()

    kw, enable, log_period = ({}, True, 10.0)
    if a.params:
        kw, enable, log_period = load_filter_yaml(a.params)
    p = FilterParams(**kw)
    filt = ImageFilter(p)
    print('image_filter.py loaded from:', imgf.__file__)
    print('settings:', p.describe())
    if not enable:
        print('NOTE: yaml has enable: false (the robot would run unfiltered); preview still shows the filter.')

    if a.image:
        srcs = [lambda im=cv2.imread(a.image, cv2.IMREAD_GRAYSCALE): im]
        if a.image2:
            srcs.append(lambda im=cv2.imread(a.image2, cv2.IMREAD_GRAYSCALE): im)
    elif a.ros:
        srcs = ros_sources(a.topic_left, a.topic_right)
    elif a.left:
        caps = [open_cam(a.left, a.width, a.height)]
        if a.right:
            caps.append(open_cam(a.right, a.width, a.height))
        srcs = [lambda c=c: grab(c) for c in caps]
    else:
        ap.error('give --image, --ros or --left')

    if a.one_eye:
        srcs = srcs[:1]

    view = {'diff': a.diff, 'noise': a.add_noise}

    def render():
        rows = []
        touched = []
        t = time.perf_counter()
        for s in srcs:
            g = s()
            if view['noise']:
                g = add_speckle(g)
            out = filt(g)
            if view['diff']:
                d = cv2.absdiff(g, filt.despeckle(g))
                touched.append((d > 0).mean() * 100)
                rows.append(np.hstack([g, out, np.clip(d.astype(np.int32) * 8, 0, 255).astype(np.uint8)]))
            else:
                rows.append(np.hstack([g, out]))
        ms = (time.perf_counter() - t) * 1000 / len(srcs)
        img = np.vstack(rows)
        txt = f'{ms:.1f} ms/eye  glare {filt.last_glare_frac * 100:.1f}%  norm {p.norm_mode if p.local_norm else "off"}'
        if view['diff']:
            txt += f'  despeckle touched {np.mean(touched):.1f}% px (panel 3 = change x8)'
        if view['noise']:
            txt += '  [fake speckle ON]'
        cv2.putText(img, txt, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 255, 1)
        return img

    if a.save:
        cv2.imwrite(a.save, render())
        print('wrote', a.save)
        return

    win = 'raw | filtered'
    ctl = 'controls'
    gui_normal = getattr(cv2, 'WINDOW_GUI_NORMAL', 0x10)       # Qt: no toolbar / status bar
    cv2.namedWindow(win, cv2.WINDOW_NORMAL | gui_normal)
    cv2.namedWindow(ctl, cv2.WINDOW_NORMAL | gui_normal)
    panel = ControlPanel(p)
    cv2.setMouseCallback(ctl, panel.mouse)
    cv2.resizeWindow(ctl, panel.W, panel.H)
    first = True
    while True:
        img = render()
        if a.scale != 1.0:
            img = cv2.resize(img, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_AREA)
        cv2.imshow(win, img)
        cv2.imshow(ctl, panel.draw())
        if first:
            cv2.resizeWindow(win, img.shape[1], img.shape[0])
            cv2.moveWindow(ctl, 20, 20)
            cv2.moveWindow(win, 500, 20)
            first = False
        k = cv2.waitKey(30) & 0xFF
        if k == ord('q'):
            break
        if k == ord('d'):
            view['diff'] = not view['diff']
            first = True
        if k == ord('n'):
            view['noise'] = not view['noise']
        if k == ord('p'):
            print('image_filter:')
            print(f'  enable: {str(enable).lower()}')
            print(f'  log_period_s: {log_period}')
            for f, v in vars(p).items():
                print(f'  {f}: {str(v).lower() if isinstance(v, bool) else v}')


if __name__ == '__main__':
    main()
