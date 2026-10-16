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
        P('max_duty', 0.85)                 # see docstring about L298N drop
        P('max_duty_rate', 3.0)             # duty/s slew limit (protects driver, avoids wheelspin)
        P('cmd_timeout', 0.5)               # s
        P('linear_scale', 1.0)              # measured/commanded distance ratio
        P('angular_scale', 1.0)             # measured/commanded rotation ratio
        P('rate', 50.0)
        # channel mapping from your 04_motor_test notes: FL 0/1, RL 2/3, RR 4/5, FR 6/7
        P('fl', [0, 1]); P('rl', [2, 3]); P('rr', [4, 5]); P('fr', [6, 7])
        P('invert_left', False); P('invert_right', False)

        g = lambda n: self.get_parameter(n).value
        self.sep = g('wheel_separation'); self.vmax = g('v_max')
        self.min_d = g('min_duty'); self.max_d = g('max_duty')
        self.slew = g('max_duty_rate'); self.timeout = g('cmd_timeout')
        self.ls = g('linear_scale'); self.as_ = g('angular_scale')
        self.dry = g('dry_run')

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
        self.create_subscription(Twist, g('cmd_vel_in'), self.cb, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel_applied', 10)
        self.dt = 1.0 / g('rate')
        self.create_timer(self.dt, self.tick)
        self.get_logger().info(f'motor_driver up (dry_run={self.dry}) vmax={self.vmax} '
                               f'duty=[{self.min_d},{self.max_d}]')

    def cb(self, msg):
        self.cmd = msg
        self.last_cmd = self.get_clock().now()

    def to_duty(self, n):
        """normalized wheel speed (-1..1) -> signed duty incl. deadband compensation"""
        if abs(n) < 1e-3:
            return 0.0
        d = self.min_d + min(abs(n), 1.0) * (self.max_d - self.min_d)
        return math.copysign(d, n)

    def from_duty(self, d):
        if abs(d) < 1e-6:
            return 0.0
        return math.copysign(max(0.0, (abs(d) - self.min_d) / (self.max_d - self.min_d)), d)

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
        nl, nr = nl / m, nr / m
        tl, tr = self.to_duty(nl), self.to_duty(nr)

        step = self.slew * self.dt
        self.cur_l += max(-step, min(step, tl - self.cur_l))
        self.cur_r += max(-step, min(step, tr - self.cur_r))
        if not self.dry:
            for mo in self.motors_l:
                mo.set(self.cur_l)
            for mo in self.motors_r:
                mo.set(self.cur_r)

        # Reconstruct what the wheels are really being told to do (inverse of to_duty)
        al, ar = self.from_duty(self.cur_l) * self.vmax, self.from_duty(self.cur_r) * self.vmax
        out = Twist()
        out.linear.x = (al + ar) / 2.0 * self.ls
        out.angular.z = (ar - al) / self.sep * self.as_
        self.pub.publish(out)

    def stop(self):
        if self.pca is not None:
            for mo in self.motors_l + self.motors_r:
                mo.set(0.0)
            self.pca.deinit()


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
