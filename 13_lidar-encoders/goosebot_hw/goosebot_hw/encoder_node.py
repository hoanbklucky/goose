#!/usr/bin/env python3
"""
Front-wheel hall encoders -> nav_msgs/Odometry on /wheel/odom (measured wheel speed, replaces open-loop cmd_vel odometry
in the EKF; see config/encoder_params.yaml and README "Wheel encoders").

Hardware (GOOSEBOT_TODO A2): FL encoder A/B on gpiochip1 lines 5/8 (pins 16/18), FR encoder A/B on lines 13/4
(pins 22/26), 3.3 V. The rear motors have no encoders.

What is published:
  twist.linear.x  = mean of the two front wheel speeds * linear_scale. This is what the EKF fuses (odom0, vx only).
  twist.angular.z = (right - left) / wheel_separation * angular_scale. Published for comparison only, with a large
                    covariance: skid-steer wheels slip sideways in every turn, so encoder yaw rate reads wrong. The gyro
                    owns yaw rate in the EKF.
  pose            = integration of the above (frame odom, child base_footprint). NOT fused (the EKF config only takes
                    vx); useful for comparing against the 2 m square.
No TF is published: the EKF owns odom -> base_footprint.

Calibration (README): counts_per_rev MUST be measured with scripts/encoder_check.py; the node refuses to start while it
is 0, because a guessed value gives a wrong distance scale that nothing downstream can detect. fl_sign / fr_sign make
forward motion count up on both sides.
"""
import collections
import math

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node

from goosebot_hw.quadrature import Encoders


