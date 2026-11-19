#!/usr/bin/env python3
"""
motor_lowspeed_test.py - find out WHY goosebot's wheels stall at low duty (esp. the reversing side
during a spin) and measure what the robot can really do slowly.

Standalone, no ROS. STOP hw_bringup / motor_driver_node / imu_node first: two processes writing the
PCA9685 fight each other, and imu_node reconfigures the MPU6050.

Reads the channel mapping, invert flags and pwm_frequency from hw_params.yaml (motor_driver section),
using the same forward/reverse rule as motor_driver_node, so "fwd" here == what the driver calls forward.

MODES
  sweep  WHEELS LIFTED. Per wheel, per direction: duty ramps UP until you press Enter (wheel started),
         then ramps DOWN until you press Enter (wheel stopped).
         -> start (static) duty and run (kinetic) duty for all 8 wheel/direction combos.
  pair   WHEELS LIFTED. Drives the spin pattern (all 4 wheels) at a fixed duty, asks which wheels
         turned, then drives each wheel ALONE in the same direction at the same duty and asks again.
         A wheel that turns alone but not with the other three -> supply / driver problem, not the motor.
  hold   One wheel, one direction, fixed duty until Enter. For multimeter readings (motor terminals,
         L298N VS-GND) - compare fwd vs rev at the same duty.
  spin   ON THE FLOOR, clear space. Steps spin duty and measures yaw rate with the MPU6050 directly.
         Default: robot stops between steps (start-from-rest curve).
         --down: starts high and steps DOWN without stopping (running curve; shows how slow it can
         turn once already moving).
  spinwatch  Like spin, but at every duty step YOU type which wheels turned ('fl rr', 'all',
         blank = none, 'r' = repeat, 'q' = quit). Gyro yaw rate is logged too if the IMU answers
         (--no-imu to skip, e.g. lifted). Default: stops between steps (which wheels START).
         --down: keeps spinning and steps down while you watch (which wheels KEEP running).
         Ends with a table: lowest duty each wheel turned at, per spin direction.

EXAMPLES
  python3 motor_lowspeed_test.py sweep
  python3 motor_lowspeed_test.py sweep --freq 50
  python3 motor_lowspeed_test.py sweep --wheels rl fl --kick-duty 0.7 --kick-time 0.1
  python3 motor_lowspeed_test.py pair --duty 0.18
  python3 motor_lowspeed_test.py hold --wheel rl --dir rev --duty 0.25
  python3 motor_lowspeed_test.py spin --start 0.10 --max 0.45 --step 0.025
  python3 motor_lowspeed_test.py spin --down --start 0.10 --max 0.45 --step 0.025
  python3 motor_lowspeed_test.py spinwatch --start 0.10 --max 0.40 --step 0.02
  python3 motor_lowspeed_test.py spinwatch --down --start 0.04 --max 0.40 --step 0.02
  python3 motor_lowspeed_test.py spinwatch --no-imu --dirs ccw --kick-duty 0.7 --kick-time 0.1
Every mode writes a CSV next to where you run it. --vbat 12.1 just records your pack voltage in it.
"""
import argparse
import csv
import math
import os
import select
import signal
import sys
import time

WHEELS = ("fl", "fr", "rl", "rr")
LEFT = ("fl", "rl")


# ----------------------------------------------------------------------------- hardware
class Drive:
    def __init__(self, cfg, freq):
        import board
        import busio
        from adafruit_pca9685 import PCA9685
        self.pca = PCA9685(busio.I2C(board.SCL, board.SDA))   # Blinka default bus = I2C8 on this Rock
        self.pca.frequency = freq
        self.ch = {}
        for name in WHEELS:
            in1, in2 = cfg.get(name, {"fl": [0, 1], "rl": [2, 3], "rr": [4, 5], "fr": [6, 7]}[name])
            inv = cfg.get("invert_left" if name in LEFT else "invert_right", False)
            # same rule as motor_driver_node.Motor: a = forward channel, b = reverse channel
            self.ch[name] = (in2, in1) if inv else (in1, in2)

    def set(self, name, duty_signed):
        a, b = (self.pca.channels[c] for c in self.ch[name])
        d = int(min(abs(duty_signed), 1.0) * 65535)
        if duty_signed > 0:
            a.duty_cycle, b.duty_cycle = d, 0
        elif duty_signed < 0:
            a.duty_cycle, b.duty_cycle = 0, d
        else:
            a.duty_cycle = b.duty_cycle = 0

    def set_many(self, duties):
        for n, d in duties.items():
            self.set(n, d)

    def off(self):
        for n in WHEELS:
            try:
                self.set(n, 0.0)
            except OSError:
                pass

    def close(self):
        self.off()
        try:
            self.pca.deinit()
        except OSError:
            pass


