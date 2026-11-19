#!/usr/bin/env python3
"""
32 Hz motor floor calibration ON THE FLOOR (GOOSEBOT_TODO A4 steps 3, 4 and 6), measured the way motor_driver_node
really drives: same PWM frequency, same kick, same rear-wheel matching, all read from hw_params.yaml. Speed comes from
the front-wheel encoders, turn rate from the MPU6050 gyro. No ROS needed; STOP BRINGUP FIRST (it owns the motors, the
encoder lines and the IMU).

    python3 ~/goosebot_hw/scripts/floor_calib.py straight     # -> min_duty, v_floor
    python3 ~/goosebot_hw/scripts/floor_calib.py spin         # -> min_duty_spin, w_floor
    python3 ~/goosebot_hw/scripts/floor_calib.py vmax         # -> v_max (speed at max_duty)

Each test steps the duty DOWN (default 0.16 -> 0.04 in 0.01 steps). At each duty the robot kicks, holds the duty for
--hold s (forward then backward, or CCW then CW, so it stays roughly in place), and the last --measure s are averaged.
It stops after two duties in a row where the robot no longer moves. At the end it prints the values for hw_params.yaml.

Needs: robot ON THE FLOOR it normally drives on, about 1 m clear in front and behind (straight) or 0.4 m around (spin),
battery charged (note the voltage: floors rise as the pack sags), hand on the kill switch. Ctrl+C stops the motors.
Options: --start 0.16 --stop 0.04 --step 0.01 --hold 2.0 --measure 1.0 --config ~/goosebot_hw/config
"""
import argparse
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))       # source tree: goosebot_hw.quadrature / motor_driver_node

import yaml  # noqa: E402
from goosebot_hw.quadrature import Encoders  # noqa: E402
from goosebot_hw.motor_driver_node import Motor, WheelMatch  # noqa: E402


def load(cfg_dir, fname, node):
    with open(os.path.join(cfg_dir, fname)) as f:
        return (yaml.safe_load(f) or {})[node]['ros__parameters']


class Gyro:
    """MPU6050 yaw rate (rad/s, CCW +), same register setup as imu_node."""
    def __init__(self, p):
        from smbus2 import SMBus
        self.bus, self.addr = SMBus(int(p.get('bus', 6))), int(p.get('address', 0x68))
        rng = {250: (0, 131.0), 500: (1, 65.5), 1000: (2, 32.8), 2000: (3, 16.4)}[int(p.get('gyro_range_dps', 500))]
        self.lsb, self.sign = rng[1], float(p.get('gyro_z_sign', 1.0))
        self.bus.write_byte_data(self.addr, 0x6B, 0x01)
        time.sleep(0.1)
        self.bus.write_byte_data(self.addr, 0x1A, int(p.get('dlpf_cfg', 3)))
        self.bus.write_byte_data(self.addr, 0x1B, rng[0] << 3)
        self.bias = 0.0
        xs = []
        for _ in range(300):
            xs.append(self.raw())
            time.sleep(0.005)
        self.bias = sum(xs) / len(xs)

    def raw(self):
        h, l = self.bus.read_i2c_block_data(self.addr, 0x47, 2)
        v = (h << 8) | l
        return (v - 65536 if v >= 32768 else v) / self.lsb * math.pi / 180.0

    def rate(self):
        return self.sign * (self.raw() - self.bias)