class EncoderNode(Node):
    def __init__(self):
        super().__init__('encoder_node')
        P = self.declare_parameter
        P('chip', '/dev/gpiochip1')
        P('fl_lines', [5, 8])           # [A, B] line offsets on `chip`
        P('fr_lines', [13, 4])
        P('fl_sign', 1)                 # +1 / -1 so that driving FORWARD counts UP (encoder_check.py)
        P('fr_sign', -1)
        P('counts_per_rev', 0)          # x4 counts per WHEEL revolution. 0 = not calibrated -> node exits
        P('wheel_radius', 0.03305)      # m, same as the URDF (66.1 mm caliper)
        P('wheel_separation', 0.137)    # m, only for the (not fused) yaw rate
        P('linear_scale', 1.0)          # measured / encoder distance on the 1 m drive test (slip, tyre squash)
        P('angular_scale', 1.0)
        P('rate', 20.0)                 # Hz publish rate
        P('window_s', 0.1)              # speed is averaged over this long (quantization vs lag)
        P('vx_var', 0.01)               # (m/s)^2 forward speed variance given to the EKF
        P('wz_var', 0.5)                # (rad/s)^2 yaw rate variance (large on purpose, not fused)
        P('odom_topic', '/wheel/odom')
        P('odom_frame', 'odom')
        P('base_frame', 'base_footprint')
        P('error_warn_fraction', 0.01)  # warn if more than this fraction of edges were missed
        g = lambda n: self.get_parameter(n).value

        self.cpr = int(g('counts_per_rev'))
        if self.cpr <= 0:
            raise RuntimeError('encoder_node: counts_per_rev is 0 (not calibrated). Run scripts/encoder_check.py, '
                               'turn a wheel exactly 10 turns, and put the counts per turn in encoder_params.yaml. '
                               'Or launch with with_encoders:=false.')
        self.m_per_count = 2.0 * math.pi * g('wheel_radius') / self.cpr
        self.sign = {'fl': int(g('fl_sign')), 'fr': int(g('fr_sign'))}
        self.sep, self.ls, self.as_ = g('wheel_separation'), g('linear_scale'), g('angular_scale')
        self.window = g('window_s')
        self.vx_var, self.wz_var = g('vx_var'), g('wz_var')
        self.err_frac = g('error_warn_fraction')
        self.odom_frame, self.base_frame = g('odom_frame'), g('base_frame')

        fl, fr = list(g('fl_lines')), list(g('fr_lines'))
        self.enc = Encoders(g('chip'), {'fl': (fl[0], fl[1]), 'fr': (fr[0], fr[1])}, consumer='goosebot_encoder_node')
        self.get_logger().info(
            f"encoders on {g('chip')}: FL A/B {fl}, FR A/B {fr}; libgpiod {'v2' if self.enc.v2 else 'v1'}; "
            f"{self.cpr} counts/rev = {self.m_per_count * 1000:.3f} mm/count")

        self.hist = collections.deque()        # (t, left_m, right_m)
        self.x = self.y = self.th = 0.0
        self.last_l = self.last_r = None
        self.last_err_report = (0, 0)
        self.pub = self.create_publisher(Odometry, g('odom_topic'), 10)
        self.create_timer(1.0 / g('rate'), self.tick)
        self.create_timer(10.0, self.report)

    def distances(self):
        s = self.enc.snapshot()
        return (s['fl'][0] * self.sign['fl'] * self.m_per_count,
                s['fr'][0] * self.sign['fr'] * self.m_per_count)

    def tick(self):
        if self.enc.error is not None:
            self.get_logger().error(f'encoder reader thread died: {self.enc.error!r}', throttle_duration_sec=5.0)
            return
        now = self.get_clock().now()
        t = now.nanoseconds * 1e-9
        dl, dr = self.distances()
        self.hist.append((t, dl, dr))
        while len(self.hist) > 2 and t - self.hist[0][0] > self.window:
            self.hist.popleft()
        t0, l0, r0 = self.hist[0]
        dt = t - t0
        vl = (dl - l0) / dt if dt > 0 else 0.0
        vr = (dr - r0) / dt if dt > 0 else 0.0
        vx = (vl + vr) / 2.0 * self.ls
        wz = (vr - vl) / self.sep * self.as_

        # pose (comparison only): integrate the step since the last tick
        if self.last_l is not None:
            sl, sr = dl - self.last_l, dr - self.last_r
            ds = (sl + sr) / 2.0 * self.ls
            dth = (sr - sl) / self.sep * self.as_
            self.x += ds * math.cos(self.th + dth / 2.0)
            self.y += ds * math.sin(self.th + dth / 2.0)
            self.th = math.atan2(math.sin(self.th + dth), math.cos(self.th + dth))
        self.last_l, self.last_r = dl, dr

        m = Odometry()
        m.header.stamp = now.to_msg()
        m.header.frame_id = self.odom_frame
        m.child_frame_id = self.base_frame
        m.pose.pose.position.x, m.pose.pose.position.y = self.x, self.y
        m.pose.pose.orientation.z, m.pose.pose.orientation.w = math.sin(self.th / 2.0), math.cos(self.th / 2.0)
        pc = [0.0] * 36
        pc[0] = pc[7] = 0.1
        pc[14] = pc[21] = pc[28] = 1e6
        pc[35] = 1.0
        m.pose.covariance = pc
        m.twist.twist.linear.x = vx
        m.twist.twist.angular.z = wz
        tc = [0.0] * 36
        tc[0] = self.vx_var
        tc[7] = tc[14] = tc[21] = tc[28] = 1e6
        tc[35] = self.wz_var
        m.twist.covariance = tc
        self.pub.publish(m)

    def report(self):
        s = self.enc.snapshot()
        for n in ('fl', 'fr'):
            count, err, edges = s[n]
            if edges and err / edges > self.err_frac:
                self.get_logger().warn(f'{n}: {err} missed edges out of {edges} ({100.0 * err / edges:.1f}%). '
                                       f'Distance reads short. CPU overload or noise on the encoder lines.')

    def destroy_node(self):
        try:
            self.enc.close()
        finally:
            super().destroy_node()


def main():
    rclpy.init()
    n = None
    try:
        n = EncoderNode()
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        if n is not None:
            n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
