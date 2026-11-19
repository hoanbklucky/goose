#!/usr/bin/env python3
"""
Wheel encoder bench check and calibration (README "Wheel encoders"). No ROS needed. Stop bringup first: only one
program can hold the GPIO lines (encoder_node would make this fail with "Device or resource busy").

    python3 ~/goosebot_hw/scripts/encoder_check.py            # live counts, Ctrl+C for the summary

1. SIGN: with the robot lifted, turn each front wheel by hand in the robot's FORWARD direction. Its count must go UP.
   If it goes down, flip that wheel's sign (fl_sign / fr_sign) in config/encoder_params.yaml.
2. COUNTS PER REV: put a tape mark on one wheel, start the script, turn that wheel exactly 10 full turns forward, then
   Ctrl+C. counts_per_rev = |count| / 10 (printed). Do both wheels; they should agree within a few counts. Put the
   rounded value in counts_per_rev.
3. MISSED EDGES: drive the wheels with the motors (teleop, lifted) at top speed for ~10 s while this runs. "missed"
   must stay near 0. If not, the CPU cannot keep up with the edge rate at that speed (see README).

Options: --chip /dev/gpiochip1 --fl 5 8 --fr 13 4 --turns 10
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))   # source tree, no build needed
from goosebot_hw.quadrature import Encoders  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chip', default='/dev/gpiochip1')
    ap.add_argument('--fl', type=int, nargs=2, default=[5, 8], metavar=('A', 'B'))
    ap.add_argument('--fr', type=int, nargs=2, default=[13, 4], metavar=('A', 'B'))
    ap.add_argument('--turns', type=float, default=10.0, help='wheel turns made, for the counts/rev result')
    a = ap.parse_args()
    enc = Encoders(a.chip, {'fl': tuple(a.fl), 'fr': tuple(a.fr)}, consumer='encoder_check')
    print(f"libgpiod {'v2' if enc.v2 else 'v1'}; FL A/B {a.fl}, FR A/B {a.fr} on {a.chip}. Ctrl+C to stop.\n")
    t0 = time.monotonic()
    prev, tp = enc.snapshot(), t0
    peak = {'fl': 0.0, 'fr': 0.0}
    try:
        while True:
            time.sleep(0.5)
            if enc.error is not None:
                print(f'\nreader thread failed: {enc.error!r}')
                break
            s, t = enc.snapshot(), time.monotonic()
            rates = {n: (s[n][2] - prev[n][2]) / (t - tp) for n in s}
            for n in rates:
                peak[n] = max(peak[n], rates[n])
            print(f"\rFL count {s['fl'][0]:+8d} missed {s['fl'][1]:5d} ({rates['fl']:6.0f} edges/s)   "
                  f"FR count {s['fr'][0]:+8d} missed {s['fr'][1]:5d} ({rates['fr']:6.0f} edges/s)   ",
                  end='', flush=True)
            prev, tp = s, t
    except KeyboardInterrupt:
        pass
    s = enc.snapshot()
    enc.close()
    print('\n')
    for n in ('fl', 'fr'):
        count, err, edges = s[n]
        print(f'{n.upper()}: count {count:+d} over {a.turns:g} turns -> {abs(count) / a.turns:.1f} counts/rev '
              f'(sign: {"+1" if count >= 0 else "-1"} if you turned it FORWARD); '
              f'missed {err} of {edges} edges; peak {peak[n]:.0f} edges/s')
    print('\nIf only one wheel was turned, ignore the other line.')


if __name__ == '__main__':
    main()
