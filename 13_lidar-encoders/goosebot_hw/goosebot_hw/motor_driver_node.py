#!/usr/bin/env python3
"""
Real-robot replacement for Gazebo's DiffDrive plugin.

Input : geometry_msgs/Twist on `cmd_vel_in` (REP-103: +x forward m/s, +z = CCW/left rad/s)
Output: PCA9685 PWM -> L298N -> 4 TT motors (left pair / right pair, skid steer)
        /cmd_vel_applied (Twist): the velocity this node ACTUALLY sent after deadband,
        clamping and slew limiting. cmd_vel_to_odom integrates THIS, not raw /cmd_vel.

Differences from the old goose_ros2/goose_adapter.py (read before reusing it):
  * The old adapter treated Twist as unitless (-1..1) and used left = fwd + steer,
    i.e. POSITIVE angular.z turned the robot RIGHT. That is opposite to REP-103/Nav2.
    This node uses real units and the REP-103 sign. Lane-follower output must go
    through cmd_vel_mux_node (lane_angular_sign) or its turns will be inverted.
  * Open-loop: v_max / min_duty / max_duty are CALIBRATION VALUES (see README).
  * max_duty caps the PWM so a full 3S pack (12.6 V) minus the ~2 V L298N drop does not
    over-volt 6-9 V TT motors. Derived arithmetic; check against your measured pack voltage.
  * Watchdog: no command for `cmd_timeout` s -> outputs go to 0.
  * Wheel matching (2026-11-19): the front motors (new, with encoders) and the rear motors (old TT) turn at
    different speeds for the same duty (rears ~1.46x faster, measured lifted). Each side's duty is computed as before
    and sent to the FRONT motor; each REAR motor gets the duty that makes it turn at the same speed as its front,
    looked up from per-motor speed-vs-duty measurements (wheel_cal_* parameters, see WheelMatch). The fronts set the
    speed, which is also what the encoders measure. Disable with wheel_matching: false (all four get the side duty).
  * Speed table (2026-11-19): wheel speed -> duty comes from a measured on-floor table (speed_table_duty /
    speed_table_speed, from scripts/floor_calib.py straight + vmax) instead of a straight line from (min_duty, v_floor)
    to (max_duty, v_max). The real curve is steep near the floor and flattens towards max_duty, so the straight line
    drove ~30 % faster than commanded mid-range. Turning still adds the min_duty -> min_duty_spin floor blend on top,
    fading out towards max_duty. speed_table: false restores the old straight-line mapping.
"""
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class Motor:
    def __init__(self, pca, in1, in2, invert=False):
        self.a = pca.channels[in2 if invert else in1]
        self.b = pca.channels[in1 if invert else in2]

    def set(self, duty_signed):
        d = int(min(abs(duty_signed), 1.0) * 65535)
        if duty_signed > 0:
            self.a.duty_cycle, self.b.duty_cycle = d, 0
        elif duty_signed < 0:
            self.a.duty_cycle, self.b.duty_cycle = 0, d
        else:
            self.a.duty_cycle = self.b.duty_cycle = 0


def _interp(x, xs, ys):
    """Piecewise-linear y(x) through (xs, ys) (xs ascending); linear extrapolation off both ends."""
    if x <= xs[0]:
        i = 0
    elif x >= xs[-1]:
        i = len(xs) - 2
    else:
        i = next(k for k in range(len(xs) - 1) if xs[k] <= x <= xs[k + 1])
    x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


