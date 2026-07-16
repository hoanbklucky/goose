#!/usr/bin/env python3
"""
wall_avoider_slam.py

Reactive obstacle-avoidance behavior driven by the OctoMap that ORB-SLAM3
is building (camera-only robot, no lidar).

Logic:
  - Subscribe to the OctoMap's occupied-voxel point cloud (published as
    sensor_msgs/PointCloud2 in the SLAM/map frame).
  - Use tf2 to find the robot's current pose in that same frame.
  - Transform occupied voxels into the robot's local frame and check
    whether any lie within a forward-facing cone and within
    OBSTACLE_DISTANCE.
  - FORWARD state: drive straight until a voxel is detected ahead -> TURNING.
  - TURNING state: rotate left in place until the cone ahead is clear
    beyond CLEAR_DISTANCE -> FORWARD.

IMPORTANT - things you must verify/adjust for your setup before running:
  1. OCTOMAP_TOPIC below: the exact topic name orbslam3_ros2 publishes the
     occupied-voxel cloud on. Check with:
         ros2 topic list
     Look for something like /octomap_point_cloud_centers,
     /occupied_cells_vis_array (MarkerArray - NOT usable directly here),
     or a custom topic name from the orbslam3_ros2 package/launch file.
     If it's only publishing a MarkerArray, ping me and I'll adapt this
     script to subscribe to that message type instead of PointCloud2.
  2. MAP_FRAME / BASE_FRAME below: the tf frame names actually in use.
     Check with:
         ros2 run tf2_tools view_frames
     (generates frames.pdf) or:
         ros2 topic echo /tf --once
  3. CMD_VEL_TOPIC: confirm with `ros2 topic list`, adjust if namespaced.

Since SLAM map points only populate once the robot sees textured surfaces
(per your README notes), this script will effectively do nothing useful
until the OctoMap has some occupied voxels in front of the robot - drive
towards a textured wall first to confirm mapping is working, e.g. via
rqt_image_view and the Map View window, before trusting this script.
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import PointCloud2
import sensor_msgs_py.point_cloud2 as pc2

import tf2_ros
from tf2_ros import TransformException


# ---- Tunable parameters ----
OCTOMAP_TOPIC = '/octomap_point_cloud_centers'   # VERIFY - see notes above
CMD_VEL_TOPIC = '/cmd_vel'

MAP_FRAME = 'map'          # VERIFY - frame the octomap points are published in
BASE_FRAME = 'base_link'   # VERIFY - robot's base frame

FORWARD_SPEED = 0.15        # m/s
TURN_SPEED = 0.6            # rad/s (positive = left)

OBSTACLE_DISTANCE = 0.8     # meters - stop & turn if a voxel is closer than this, ahead
CLEAR_DISTANCE = 1.2        # meters - must be clear beyond this to resume driving
FRONT_HALF_WIDTH_DEG = 35   # degrees to each side of straight-ahead to consider "ahead"
MIN_HEIGHT = 0.05           # ignore voxels below this height (floor) in the base frame
MAX_HEIGHT = 1.0            # ignore voxels above this height (ceiling/overhangs)


class SlamWallAvoider(Node):
    def __init__(self):
        super().__init__('slam_wall_avoider')

        self.state = 'FORWARD'
        self.front_min_distance = float('inf')

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.cloud_sub = self.create_subscription(
            PointCloud2, OCTOMAP_TOPIC, self.cloud_callback, 10)
        self.cmd_pub = self.create_publisher(Twist, CMD_VEL_TOPIC, 10)

        self.timer = self.create_timer(0.1, self.control_loop)

        self.get_logger().info('slam_wall_avoider node started, waiting for octomap + tf...')

    def cloud_callback(self, msg: PointCloud2):
        try:
            transform = self.tf_buffer.lookup_transform(
                BASE_FRAME, MAP_FRAME, rclpy.time.Time())
        except TransformException as ex:
            self.get_logger().warn(f'tf lookup failed ({BASE_FRAME} <- {MAP_FRAME}): {ex}',
                                    throttle_duration_sec=2.0)
            return

        t = transform.transform.translation
        q = transform.transform.rotation

        # quaternion -> yaw (only need yaw since ground robot is planar)
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)

        min_dist = float('inf')

        for x, y, z in pc2.read_points(msg, field_names=('x', 'y', 'z'), skip_nans=True):
            # transform point from map frame into base frame (2D, planar robot)
            dx = x + t.x
            dy = y + t.y

            local_x = dx * cos_yaw - dy * sin_yaw
            local_y = dx * sin_yaw + dy * cos_yaw

            if z < MIN_HEIGHT or z > MAX_HEIGHT:
                continue

            if local_x <= 0:
                continue  # behind the robot

            distance = math.hypot(local_x, local_y)
            angle_deg = math.degrees(math.atan2(local_y, local_x))

            if -FRONT_HALF_WIDTH_DEG <= angle_deg <= FRONT_HALF_WIDTH_DEG:
                if distance < min_dist:
                    min_dist = distance

        self.front_min_distance = min_dist

    def control_loop(self):
        cmd = Twist()

        if self.state == 'FORWARD':
            if self.front_min_distance < OBSTACLE_DISTANCE:
                self.get_logger().info(
                    f'Obstacle detected at {self.front_min_distance:.2f} m ahead, turning left')
                self.state = 'TURNING'
                cmd.linear.x = 0.0
                cmd.angular.z = TURN_SPEED
            else:
                cmd.linear.x = FORWARD_SPEED
                cmd.angular.z = 0.0

        elif self.state == 'TURNING':
            if self.front_min_distance > CLEAR_DISTANCE:
                self.get_logger().info('Path clear, resuming forward')
                self.state = 'FORWARD'
                cmd.linear.x = FORWARD_SPEED
                cmd.angular.z = 0.0
            else:
                cmd.linear.x = 0.0
                cmd.angular.z = TURN_SPEED

        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = SlamWallAvoider()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stop_cmd = Twist()
        node.cmd_pub.publish(stop_cmd)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
