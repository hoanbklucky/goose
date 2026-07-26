#!/usr/bin/env python3
"""
Super basic reactive navigation: drive forward until the occupancy map shows
a wall ahead, then rotate left in place until the path ahead is clear again.

This is a standalone sanity-check script, NOT a replacement for Nav2. It
proves the camera -> ORB-SLAM3 -> octomap -> /projected_map pipeline
produces usable occupancy data, before you invest time in full Nav2 config.

Run directly (no colcon build needed):
    source ~/ros2_ws/install/setup.bash
    python3 wall_avoider.py
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry


class WallAvoider(Node):
    def __init__(self):
        super().__init__('wall_avoider')

        # --- tuning knobs, adjust freely ---
        self.linear_speed = 0.60       # m/s while driving forward
        self.angular_speed = 1.5       # rad/s while turning left
        self.lookahead_distance = 0.4  # m, how far ahead to check for a wall
        self.occupied_threshold = 65   # occupancy value (0-100) counted as "wall"
        # ------------------------------------

        self.map = None
        self.pose = None  # (x, y, yaw)
        self.state = 'FORWARD'

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(OccupancyGrid, '/projected_map', self.map_cb, 10)
        self.create_subscription(Odometry, '/slam/odometry', self.odom_cb, 10)

        self.timer = self.create_timer(0.1, self.control_loop)  # 10 Hz

    def map_cb(self, msg):
        self.map = msg

    def odom_cb(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        # yaw from quaternion
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        self.pose = (p.x, p.y, yaw)

    def cell_value_at(self, x, y):
        """Look up the occupancy value at a world-frame (x, y) point."""
        if self.map is None:
            return -1
        info = self.map.info
        col = int((x - info.origin.position.x) / info.resolution)
        row = int((y - info.origin.position.y) / info.resolution)
        if col < 0 or col >= info.width or row < 0 or row >= info.height:
            # off the currently mapped area -- treat as unknown, not blocked
            return -1
        index = row * info.width + col
        return self.map.data[index]

    def path_ahead_is_blocked(self):
        if self.pose is None or self.map is None:
            return False  # no data yet, don't block, just don't move either
        x, y, yaw = self.pose
        check_x = x + self.lookahead_distance * math.cos(yaw)
        check_y = y + self.lookahead_distance * math.sin(yaw)
        value = self.cell_value_at(check_x, check_y)
        return value >= self.occupied_threshold  # -1 (unknown) is NOT blocked

    def control_loop(self):
        cmd = Twist()

        if self.pose is None or self.map is None:
            # waiting for first odom/map messages -- stay still
            self.cmd_pub.publish(cmd)
            return

        blocked = self.path_ahead_is_blocked()

        if self.state == 'FORWARD':
            if blocked:
                self.get_logger().info('Wall ahead -- turning left')
                self.state = 'TURNING'
            else:
                cmd.linear.x = self.linear_speed

        elif self.state == 'TURNING':
            if blocked:
                cmd.angular.z = self.angular_speed  # positive = left turn
            else:
                self.get_logger().info('Path clear -- driving forward')
                self.state = 'FORWARD'

        self.cmd_pub.publish(cmd)


def main():
    rclpy.init()
    node = WallAvoider()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
