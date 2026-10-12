#!/usr/bin/env python3
"""
Shows where the robot's heading in RViz goes wrong, by comparing how much the
robot has ROTATED (total degrees since this script started) according to:

  truth : Gazebo ground truth  (/ground_truth/pose, sim only)
  odom  : the EKF             (TF odom -> base_footprint)
  map   : EKF + RTAB-Map      (TF map  -> base_footprint)  <- what RViz shows

Using rotation since start (not absolute yaw) removes constant offsets such
as the spawn yaw, so what remains is real disagreement. Start the script with
the robot stationary, then teleop: turn in place, drive around, etc.

  python3 check_heading.py        # (ROS 2 environment sourced)

How to read the output:
  * odom tracks truth, map does not   -> RTAB-Map's map->odom correction is
                                         rotating the robot (bad loop closure)
  * odom and map both differ from
    truth by a steady ratio           -> the EKF heading (gyro) is mis-scaled
  * all three agree here but RViz
    still looks rotated               -> constant offset from the start
    (e.g. spawned with yaw != 0), not a tracking problem
"""
import math

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


class Tracker:
    """Accumulates unwrapped rotation from successive yaw samples."""

    def __init__(self):
        self.last = None
        self.total = 0.0

    def update(self, yaw):
        if self.last is not None:
            self.total += wrap(yaw - self.last)
        self.last = yaw
        return math.degrees(self.total)


class CheckHeading(Node):
    def __init__(self):
        super().__init__('check_heading')
        self.gt_yaw = None
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_subscription(Odometry, '/ground_truth/pose', self.on_gt, 10)
        self.trk = {'truth': Tracker(), 'odom': Tracker(), 'map': Tracker()}
        self.create_timer(0.5, self.tick)  # sample fast enough to track turns

    def on_gt(self, msg):
        self.gt_yaw = yaw_of(msg.pose.pose.orientation)

    def lookup_yaw(self, parent):
        try:
            t = self.tf_buffer.lookup_transform(parent, 'base_footprint', Time())
            return yaw_of(t.transform.rotation)
        except Exception:
            return None

    def tick(self):
        yaws = {'truth': self.gt_yaw,
                'odom': self.lookup_yaw('odom'),
                'map': self.lookup_yaw('map')}
        if any(v is None for v in yaws.values()):
            missing = [k for k, v in yaws.items() if v is None]
            self.get_logger().info(f'waiting for: {", ".join(missing)}')
            return
        rot = {k: self.trk[k].update(v) for k, v in yaws.items()}
        self.get_logger().info(
            f'rotated since start -- truth {rot["truth"]:8.1f} deg | '
            f'odom {rot["odom"]:8.1f} ({rot["odom"] - rot["truth"]:+.1f}) | '
            f'map {rot["map"]:8.1f} ({rot["map"] - rot["truth"]:+.1f})')


def main():
    rclpy.init()
    node = CheckHeading()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