class Rig:
    def __init__(self, cfg_dir):
        md = load(cfg_dir, 'hw_params.yaml', 'motor_driver')
        enc = load(cfg_dir, 'encoder_params.yaml', 'encoder_node')
        imu = load(cfg_dir, 'hw_params.yaml', 'imu_node')
        self.md = md
        self.max_d = float(md['max_duty'])
        self.kick_d, self.kick_t = float(md.get('kick_duty', 0.7)), float(md.get('kick_time', 0.02))
        self.freq = int(md.get('pwm_frequency', 100))
        self.match = None
        if md.get('wheel_matching', False):
            fd, rd = md['wheel_cal_duty_front'], md['wheel_cal_duty_rear']
            self.match = (WheelMatch((fd, md['wheel_cal_fl']), (rd, md['wheel_cal_rl']), self.max_d),
                          WheelMatch((fd, md['wheel_cal_fr']), (rd, md['wheel_cal_rr']), self.max_d))
        cpr = int(enc['counts_per_rev'])
        if cpr <= 0:
            sys.exit('encoder_params.yaml counts_per_rev is 0: calibrate the encoders first.')
        self.m_per_count = 2 * math.pi * float(enc['wheel_radius']) / cpr
        self.sign = {'fl': int(enc['fl_sign']), 'fr': int(enc['fr_sign'])}
        self.enc = Encoders(enc['chip'], {'fl': tuple(enc['fl_lines']), 'fr': tuple(enc['fr_lines'])},
                            consumer='floor_calib')
        print('Gyro bias: keep the robot still ...')
        self.gyro = Gyro(imu)
        import board, busio
        from adafruit_pca9685 import PCA9685
        self.pca = PCA9685(busio.I2C(board.SCL, board.SDA))
        self.pca.frequency = self.freq
        il, ir = md.get('invert_left', False), md.get('invert_right', False)
        self.fl, self.rl = Motor(self.pca, *md['fl'], il), Motor(self.pca, *md['rl'], il)
        self.fr, self.rr = Motor(self.pca, *md['fr'], ir), Motor(self.pca, *md['rr'], ir)
        print(f"PWM {self.freq} Hz, kick {self.kick_d} for {self.kick_t} s, max_duty {self.max_d}, "
              f"wheel matching {'on' if self.match else 'off'}")

    def rear(self, side, d):
        if self.match is None or abs(d) < 1e-6:
            return d
        return math.copysign(self.match[side].map(abs(d)), d)

    def set(self, dl, dr, kick=False):
        f = (lambda d: math.copysign(max(abs(d), self.kick_d), d) if (kick and abs(d) > 1e-6) else d)
        self.fl.set(f(dl)); self.rl.set(f(self.rear(0, dl)))
        self.fr.set(f(dr)); self.rr.set(f(self.rear(1, dr)))

    def stop(self):
        for m in (self.fl, self.rl, self.fr, self.rr):
            try:
                m.set(0.0)
            except OSError:
                pass

    def dist(self):
        s = self.enc.snapshot()
        return s['fl'][0] * self.sign['fl'] * self.m_per_count, s['fr'][0] * self.sign['fr'] * self.m_per_count

    def run(self, dl, dr, hold, measure):
        """Kick, hold (dl, dr) for `hold` s, stop. Returns (v_left, v_right, w) averaged over the last `measure` s."""
        samples = []
        t0 = time.monotonic()
        self.set(dl, dr, kick=True)
        kicked = False
        while True:
            t = time.monotonic() - t0
            if not kicked and t >= self.kick_t:
                self.set(dl, dr)
                kicked = True
            if t >= hold:
                break
            l, r = self.dist()
            samples.append((t, l, r, self.gyro.rate()))
            time.sleep(0.01)
        self.stop()
        win = [s for s in samples if s[0] >= hold - measure]
        if len(win) < 2:
            return 0.0, 0.0, 0.0
        dt = win[-1][0] - win[0][0]
        vl = (win[-1][1] - win[0][1]) / dt
        vr = (win[-1][2] - win[0][2]) / dt
        w = sum(s[3] for s in win) / len(win)
        time.sleep(0.8)                         # let the robot settle before the next step
        return vl, vr, w

    def close(self):
        self.stop()
        self.enc.close()
        try:
            self.pca.deinit()
        except OSError:
            pass


