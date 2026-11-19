#!/usr/bin/env python3
"""
RPLIDAR bench check (README Part 6). Run with the lidar node up and the robot on a CLEAR floor (nothing within ~0.5 m):

    python3 scripts/scan_check.py                # 10 s on /scan
    python3 scripts/scan_check.py --near 0.20    # report returns closer than 0.20 m

Prints the scan rate, the frame_id, how many beams are valid, and every return closer than --near metres with its angle
in the ROBOT frame (0 deg = straight ahead, +90 = left). On a clear floor there should be NONE: a near return at a fixed
angle is the robot seeing itself (camera bracket, cable, mount post). Nav2's collision monitor treats those as an
obstacle touching the robot and will refuse to move. Fix the mount (raise the lidar) rather than filtering.
Also prints the closest return overall: put a box straight in front of the robot and check it reads near 0 deg; if it
reads near 180 deg, set lidar_yaw to ${pi} in the URDF (near +/-90: ${pi/2} / ${-pi/2}).
"""
import argparse
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class ScanCheck(Node):
    def __init__(self, topic, near):
        super().__init__('scan_check')
        self.near = near
        self.msgs = []
        self.tf = Buffer()
        self.tl = TransformListener(self.tf, self)
        self.create_subscription(LaserScan, topic, self.cb, qos_profile_sensor_data)

    def cb(self, m):
        self.msgs.append((time.monotonic(), m))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default='/scan')
    ap.add_argument('--seconds', type=float, default=10.0)
    ap.add_argument('--near', type=float, default=0.15, help='report returns closer than this (m)')
    a = ap.parse_args()
    rclpy.init()
    n = ScanCheck(a.topic, a.near)
    t_end = time.monotonic() + a.seconds
    while time.monotonic() < t_end:
        rclpy.spin_once(n, timeout_sec=0.1)
    if len(n.msgs) < 2:
        print(f'FAIL: {len(n.msgs)} messages on {a.topic} in {a.seconds} s. Is the lidar node running? '
              f'Check the port, the baud rate (460800 for C1) and `ros2 topic list`.')
        return
    dt = n.msgs[-1][0] - n.msgs[0][0]
    rate = (len(n.msgs) - 1) / dt if dt > 0 else 0.0
    m = n.msgs[-1][1]
    print(f'rate: {rate:.1f} Hz (C1 typical ~10)   frame_id: {m.header.frame_id}   beams: {len(m.ranges)}   '
          f'range_min/max: {m.range_min:.2f}/{m.range_max:.2f} m')

    yaw_off = 0.0
    try:
        t = n.tf.lookup_transform('base_footprint', m.header.frame_id, rclpy.time.Time())
        yaw_off = yaw_of(t.transform.rotation)
        print(f'TF base_footprint <- {m.header.frame_id}: yaw {math.degrees(yaw_off):.1f} deg '
              f'(angles below are in the robot frame)')
    except Exception as e:
        print(f'WARN: no TF base_footprint <- {m.header.frame_id} ({e}). Is robot_state_publisher running? '
              f'Angles below are in the lidar frame.')

    # aggregate near returns over all scans, by robot-frame angle (1 deg bins)
    near_bins, valid, total = {}, 0, 0
    closest = (float('inf'), 0.0)
    for _, s in n.msgs:
        for i, r in enumerate(s.ranges):
            total += 1
            if not math.isfinite(r) or r <= 0.0:
                continue
            valid += 1
            ang = math.degrees(math.atan2(math.sin(s.angle_min + i * s.angle_increment + yaw_off),
                                          math.cos(s.angle_min + i * s.angle_increment + yaw_off)))
            if r < closest[0]:
                closest = (r, ang)
            if r < a.near:
                b = int(round(ang))
                near_bins[b] = near_bins.get(b, 0) + 1
    print(f'valid returns: {100.0 * valid / max(total, 1):.0f}% of beams')
    print(f'closest return: {closest[0]:.3f} m at {closest[1]:+.0f} deg (0 = ahead, +90 = left)')
    if near_bins:
        print(f'FAIL: returns closer than {a.near} m (robot seeing itself, or something too close):')
        for b in sorted(near_bins):
            print(f'   {b:+4d} deg  x{near_bins[b]}')
    else:
        print(f'OK: nothing closer than {a.near} m')
    n.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