class WheelMatch:
    """Rear-motor duty that makes a rear wheel turn as fast as the front wheel on its side.

    front_cal / rear_cal: (duties, turns_per_s) measured with the wheels LIFTED, one motor at a time
    (motor_lowspeed_test.py hold + stopwatch / encoder_check.py). Duty magnitudes; direction handled by the caller.
    map(d): front speed at duty d (front curve) -> rear duty giving that speed (inverse of rear curve).
    Below the rear's lowest calibrated speed the rear gets its lowest calibrated duty (it cannot run slower and still
    turn); above the top point both curves are extrapolated linearly. Result clamped to [0, max_duty]."""

    def __init__(self, front_cal, rear_cal, max_duty):
        self.fd, self.fs = self._check(front_cal)
        self.rd, self.rs = self._check(rear_cal)
        self.max_d = max_duty

    @staticmethod
    def _check(cal):
        d, s = [float(x) for x in cal[0]], [float(x) for x in cal[1]]
        if len(d) != len(s) or len(d) < 2:
            raise ValueError(f'wheel_cal needs >= 2 matching duty/speed points, got {d} / {s}')
        if any(b <= a for a, b in zip(d, d[1:])) or any(b <= a for a, b in zip(s, s[1:])):
            raise ValueError(f'wheel_cal duties and speeds must both increase: {d} / {s}')
        return d, s

    def map(self, d):
        if d <= 0.0:
            return 0.0
        target = _interp(d, self.fd, self.fs)
        if target <= self.rs[0]:
            return min(self.rd[0], self.max_d)
        return max(0.0, min(_interp(target, self.rs, self.rd), self.max_d))