class Gyro:
    """Minimal MPU6050 z-gyro reader (+-500 dps, DLPF 3), same settings as hw_params imu_node."""
    def __init__(self, bus, addr, sign):
        from smbus2 import SMBus
        self.b, self.a, self.sign, self.bias = SMBus(bus), addr, sign, 0.0
        self.b.write_byte_data(addr, 0x6B, 0x00)   # wake
        time.sleep(0.1)
        self.b.write_byte_data(addr, 0x1A, 0x03)   # DLPF
        self.b.write_byte_data(addr, 0x1B, 0x08)   # FS_SEL=1, 65.5 LSB/(deg/s)
        time.sleep(0.05)

    def raw(self):
        h, l = self.b.read_i2c_block_data(self.a, 0x47, 2)
        v = (h << 8) | l
        if v >= 0x8000:
            v -= 65536
        return self.sign * math.radians(v / 65.5)

    def rate(self):
        return self.raw() - self.bias

    def calibrate(self, sec=2.0):
        s, n, t_end = 0.0, 0, time.time() + sec
        while time.time() < t_end:
            s += self.raw(); n += 1; time.sleep(0.005)
        self.bias = s / max(n, 1)
        return self.bias

    def mean_rate(self, sec):
        s, n, t_end = 0.0, 0, time.time() + sec
        while time.time() < t_end:
            s += self.rate(); n += 1; time.sleep(0.005)
        return s / max(n, 1)


# ----------------------------------------------------------------------------- helpers
def enter_pressed():
    r, _, _ = select.select([sys.stdin], [], [], 0)
    if r:
        sys.stdin.readline()
        return True
    return False


def wait_or_enter(sec):
    t_end = time.time() + sec
    while time.time() < t_end:
        if enter_pressed():
            return True
        time.sleep(0.01)
    return False


def kick(drv, duties, kd, kt):
    if kd > 0 and kt > 0:
        drv.set_many({n: math.copysign(max(kd, abs(d)), d) for n, d in duties.items() if d != 0})
        time.sleep(kt)


def spin_pattern(duty, ccw):
    """REP-103 CCW (+z): left wheels reverse, right wheels forward."""
    s = 1.0 if ccw else -1.0
    return {"fl": -s * duty, "rl": -s * duty, "fr": s * duty, "rr": s * duty}


def frange(a, b, step):
    out, x = [], a
    while (step > 0 and x <= b + 1e-9) or (step < 0 and x >= b - 1e-9):
        out.append(round(x, 4)); x += step
    return out


def open_csv(args, header):
    name = args.out or f"motor_{args.mode}_{args.freq}Hz_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    f = open(name, "w", newline="")
    w = csv.writer(f)
    w.writerow(["# mode", args.mode, "freq_hz", args.freq, "vbat", args.vbat,
                "kick_duty", args.kick_duty, "kick_time", args.kick_time])
    w.writerow(header)
    print(f"logging to {name}")
    return f, w


# ----------------------------------------------------------------------------- modes
def do_sweep(drv, args):
    f, w = open_csv(args, ["wheel", "dir", "start_duty", "run_duty"])
    results = []
    for name in args.wheels:
        order = ((-1, "rev"), (1, "fwd")) if args.rev_first else ((1, "fwd"), (-1, "rev"))
        for sgn, dname in order:
            input(f"\n[{name.upper()} {dname}] wheels lifted? Enter to start the up-ramp "
                  f"(press Enter again the moment the wheel STARTS turning)")
            started, d = None, args.start
            while d <= args.max + 1e-9:
                print(f"\r  up   duty {d:.3f} ", end="", flush=True)
                kick(drv, {name: sgn * d}, args.kick_duty, args.kick_time)
                drv.set(name, sgn * d)
                if wait_or_enter(args.dwell):
                    started = d; break
                d = round(d + args.step, 4)
            if started is None:
                drv.off()
                print(f"\n  never started up to {args.max}")
                results.append((name, dname, None, None)); w.writerow([name, dname, "", ""]); f.flush()
                continue
            print(f"\n  started at ~{started:.3f}. Holding 1 s, then ramping DOWN: "
                  f"press Enter the moment it STOPS")
            time.sleep(1.0)
            stopped, d = None, started
            while d >= 0.0:
                print(f"\r  down duty {d:.3f} ", end="", flush=True)
                drv.set(name, sgn * d)
                if wait_or_enter(args.dwell):
                    stopped = d; break
                d = round(d - args.step, 4)
            drv.off()
            print()
            results.append((name, dname, started, stopped))
            w.writerow([name, dname, started, stopped if stopped is not None else 0.0]); f.flush()
    f.close()
    print("\nwheel dir  start  run   (Enter reaction lag: values may read ~1 step late)")
    for n, dn, s, r in results:
        print(f"{n:>5} {dn:>3}  {'' if s is None else f'{s:.3f}':>5}  {'' if r is None else f'{r:.3f}':>5}")
    fwd = [s for _, dn, s, _ in results if dn == "fwd" and s is not None]
    rev = [s for _, dn, s, _ in results if dn == "rev" and s is not None]
    if fwd and rev:
        print(f"mean start: fwd {sum(fwd)/len(fwd):.3f}  rev {sum(rev)/len(rev):.3f}")


