#!/usr/bin/env python3
"""
scale_check.py

Compares ORB-SLAM3's /slam/odometry against Gazebo's ground-truth wheel
/odom to reveal monocular scale drift.

How to use:
  1. Run this node while SLAM + Gazebo are running.
  2. Drive the robot manually (teleop) in a straight line for a known
     distance, e.g. exactly 1.0m using teleop or by watching /odom.
  3. Watch the printed "ratio" column. If mono SLAM had perfect,
     consistent scale, ratio would stay pinned near some constant value
     for the whole run. If it drifts around over time, that's scale
     drift -- and if it's wildly far from 1.0 in magnitude, note that a
     non-1.0 ratio by itself is FINE (mono SLAM is arbitrary-scale by
     nature) -- what matters is whether the ratio stays roughly constant
     or wanders.

Topics used:
  /slam/odometry   (nav_msgs/Odometry)  -- SLAM's estimate, arbitrary scale
  /odom            (nav_msgs/Odometry)  -- Gazebo ground-truth wheel odom
"""

import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class ScaleCheck(Node):
    def __init__(self):
        super().__init__('scale_check')

        self.slam_start = None
        self.odom_start = None
        self.slam_last = None
        self.odom_last = None

        self.slam_total = 0.0   # cumulative path length, SLAM frame
        self.odom_total = 0.0   # cumulative path length, ground-truth frame

        self.create_subscription(Odometry, '/slam/odometry', self.slam_cb, 10)
        self.create_subscription(Odometry, '/odom', self.odom_cb, 10)

        self.timer = self.create_timer(1.0, self.report)

        self.get_logger().info(
            'scale_check started. Drive the robot manually and watch the ratio column.')

    def slam_cb(self, msg: Odometry):
        p = msg.pose.pose.position
        pt = (p.x, p.y, p.z)
        if self.slam_start is None:
            self.slam_start = pt
        if self.slam_last is not None:
            self.slam_total += dist(self.slam_last, pt)
        self.slam_last = pt

    def odom_cb(self, msg: Odometry):
        p = msg.pose.pose.position
        pt = (p.x, p.y, p.z)
        if self.odom_start is None:
            self.odom_start = pt
        if self.odom_last is not None:
            self.odom_total += dist(self.odom_last, pt)
        self.odom_last = pt

    def report(self):
        if self.slam_last is None or self.odom_last is None:
            self.get_logger().info(
                f'Waiting for data... slam_odom_seen={self.slam_last is not None} '
                f'wheel_odom_seen={self.odom_last is not None}')
            return

        slam_disp = dist(self.slam_start, self.slam_last)   # straight-line displacement
        odom_disp = dist(self.odom_start, self.odom_last)

        ratio_disp = (slam_disp / odom_disp) if odom_disp > 1e-6 else float('nan')
        ratio_path = (self.slam_total / self.odom_total) if self.odom_total > 1e-6 else float('nan')

        self.get_logger().info(
            f'displacement -> slam={slam_disp:.3f}m  wheel={odom_disp:.3f}m  ratio={ratio_disp:.3f}  |  '
            f'path_len -> slam={self.slam_total:.3f}m  wheel={self.odom_total:.3f}m  ratio={ratio_path:.3f}'
        )


def dist(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)


def main():
    rclpy.init()
    node = ScaleCheck()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