class MotorDriver(Node):
    def __init__(self):
        super().__init__('motor_driver')
        P = self.declare_parameter
        P('cmd_vel_in', '/cmd_vel_mux')
        P('dry_run', False)                 # True: no I2C, just compute (bench/laptop testing)
        P('pwm_frequency', 100)             # Hz, same as the existing goose code
        P('wheel_separation', 0.1346)       # m. 5.3 in from your encoder notes: RE-MEASURE
        P('v_max', 0.25)                    # m/s at duty == max_duty. CALIBRATE (README step 3)
        P('min_duty', 0.07)                 # stiction deadband; 0.07 is the old repo value. CALIBRATE
        P('min_duty_spin', 0.3)             # stiction duty for in-place spin; 0 = same as min_duty. CALIBRATE
        P('v_floor', 0.0)                   # m/s the robot really does at the straight stiction duty (min_duty); 0 = old mapping. CALIBRATE
        P('w_floor', 0.0)                   # rad/s the robot really turns at the spin stiction duty (min_duty_spin); 0 = old mapping. CALIBRATE
        P('max_duty', 0.85)                 # see docstring about L298N drop
        P('max_duty_rate', 3.0)             # duty/s slew limit (protects driver, avoids wheelspin)
        P('cmd_timeout', 0.5)               # s
        P('linear_scale', 1.0)              # measured/commanded distance ratio
        P('angular_scale', 1.0)             # measured/commanded rotation ratio
        P('rate', 50.0)
        P('kick_duty', 0.7)                 # duty used for the start burst (breaks stiction)
        P('kick_time', 0.02)                # s, length of the start burst
        # channel mapping from your 04_motor_test notes: FL 0/1, RL 2/3, RR 4/5, FR 6/7
        P('fl', [0, 1]); P('rl', [2, 3]); P('rr', [4, 5]); P('fr', [6, 7])
        P('invert_left', False); P('invert_right', False)
        # Wheel matching (see docstring). Speeds in wheel turns/s, measured lifted at the listed duties.
        P('wheel_matching', True)
        P('wheel_cal_duty_front', [0.08, 0.15, 0.30])
        P('wheel_cal_fl', [0.765, 1.163, 1.779])
        P('wheel_cal_fr', [0.781, 1.142, 1.779])
        P('wheel_cal_duty_rear', [0.05, 0.06, 0.08, 0.15, 0.30])
        P('wheel_cal_rl', [0.455, 0.801, 1.136, 1.701, 2.564])
        P('wheel_cal_rr', [0.345, 0.687, 1.111, 1.667, 2.688])
        # Speed table (see docstring): side duty -> robot speed in m/s driving straight, measured on the floor.
        # First duty should be min_duty, last max_duty. Empty lists = use the straight-line mapping.
        # Per-side speed trim: multiplies that side's wheel-speed demand before the duty lookup, so a side that runs
        # fast can be slowed to match (measured 2026-11-19: right ~2 % faster -> robot curves left going forward).
        P('speed_trim_left', 1.0)
        P('speed_trim_right', 1.0)
        P('speed_table', True)
        P('speed_table_duty', [0.0])
        P('speed_table_speed', [0.0])

        g = lambda n: self.get_parameter(n).value
        self.sep = g('wheel_separation'); self.vmax = g('v_max')
        self.min_d = g('min_duty'); self.max_d = g('max_duty')
        self.min_spin = g('min_duty_spin') or self.min_d
        self.vfloor = g('v_floor'); self.wfloor = g('w_floor')
        self.slew = g('max_duty_rate'); self.timeout = g('cmd_timeout')
        self.ls = g('linear_scale'); self.as_ = g('angular_scale')
        self.dry = g('dry_run')
        self.trim = (float(g('speed_trim_left')), float(g('speed_trim_right')))
        if not all(0.8 <= x <= 1.2 for x in self.trim):
            raise ValueError(f'speed_trim_left/right must be within 0.8..1.2, got {self.trim}')

        self.tab = None
        if g('speed_table'):
            td, ts = [float(x) for x in g('speed_table_duty')], [float(x) for x in g('speed_table_speed')]
            if len(td) < 2 or len(td) != len(ts):
                raise ValueError('speed_table is on but speed_table_duty / speed_table_speed are missing or differ in '
                                 'length. Fill them from floor_calib.py or set speed_table: false')
            if any(b <= a for a, b in zip(td, td[1:])) or any(b <= a for a, b in zip(ts, ts[1:])):
                raise ValueError(f'speed_table duties and speeds must both increase: {td} / {ts}')
            self.tab = (td, ts)
            self.min_d, self.max_d = td[0], min(self.max_d, td[-1])
            self.vmax = ts[-1]
            self.get_logger().info(f'speed table on: {len(td)} points, {td[0]:.2f}->{ts[0]:.3f} m/s ... '
                                   f'{td[-1]:.2f}->{ts[-1]:.3f} m/s (min_duty / v_max taken from the table)')

        self.match = None
        if g('wheel_matching'):
            fd, rd = list(g('wheel_cal_duty_front')), list(g('wheel_cal_duty_rear'))
            self.match = (WheelMatch((fd, g('wheel_cal_fl')), (rd, g('wheel_cal_rl')), self.max_d),
                          WheelMatch((fd, g('wheel_cal_fr')), (rd, g('wheel_cal_rr')), self.max_d))
            ex = ', '.join(f'{d:.2f}->RL {self.match[0].map(d):.3f}/RR {self.match[1].map(d):.3f}'
                           for d in (0.08, 0.15, 0.30) if d <= self.max_d)
            self.get_logger().info(f'wheel matching on (front duty -> rear duty): {ex}')

        self.motors_l, self.motors_r = [], []
        self.pca = None
        if not self.dry:
            import board, busio
            from adafruit_pca9685 import PCA9685
            self.pca = PCA9685(busio.I2C(board.SCL, board.SDA))
            self.pca.frequency = g('pwm_frequency')
            il, ir = g('invert_left'), g('invert_right')
            self.motors_l = [Motor(self.pca, *g('fl'), il), Motor(self.pca, *g('rl'), il)]
            self.motors_r = [Motor(self.pca, *g('fr'), ir), Motor(self.pca, *g('rr'), ir)]

        self.cmd = Twist(); self.last_cmd = None
        self.cur_l = 0.0; self.cur_r = 0.0       # current signed duty (post-slew)
        self.kick_duty = g('kick_duty'); self.kick_time = g('kick_time')
        self.prev_sign = [0, 0]
        self.kick_until = [0.0, 0.0]
        self.create_subscription(Twist, g('cmd_vel_in'), self.cb, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel_applied', 10)
        self.dt = 1.0 / g('rate')
        self.create_timer(self.dt, self.tick)
        self.get_logger().info(f'motor_driver up (dry_run={self.dry}) pwm={g("pwm_frequency")} Hz vmax={self.vmax} '
                               f'duty=[{self.min_d},{self.max_d}] kick={self.kick_duty} for {self.kick_time} s trim L/R {self.trim}')
        if g('pwm_frequency') < 50 and self.kick_time < 1.0 / g('pwm_frequency'):
            self.get_logger().warn(f'kick_time {self.kick_time} s is shorter than one PWM period '
                                   f'({1.0 / g("pwm_frequency"):.3f} s): the kick may not reach the motors')

    def cb(self, msg):
        self.cmd = msg
        self.last_cmd = self.get_clock().now()

    def to_duty(self, n, floor, nf):
        """normalized wheel speed (-1..1) -> signed duty incl. deadband compensation.
        floor = stiction duty for the current motion (see tick()).
        nf    = normalized speed the wheels really do AT the floor duty (v_floor / v_max).
        Any nonzero demand at or below nf just gets the floor duty (the robot cannot go
        slower); above nf the duty rises linearly to max_duty at n = 1."""
        if abs(n) < 1e-3:
            return 0.0
        frac = max(0.0, (min(abs(n), 1.0) - nf) / (1.0 - nf))
        d = floor + frac * (self.max_d - floor)
        return math.copysign(d, n)

    def tab_to_duty(self, v, t):
        """Speed table: wheel speed v (m/s, signed) -> signed side duty. t = turn fraction (0 straight, 1 spin).
        Below the table's first speed the side gets the floor duty (the robot cannot go slower). For turning, the
        extra spin floor (min_duty_spin - min_duty) is added and fades out linearly towards max_duty."""
        if abs(v) < 1e-4:
            return 0.0
        td, ts = self.tab
        base = td[0] if abs(v) <= ts[0] else min(_interp(abs(v), ts, td), self.max_d)
        off = t * (self.min_spin - self.min_d)
        d = base + off * (self.max_d - base) / (self.max_d - td[0])
        return math.copysign(min(d, self.max_d), v)

    def tab_from_duty(self, d, t):
        """Inverse of tab_to_duty: signed side duty -> wheel speed (m/s) the table says it gives."""
        td, ts = self.tab
        if abs(d) < 1e-6:
            return 0.0
        k = t * (self.min_spin - self.min_d) / (self.max_d - td[0])
        base = (abs(d) - k * self.max_d) / (1.0 - k) if k < 1.0 else td[0]
        if base < td[0] - 1e-6:
            return 0.0                    # below the floor (e.g. while slewing up): wheels not turning
        return math.copysign(min(_interp(base, td, ts), ts[-1]), d)

    def from_duty(self, d, floor, nf):
        """inverse of to_duty: signed duty -> normalized wheel speed actually achieved"""
        if abs(d) < 1e-6 or abs(d) < floor - 1e-9:
            return 0.0       # at/under stiction the wheels are not turning
        n = nf + (abs(d) - floor) / (self.max_d - floor) * (1.0 - nf)
        return math.copysign(n, d)

    def _kicking(self, side, d, tnow):
        """Start-burst: when a side starts moving or reverses, drive it at kick_duty for
        kick_time to break stiction. Only affects what is sent to the motors; cur_l/cur_r
        and /cmd_vel_applied are unchanged, so odometry is not affected. Returns True while
        the side is inside its kick window."""
        sign = 0 if abs(d) < 1e-6 else (1 if d > 0 else -1)
        if sign != 0 and sign != self.prev_sign[side]:     # start or direction change
            self.kick_until[side] = tnow + self.kick_time
        self.prev_sign[side] = sign
        return sign != 0 and tnow < self.kick_until[side]

    def _motor_duties(self, side, d, kicking):
        """Side duty -> (front duty, rear duty). Front gets the side duty; rear gets its matched duty.
        During a kick every motor gets at least kick_duty."""
        rear = d
        if self.match is not None and abs(d) > 1e-6:
            rear = math.copysign(self.match[side].map(abs(d)), d)
        front = d
        if kicking:
            front = math.copysign(max(abs(front), self.kick_duty), d)
            rear = math.copysign(max(abs(rear), self.kick_duty), d)
        return front, rear

    def tick(self):
        now = self.get_clock().now()
        stale = (self.last_cmd is None or
                 (now - self.last_cmd).nanoseconds * 1e-9 > self.timeout)
        v = 0.0 if stale else self.cmd.linear.x
        w = 0.0 if stale else self.cmd.angular.z

        # wheel linear speeds (m/s); divide by scales so the *achieved* motion matches the request
        vl = (v / self.ls) - (w / self.as_) * self.sep / 2.0
        vr = (v / self.ls) + (w / self.as_) * self.sep / 2.0
        nl, nr = vl / self.vmax, vr / self.vmax
        m = max(abs(nl), abs(nr), 1.0)       # saturate BOTH sides together: keeps the turn ratio
        nl, nr = nl / m * self.trim[0], nr / m * self.trim[1]     # per-side trim (side that runs fast gets < 1)
        # Stiction floor: min_duty when driving straight, min_duty_spin for a pure in-place
        # spin, blended by how much of the wheel demand is turning (0 = straight, 1 = spin).
        half_turn = abs(w / self.as_) * self.sep / 2.0
        lin = abs(v / self.ls)
        t = half_turn / (half_turn + lin) if (half_turn + lin) > 1e-9 else 0.0
        floor = self.min_d + t * (self.min_spin - self.min_d)
        # Speed the wheels really do at the floor duty: v_floor when driving straight, w_floor
        # (as a wheel speed) for a pure in-place spin, blended by t. Divided by the odometry
        # scales so /cmd_vel_applied reports the real floor speed.
        nf_lin = self.vfloor / self.ls
        nf_ang = (self.wfloor / self.as_) * self.sep / 2.0
        nf = min(((1.0 - t) * nf_lin + t * nf_ang) / self.vmax, 0.99)
        if self.tab is not None:
            tl, tr = self.tab_to_duty(nl * self.vmax, t), self.tab_to_duty(nr * self.vmax, t)
        else:
            tl, tr = self.to_duty(nl, floor, nf), self.to_duty(nr, floor, nf)

        step = self.slew * self.dt
        self.cur_l += max(-step, min(step, tl - self.cur_l))
        self.cur_r += max(-step, min(step, tr - self.cur_r))
        if not self.dry:
            tnow = now.nanoseconds * 1e-9
            fl, rl = self._motor_duties(0, self.cur_l, self._kicking(0, self.cur_l, tnow))
            fr, rr = self._motor_duties(1, self.cur_r, self._kicking(1, self.cur_r, tnow))
            try:
                # motors_l = [FL, RL], motors_r = [FR, RR] (see __init__)
                self.motors_l[0].set(fl); self.motors_l[1].set(rl)
                self.motors_r[0].set(fr); self.motors_r[1].set(rr)
            except OSError as e:
                # An I2C error used to propagate out of spin() and kill this node.
                # Keep running, log it, and skip /cmd_vel_applied this cycle (the write
                # was not delivered, so odometry must not integrate it).
                self.get_logger().warn(f'PCA9685 write failed: {e}', throttle_duration_sec=1.0)
                return

        # Reconstruct what the wheels are really being told to do (inverse of to_duty)
        if self.tab is not None:
            al, ar = self.tab_from_duty(self.cur_l, t), self.tab_from_duty(self.cur_r, t)
        else:
            al, ar = self.from_duty(self.cur_l, floor, nf) * self.vmax, self.from_duty(self.cur_r, floor, nf) * self.vmax
        al, ar = al / self.trim[0], ar / self.trim[1]            # undo the trim: report the real wheel speed
        out = Twist()
        out.linear.x = (al + ar) / 2.0 * self.ls
        out.angular.z = (ar - al) / self.sep * self.as_
        self.pub.publish(out)

    def stop(self):
        if self.pca is not None:
            for mo in self.motors_l + self.motors_r:
                try:
                    mo.set(0.0)
                except OSError as e:
                    self.get_logger().error(f'could not zero a motor on shutdown: {e}')
            try:
                self.pca.deinit()
            except OSError:
                pass


def main():
    rclpy.init()
    n = MotorDriver()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.stop()
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