def ask_turned(prompt):
    ans = input(prompt).lower().split()
    return {n: (n in ans) for n in WHEELS}


def do_pair(drv, args):
    f, w = open_csv(args, ["test", "spin_dir", "duty", "fl", "fr", "rl", "rr"])
    for ccw in (True, False):
        sd = "ccw" if ccw else "cw"
        pat = spin_pattern(args.duty, ccw)
        input(f"\n[{sd.upper()} spin pattern, ALL FOUR, duty {args.duty}] wheels lifted? Enter to run "
              f"{args.time:.0f} s")
        kick(drv, pat, args.kick_duty, args.kick_time)
        drv.set_many(pat); time.sleep(args.time); drv.off()
        t = ask_turned("  which wheels turned? (e.g. 'fl rr', blank = none): ")
        w.writerow(["all4", sd, args.duty] + [int(t[n]) for n in WHEELS]); f.flush()
        alone = {}
        for n in WHEELS:
            input(f"  [{n.upper()} ALONE, {'fwd' if pat[n] > 0 else 'rev'}, duty {args.duty}] Enter to run")
            kick(drv, {n: pat[n]}, args.kick_duty, args.kick_time)
            drv.set(n, pat[n]); time.sleep(args.time); drv.off()
            alone[n] = input("    turned? [y/N]: ").strip().lower().startswith("y")
        w.writerow(["alone", sd, args.duty] + [int(alone[n]) for n in WHEELS]); f.flush()
        for n in WHEELS:
            if alone[n] and not t[n]:
                print(f"  !! {n.upper()} turns alone but not with all four -> supply sag / driver, not the motor")
            if not alone[n]:
                print(f"  {n.upper()} does not turn even alone at {args.duty} in "
                      f"{'fwd' if pat[n] > 0 else 'rev'} -> that motor/channel needs more duty")
    f.close()


def do_hold(drv, args):
    sgn = 1 if args.dir == "fwd" else -1
    print(f"{args.wheel.upper()} {args.dir} at duty {args.duty}. Measure DC volts across the motor leads "
          f"and across L298N VS-GND. Enter to stop.")
    kick(drv, {args.wheel: sgn * args.duty}, args.kick_duty, args.kick_time)
    drv.set(args.wheel, sgn * args.duty)
    input()
    drv.off()


def do_spin(drv, args):
    g = Gyro(args.imu_bus, args.imu_addr, args.gyro_sign)
    input("ON THE FLOOR, clear ~0.5 m around it. Keep it still for bias calibration, then Enter")
    print(f"gyro bias {g.calibrate():+.5f} rad/s")
    f, w = open_csv(args, ["profile", "spin_dir", "duty", "yaw_rate_rad_s", "yaw_rate_deg_s", "stalled"])
    duties = frange(args.start, args.max, args.step)
    print(" profile dir   duty   rad/s   deg/s")

    def log(profile, sd, d, r):
        stalled = abs(r) < 0.05
        w.writerow([profile, sd, d, f"{r:.4f}", f"{math.degrees(r):.2f}", int(stalled)]); f.flush()
        print(f" {profile:>7} {sd:>3}  {d:.3f}  {r:+.3f}  {math.degrees(r):+7.1f}{'  STALL' if stalled else ''}")

    if not args.down:
        for d in duties:
            for ccw in (True, False):
                pat = spin_pattern(d, ccw)
                kick(drv, pat, args.kick_duty, args.kick_time)
                drv.set_many(pat)
                time.sleep(args.settle)
                r = g.mean_rate(args.measure)
                drv.off(); time.sleep(args.pause)
                log("rest", "ccw" if ccw else "cw", d, r)
    else:
        for ccw in (True, False):
            pat = spin_pattern(args.max, ccw)
            kick(drv, pat, max(args.kick_duty, args.max), max(args.kick_time, 0.1))
            for d in reversed(duties):          # no stop in between: running curve
                drv.set_many(spin_pattern(d, ccw))
                time.sleep(args.settle)
                r = g.mean_rate(args.measure)
                log("running", "ccw" if ccw else "cw", d, r)
                if abs(r) < 0.05:
                    break
            drv.off(); time.sleep(args.pause)
    f.close()


