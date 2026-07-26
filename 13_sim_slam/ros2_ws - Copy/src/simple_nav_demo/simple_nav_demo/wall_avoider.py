#!/usr/bin/env python3
"""
Super basic reactive navigation: drive forward until the occupancy map shows
a wall ahead, then rotate left in fixed increments -- tracked directly via
IMU yaw, not by re-checking the map every tick -- until the path ahead is
clear again.

This is a standalone sanity-check script, NOT a replacement for Nav2.
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import Imu


def normalize_angle(angle):
    """Wrap an angle to [-pi, pi] -- handles the wraparound at +/-180 deg."""
    return math.atan2(math.sin(angle), math.cos(angle))


def yaw_from_quat(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class WallAvoider(Node):
    def __init__(self):
        super().__init__('wall_avoider')

        # --- tuning knobs, adjust freely ---
        self.linear_speed = 0.15       # m/s while driving forward
        self.angular_speed = 0.4       # rad/s while turning left
        self.lookahead_distance = 0.4  # m, how far ahead to check for a wall
        self.occupied_threshold = 65   # occupancy value (0-100) counted as "wall"
        self.turn_increment = math.radians(30)  # turn this much per increment
        # ------------------------------------

        self.map = None
        self.pose = None       # (x, y, yaw) from SLAM, used for map lookahead checks
        self.imu_yaw = None    # current yaw from IMU, used for turn tracking
        self.turn_start_yaw = None
        self.state = 'FORWARD'

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(OccupancyGrid, '/projected_map', self.map_cb, 10)
        self.create_subscription(Odometry, '/slam/odometry', self.odom_cb, 10)
        self.create_subscription(Imu, '/imu/data', self.imu_cb, 10)

        self.timer = self.create_timer(0.1, self.control_loop)  # 10 Hz

    def map_cb(self, msg):
        self.map = msg

    def odom_cb(self, msg):
        p = msg.pose.pose.position
        yaw = yaw_from_quat(msg.pose.pose.orientation)
        self.pose = (p.x, p.y, yaw)

    def imu_cb(self, msg):
        self.imu_yaw = yaw_from_quat(msg.orientation)

    def cell_value_at(self, x, y):
        if self.map is None:
            return -1
        info = self.map.info
        col = int((x - info.origin.position.x) / info.resolution)
        row = int((y - info.origin.position.y) / info.resolution)
        if col < 0 or col >= info.width or row < 0 or row >= info.height:
            return -1
        index = row * info.width + col
        return self.map.data[index]

    def path_ahead_is_blocked(self):
        if self.pose is None or self.map is None:
            return False
        x, y, yaw = self.pose
        check_x = x + self.lookahead_distance * math.cos(yaw)
        check_y = y + self.lookahead_distance * math.sin(yaw)
        value = self.cell_value_at(check_x, check_y)
        return value >= self.occupied_threshold

    def control_loop(self):
        cmd = Twist()

        if self.pose is None or self.map is None or self.imu_yaw is None:
            self.cmd_pub.publish(cmd)
            return

        if self.state == 'FORWARD':
            if self.path_ahead_is_blocked():
                self.get_logger().info('Wall ahead -- starting turn increment')
                self.state = 'TURNING'
                self.turn_start_yaw = self.imu_yaw
            else:
                cmd.linear.x = self.linear_speed

        elif self.state == 'TURNING':
            turned = abs(normalize_angle(self.imu_yaw - self.turn_start_yaw))
            if turned < self.turn_increment:
                cmd.angular.z = self.angular_speed  # positive = left turn
            else:
                # completed this increment -- go re-check the map, not the IMU
                self.get_logger().info('Turn increment complete -- rechecking map')
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