def sweep(rig, mode, duties, hold, measure):
    rows, misses = [], 0
    print(f"\n{'duty':>5} {'dir':>4} {'v_left':>8} {'v_right':>8} {'v (m/s)':>8} {'w (rad/s)':>9}  moving")
    for d in duties:
        ok_both = True
        for sgn, name in ((1, 'fwd' if mode == 'straight' else 'ccw'), (-1, 'rev' if mode == 'straight' else 'cw')):
            dl, dr = (sgn * d, sgn * d) if mode == 'straight' else (-sgn * d, sgn * d)
            vl, vr, w = rig.run(dl, dr, hold, measure)
            v = (vl + vr) / 2
            if mode == 'straight':
                moving = abs(vl) > 0.01 and abs(vr) > 0.01 and abs(v) > 0.02
            else:
                moving = abs(w) > 0.15 and abs(vl) > 0.005 and abs(vr) > 0.005
            ok_both &= moving
            rows.append((d, name, vl, vr, v, w, moving))
            print(f'{d:5.2f} {name:>4} {vl:8.3f} {vr:8.3f} {v:8.3f} {w:9.3f}  {"yes" if moving else "NO"}')
        misses = 0 if ok_both else misses + 1
        if misses >= 2:
            print('two duties in a row without reliable motion: stopping the sweep')
            break
    return rows


def recommend(rows, mode, step, margin_steps):
    duties = sorted({r[0] for r in rows}, reverse=True)
    lowest = None
    for d in duties:                            # lowest duty where it moved both ways, with every duty above it too
        if all(r[6] for r in rows if r[0] == d):
            lowest = d
        else:
            break
    if lowest is None:
        print('\nNo duty moved the robot reliably in both directions. Raise --start.')
        return
    rec = round(lowest + margin_steps * step, 3)
    at = [r for r in rows if abs(r[0] - rec) < 1e-6] or [r for r in rows if abs(r[0] - lowest) < 1e-6]
    if mode == 'straight':
        vf = sum(abs(r[4]) for r in at) / len(at)
        print(f'\nLowest duty that moved both ways: {lowest:.2f}. With a {margin_steps * step:.2f} margin:')
        print(f'    min_duty: {rec:.2f}\n    v_floor: {vf:.3f}            # m/s measured at {at[0][0]:.2f}')
    else:
        wf = sum(abs(r[5]) for r in at) / len(at)
        print(f'\nLowest duty that spun both ways: {lowest:.2f}. With a {margin_steps * step:.2f} margin:')
        print(f'    min_duty_spin: {rec:.2f}\n    w_floor: {wf:.3f}            # rad/s measured at {at[0][0]:.2f}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['straight', 'spin', 'vmax'])
    ap.add_argument('--start', type=float, default=0.16)
    ap.add_argument('--stop', type=float, default=0.04)
    ap.add_argument('--step', type=float, default=0.01)
    ap.add_argument('--hold', type=float, default=2.0)
    ap.add_argument('--measure', type=float, default=1.0)
    ap.add_argument('--config', default=os.path.expanduser('~/goosebot_hw/config'))
    a = ap.parse_args()

    if subprocess.run(['pgrep', '-f', 'motor_driver_node|encoder_node|imu_node'],
                      capture_output=True).returncode == 0:
        sys.exit('motor_driver_node / encoder_node / imu_node is running. Stop bringup first.')
    print(__doc__.split('Needs:')[1].split('Options:')[0].strip())
    if input('\nRobot on the floor, space clear, kill switch in reach? Type GO: ').strip() != 'GO':
        return
    rig = Rig(a.config)
    try:
        if a.mode == 'vmax':
            d = rig.max_d
            res = []
            for sgn, name in ((1, 'fwd'), (-1, 'rev')):
                vl, vr, w = rig.run(sgn * d, sgn * d, max(a.hold, 2.0), a.measure)
                res.append(abs((vl + vr) / 2))
                print(f'{d:.2f} {name}: v_left {vl:.3f}  v_right {vr:.3f}  v {(vl + vr) / 2:.3f} m/s  w {w:.3f} rad/s')
            print(f'\n    v_max: {sum(res) / len(res):.3f}            # m/s at max_duty {d:.2f}')
            return
        n = int(round((a.start - a.stop) / a.step)) + 1
        duties = [round(a.start - i * a.step, 3) for i in range(n)]
        rows = sweep(rig, a.mode, duties, a.hold, a.measure)
        recommend(rows, a.mode, a.step, 1 if a.mode == 'straight' else 2)
    except KeyboardInterrupt:
        print('\nstopped')
    finally:
        rig.close()


if __name__ == '__main__':
    main()