def parse_wheels(ans):
    """'fl rr' / 'fl,rr' / 'all' / '' -> dict; None for q (quit), 'r' for repeat."""
    a = ans.strip().lower().replace(",", " ")
    if a in ("q", "quit"):
        return None
    if a in ("r", "repeat"):
        return "r"
    toks = a.split()
    if "all" in toks:
        return {n: True for n in WHEELS}
    bad = [t for t in toks if t not in WHEELS and t != "none"]
    if bad:
        return "?"
    return {n: (n in toks) for n in WHEELS}


def ask_wheels(prompt):
    while True:
        r = parse_wheels(input(prompt))
        if r == "?":
            print("    use fl fr rl rr (any combination), 'all', blank/none, 'r' repeat, 'q' quit")
            continue
        return r


def do_spinwatch(drv, args):
    """Spin pattern stepped through duties; you type which wheels turned at each step.
    Rest profile (default): stops between steps -> which wheels START at each duty.
    --down: keeps running and steps DOWN while you watch -> which wheels KEEP running."""
    g = None
    if not args.no_imu:
        try:
            g = Gyro(args.imu_bus, args.imu_addr, args.gyro_sign)
        except Exception as e:
            print(f"IMU not available ({e}); continuing without yaw rate")
    dirs = [d == "ccw" for d in args.dirs]
    duties = frange(args.start, args.max, args.step)
    if g:
        input("Keep the robot still for gyro bias calibration, then Enter")
        print(f"gyro bias {g.calibrate():+.5f} rad/s")
    f, w = open_csv(args, ["profile", "spin_dir", "duty", "fl", "fr", "rl", "rr", "yaw_rate_rad_s"])
    print("Answer with the wheels that turned: e.g. 'fl rr', 'all', blank = none, "
          "'r' = repeat step, 'q' = quit")
    table = {}                                   # (dir, duty) -> dict

    def record(profile, sd, d, t, r):
        table[(sd, d)] = t
        w.writerow([profile, sd, d] + [int(t[n]) for n in WHEELS] +
                   ["" if r is None else f"{r:.4f}"])
        f.flush()

    def yaw():
        return g.mean_rate(min(args.measure, args.time)) if g else None

    quit_ = False
    if not args.down:
        for d in duties:
            for ccw in dirs:
                sd = "ccw" if ccw else "cw"
                while True:
                    pat = spin_pattern(d, ccw)
                    input(f"\n[{sd.upper()} duty {d:.3f}] Enter to run {args.time:.1f} s")
                    kick(drv, pat, args.kick_duty, args.kick_time)
                    drv.set_many(pat)
                    t0 = time.time()
                    r = yaw()
                    time.sleep(max(0.0, args.time - (time.time() - t0)))
                    drv.off()
                    if r is not None:
                        print(f"  gyro {r:+.3f} rad/s ({math.degrees(r):+.1f} deg/s)")
                    t = ask_wheels("  which wheels turned? ")
                    if t == "r":
                        continue
                    break
                if t is None:
                    quit_ = True; break
                record("rest", sd, d, t, r)
            if quit_:
                break
    else:
        for ccw in dirs:
            sd = "ccw" if ccw else "cw"
            pat = spin_pattern(duties[-1], ccw)
            input(f"\n[{sd.upper()} running profile from duty {duties[-1]:.3f} down] Enter to start. "
                  f"Wheels KEEP TURNING while you type.")
            kick(drv, pat, max(args.kick_duty, 0.7), max(args.kick_time, 0.1))
            for d in reversed(duties):
                drv.set_many(spin_pattern(d, ccw))
                time.sleep(args.settle)
                r = yaw()
                msg = f"  duty {d:.3f}" + ("" if r is None else f"  gyro {r:+.3f} rad/s")
                t = ask_wheels(msg + "  which wheels are turning NOW? ")
                if t == "r":
                    t = ask_wheels("  (repeat) which wheels are turning NOW? ")
                if t is None or t == "r":
                    quit_ = True; break
                record("running", sd, d, t, r)
                if not any(t.values()):
                    break
            drv.off()
            time.sleep(args.pause)
            if quit_:
                break
    f.close()

    # summary: per direction, per wheel, lowest duty at which it turned
    print("\nlowest duty each wheel turned at ('-' = never)")
    print("dir   " + "  ".join(f"{n:>5}" for n in WHEELS))
    for ccw in dirs:
        sd = "ccw" if ccw else "cw"
        row = []
        for n in WHEELS:
            ok = [d for (s, d), t in table.items() if s == sd and t[n]]
            row.append(f"{min(ok):5.3f}" if ok else "    -")
        print(f"{sd:>3}   " + "  ".join(row))
    print("CCW: left wheels reverse, right forward. CW: left forward, right reverse.")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["sweep", "pair", "hold", "spin", "spinwatch"])
    ap.add_argument("--config", default=os.path.expanduser("~/goosebot_hw/config/hw_params.yaml"))
    ap.add_argument("--freq", type=int, default=None, help="PWM Hz (default: pwm_frequency from yaml)")
    ap.add_argument("--vbat", default="", help="pack voltage you measured, recorded in the CSV")
    ap.add_argument("--out", default=None)
    ap.add_argument("--kick-duty", type=float, default=0.0, help="start burst duty (0 = no kick)")
    ap.add_argument("--kick-time", type=float, default=0.0, help="start burst length s")
    # sweep
    ap.add_argument("--wheels", nargs="+", default=list(WHEELS), choices=WHEELS)
    ap.add_argument("--start", type=float, default=0.05)
    ap.add_argument("--max", type=float, default=0.6)
    ap.add_argument("--step", type=float, default=0.01)
    ap.add_argument("--dwell", type=float, default=0.5, help="s per sweep step")
    ap.add_argument("--rev-first", action="store_true", help="sweep: test reverse before forward")
    # pair / hold
    ap.add_argument("--duty", type=float, default=0.18)
    ap.add_argument("--time", type=float, default=2.0)
    ap.add_argument("--wheel", choices=WHEELS, default="rl")
    ap.add_argument("--dir", choices=["fwd", "rev"], default="rev")
    # spin
    ap.add_argument("--down", action="store_true")
    ap.add_argument("--settle", type=float, default=0.7)
    ap.add_argument("--measure", type=float, default=1.0)
    ap.add_argument("--pause", type=float, default=0.8)
    ap.add_argument("--imu-bus", type=int, default=6)
    ap.add_argument("--imu-addr", type=lambda s: int(s, 0), default=0x68)
    ap.add_argument("--gyro-sign", type=float, default=None, help="default: gyro_z_sign from yaml")
    # spinwatch
    ap.add_argument("--no-imu", action="store_true", help="spinwatch: skip the gyro (e.g. lifted)")
    ap.add_argument("--dirs", nargs="+", choices=["ccw", "cw"], default=["ccw", "cw"])
    args = ap.parse_args()

    cfg, icfg = {}, {}
    try:
        import yaml
        y = yaml.safe_load(open(args.config))
        cfg = y.get("motor_driver", {}).get("ros__parameters", {})
        icfg = y.get("imu_node", {}).get("ros__parameters", {})
    except Exception as e:
        print(f"WARNING: could not read {args.config} ({e}); using default channel map")
    if args.freq is None:
        args.freq = int(cfg.get("pwm_frequency", 100))
    if args.gyro_sign is None:
        args.gyro_sign = float(icfg.get("gyro_z_sign", 1.0))
    if args.mode == "sweep" and args.step <= 0:
        sys.exit("--step must be > 0")

    drv = Drive(cfg, args.freq)
    print(f"PWM {args.freq} Hz, channels (fwd, rev): {drv.ch}")

    def bail(*_):
        drv.close(); print("\nstopped, outputs zeroed"); sys.exit(1)
    signal.signal(signal.SIGINT, bail)
    signal.signal(signal.SIGTERM, bail)
    try:
        {"sweep": do_sweep, "pair": do_pair, "hold": do_hold, "spin": do_spin,
         "spinwatch": do_spinwatch}[args.mode](drv, args)
    finally:
        drv.close()


if __name__ == "__main__":
    main()
