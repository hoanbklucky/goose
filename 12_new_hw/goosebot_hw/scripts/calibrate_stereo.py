#!/usr/bin/env python3
"""Step 2: stereo calibration (the learnopencv method) -> ROS camera_info files.

  1. calibrate each camera on its own          (cv2.calibrateCamera)
  2. find how the cameras sit relative to each other with the single-camera
     numbers held fixed                         (cv2.stereoCalibrate, FIX_INTRINSIC)
  3. compute the rectification                  (cv2.stereoRectify)
  4. write left_camera.yaml / right_camera.yaml for ROS / RTAB-Map
Runs anywhere, no cameras or display needed.
"""
import argparse
import glob
import os

import cv2
import numpy as np


def align_order(cl, cr):
    """Make the right camera count corners from the same end as the left one.
    An even x even board looks identical upside down, so OpenCV can number the
    corners from opposite ends in the two cameras. Returns (cr, was_flipped)."""
    same = np.mean(np.linalg.norm(cl - cr, axis=2))
    flip = np.mean(np.linalg.norm(cl - cr[::-1], axis=2))
    if flip < same:
        return cr[::-1].copy(), True
    return cr, False


def find_corners(dirL, dirR, size, square):
    cols, rows = size
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square   # METERS
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    filesL = sorted(glob.glob(os.path.join(dirL, '*.png')))
    filesR = sorted(glob.glob(os.path.join(dirR, '*.png')))
    if not filesL or len(filesL) != len(filesR):
        raise SystemExit(f'Need equal, non-zero image counts: {len(filesL)} left, {len(filesR)} right')
    obj, ptsL, ptsR, names, img_size = [], [], [], [], None
    n_flipped = 0
    for fl, fr in zip(filesL, filesR):
        gl = cv2.imread(fl, cv2.IMREAD_GRAYSCALE)
        gr = cv2.imread(fr, cv2.IMREAD_GRAYSCALE)
        img_size = gl.shape[::-1]                 # (width, height)
        okl, cl = cv2.findChessboardCorners(gl, size, flags)
        okr, cr = cv2.findChessboardCorners(gr, size, flags)
        if not (okl and okr):
            print(f'  skipped (board not found in both): {os.path.basename(fl)}')
            continue
        cl = cv2.cornerSubPix(gl, cl, (11, 11), (-1, -1), crit)
        cr = cv2.cornerSubPix(gr, cr, (11, 11), (-1, -1), crit)
        cr, flipped = align_order(cl, cr)
        n_flipped += flipped
        obj.append(objp); ptsL.append(cl); ptsR.append(cr)
        names.append(os.path.basename(fl))
    if n_flipped:
        print(f'  fixed corner order in {n_flipped} pair(s) (even x even board)')
    return obj, ptsL, ptsR, img_size, names


def run_calibration(obj, ptsL, ptsR, img_size):
    rmsL, K1, D1, _, _ = cv2.calibrateCamera(obj, ptsL, img_size, None, None)
    rmsR, K2, D2, _, _ = cv2.calibrateCamera(obj, ptsR, img_size, None, None)
    crit = (cv2.TERM_CRITERIA_MAX_ITER + cv2.TERM_CRITERIA_EPS, 100, 1e-6)
    rmsS, K1, D1, K2, D2, R, T, _, _ = cv2.stereoCalibrate(
        obj, ptsL, ptsR, K1, D1, K2, D2, img_size,
        flags=cv2.CALIB_FIX_INTRINSIC, criteria=crit)
    # alpha=0: crop to valid pixels, so no black borders confuse the SLAM
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
        K1, D1, K2, D2, img_size, R, T, alpha=0)
    return dict(rmsL=rmsL, rmsR=rmsR, rmsS=rmsS, K1=K1, D1=D1, K2=K2, D2=D2,
                R=R, T=T, R1=R1, R2=R2, P1=P1, P2=P2, Q=Q, size=img_size)


def epipolar_errors(c, ptsL, ptsR):
    """How far apart (in rows) matching points are after rectifying. Want ~0."""
    out = []
    for l, r in zip(ptsL, ptsR):
        ul = cv2.undistortPoints(l, c['K1'], c['D1'], R=c['R1'], P=c['P1']).reshape(-1, 2)
        ur = cv2.undistortPoints(r, c['K2'], c['D2'], R=c['R2'], P=c['P2']).reshape(-1, 2)
        out.append(float(np.mean(np.abs(ul[:, 1] - ur[:, 1]))))
    return out


