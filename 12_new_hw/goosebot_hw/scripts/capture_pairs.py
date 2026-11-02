#!/usr/bin/env python3
"""Step 1: capture checkerboard photo pairs from the two cameras.

A pair is saved automatically only when
  - BOTH cameras see the whole board,
  - the board is holding still (cheap USB cameras are not synchronized,
    so a still board is what makes the left/right photos match), and
  - the board is somewhere new compared with the last saved pair.
Works with a preview window (desktop) or without one (SSH / headless).
Stop the ROS camera nodes first: only one program can open a camera.
"""
import argparse
import os
import time

import cv2
import numpy as np


def open_cam(dev, w, h, fps):
    cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)          # focus must not drift
    if not cap.isOpened():
        raise SystemExit(f'Cannot open {dev}. Are the ROS camera nodes still running?')
    return cap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--left', default='/dev/cam_left')
    ap.add_argument('--right', default='/dev/cam_right')
    ap.add_argument('--size', default='8x6', help='INNER corners, e.g. 8x6')
    ap.add_argument('--width', type=int, default=640)
    ap.add_argument('--height', type=int, default=480)
    ap.add_argument('--fps', type=float, default=15)
    ap.add_argument('--count', type=int, default=35, help='pairs to collect')
    ap.add_argument('--out', default='pairs')
    ap.add_argument('--still-px', type=float, default=1.0,
                    help='max corner motion between frames to count as still')
    ap.add_argument('--new-px', type=float, default=30.0,
                    help='min corner shift vs last saved pair to count as new')
    a = ap.parse_args()

    cols, rows = (int(v) for v in a.size.lower().split('x'))
    size = (cols, rows)
    os.makedirs(f'{a.out}/left', exist_ok=True)
    os.makedirs(f'{a.out}/right', exist_ok=True)
    n = len(os.listdir(f'{a.out}/left'))        # continue numbering if re-run

    capL = open_cam(a.left, a.width, a.height, a.fps)
    capR = open_cam(a.right, a.width, a.height, a.fps)
    show = bool(os.environ.get('DISPLAY'))
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE

    prev = None            # corners (L) from previous frame
    last_saved = None      # corners (L) of last saved pair
    last_save_t = 0.0
    last_msg = ''
    print(f'Collecting {a.count} pairs into {a.out}/ ... (q or Ctrl+C to stop)')

    try:
        while n < a.count:
            # grab both first, decode after: keeps the two frames close in time
            if not (capL.grab() and capR.grab()):
                continue
            okL, fL = capL.retrieve()
            okR, fR = capR.retrieve()
            if not (okL and okR):
                continue
            gL = cv2.cvtColor(fL, cv2.COLOR_BGR2GRAY)
            gR = cv2.cvtColor(fR, cv2.COLOR_BGR2GRAY)
            fo_L, cL = cv2.findChessboardCorners(gL, size, flags)
            fo_R, cR = cv2.findChessboardCorners(gR, size, flags)

            if not fo_L or not fo_R:
                msg = 'board not fully visible in ' + (
                    'both' if not fo_L and not fo_R else 'left' if not fo_L else 'right')
                prev = None
            else:
                still = prev is not None and np.mean(np.linalg.norm(cL - prev, axis=2)) < a.still_px
                prev = cL
                is_new = last_saved is None or np.mean(
                    np.linalg.norm(cL - last_saved, axis=2)) > a.new_px
                if not still:
                    msg = 'hold the board still...'
                elif not is_new:
                    msg = 'same spot as last pair: move/tilt the board'
                elif time.time() - last_save_t < 1.0:
                    msg = 'wait...'
                else:
                    cv2.imwrite(f'{a.out}/left/left_{n:02d}.png', fL)
                    cv2.imwrite(f'{a.out}/right/right_{n:02d}.png', fR)
                    last_saved, last_save_t = cL.copy(), time.time()
                    n += 1
                    msg = f'SAVED pair {n}/{a.count}'

            if msg != last_msg:
                print(msg)
                last_msg = msg
            if show:
                vL, vR = fL.copy(), fR.copy()
                if fo_L:
                    cv2.drawChessboardCorners(vL, size, cL, True)
                if fo_R:
                    cv2.drawChessboardCorners(vR, size, cR, True)
                view = np.hstack([vL, vR])
                cv2.putText(view, f'{n}/{a.count}  {msg}', (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('left | right', view)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        capL.release()
        capR.release()
        cv2.destroyAllWindows()
    print(f'Done: {n} pairs in {a.out}/')


if __name__ == '__main__':
    main()