def _mat(name, m, indent='  '):
    m = np.asarray(m, float)
    data = ', '.join(f'{v:.10g}' for v in m.flatten())
    return (f'{name}:\n{indent}rows: {m.shape[0]}\n{indent}cols: {m.shape[1]}\n'
            f'{indent}data: [{data}]\n')


def write_yaml(path, cam_name, size, K, D, R, P):
    with open(path, 'w') as f:
        f.write(f'image_width: {size[0]}\nimage_height: {size[1]}\n'
                f'camera_name: {cam_name}\n')
        f.write(_mat('camera_matrix', K))
        f.write('distortion_model: plumb_bob\n')
        f.write(_mat('distortion_coefficients', np.asarray(D).reshape(1, -1)))
        f.write(_mat('rectification_matrix', R))
        f.write(_mat('projection_matrix', P))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pairs', default='pairs')
    ap.add_argument('--size', default='8x6', help='INNER corners')
    ap.add_argument('--square', type=float, required=True,
                    help='square size in METERS (measure it with a ruler)')
    ap.add_argument('--baseline', type=float, default=None,
                    help='ruler-measured camera spacing in m, for a sanity check')
    ap.add_argument('--ros-out', default=os.path.expanduser('~/.ros/camera_info'))
    a = ap.parse_args()

    cols, rows = (int(v) for v in a.size.lower().split('x'))
    print('Finding corners...')
    obj, ptsL, ptsR, size, names = find_corners(
        f'{a.pairs}/left', f'{a.pairs}/right', (cols, rows), a.square)
    print(f'Using {len(obj)} usable pairs (image size {size[0]}x{size[1]})')
    if len(obj) < 15:
        print('WARNING: fewer than 15 pairs. Collect more for a trustworthy result.')

    c = run_calibration(obj, ptsL, ptsR, size)
    errs = epipolar_errors(c, ptsL, ptsR)

    # One round of clean-up: drop pairs far worse than the typical pair, redo.
    limit = max(1.0, 3 * float(np.median(errs)))
    keep = [i for i, e in enumerate(errs) if e <= limit]
    if len(keep) < len(errs) and len(keep) >= 15:
        for i in range(len(errs)):
            if i not in keep:
                print(f'  rejected {names[i]} (row mismatch {errs[i]:.2f} px)')
        obj = [obj[i] for i in keep]
        ptsL = [ptsL[i] for i in keep]
        ptsR = [ptsR[i] for i in keep]
        names = [names[i] for i in keep]
        c = run_calibration(obj, ptsL, ptsR, size)
        errs = epipolar_errors(c, ptsL, ptsR)
        print(f'Re-calibrated with {len(obj)} pairs')
    baseline = float(np.linalg.norm(c['T']))

    print('\n--- Results ---')
    print(f"Left camera RMS error : {c['rmsL']:.3f} px")
    print(f"Right camera RMS error: {c['rmsR']:.3f} px")
    print(f"Stereo RMS error      : {c['rmsS']:.3f} px   (good: < 0.5, OK for cheap cams: < 1.0)")
    print(f"Row mismatch after rectifying: mean {np.mean(errs):.3f} px (want < 0.3)")
    worst = sorted(zip(errs, names), reverse=True)[:3]
    print('Worst pairs (delete these and re-run if the numbers are bad): '
          + ', '.join(f'{n} ({e:.2f})' for e, n in worst))
    print(f"Baseline: {baseline * 100:.2f} cm")
    if a.baseline:
        off = abs(baseline - a.baseline) / a.baseline * 100
        print(f"  ruler says {a.baseline * 100:.1f} cm -> off by {off:.1f}% "
              f"({'OK' if off < 5 else 'CHECK: wrong --square value or bad calibration'})")
    if c['T'][0, 0] > 0:
        print('WARNING: right camera appears to be on the LEFT. '
              'Swap the two USB cables (or the udev names) and recalibrate.')
    else:
        print('Left/right order looks correct.')
    print(f"Focal length: left {c['K1'][0, 0]:.1f} px, right {c['K2'][0, 0]:.1f} px")

    os.makedirs(a.ros_out, exist_ok=True)
    for cam, K, D, R, P in (('left_camera', c['K1'], c['D1'], c['R1'], c['P1']),
                            ('right_camera', c['K2'], c['D2'], c['R2'], c['P2'])):
        p = os.path.join(a.ros_out, f'{cam}.yaml')
        write_yaml(p, cam, size, K, D, R, P)
        print('Wrote', p)
    np.savez(os.path.join(a.pairs, 'stereo_calibration.npz'),
             **{k: v for k, v in c.items() if k != 'size'}, size=np.array(size))
    print('Also saved', os.path.join(a.pairs, 'stereo_calibration.npz'))


if __name__ == '__main__':
    main()
