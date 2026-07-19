#!/usr/bin/env python3
"""
Publishes the map -> odom transform Nav2 requires.

Gazebo's diff_drive plugin already publishes odom -> base_footprint from
wheel encoders (drifts over time, but smooth and high-rate). This node
takes ORB-SLAM3's pose estimate (accurate, map-frame, but lower rate) and
computes the correction needed so that map -> odom -> base_footprint lands
exactly on SLAM's estimate -- instead of just overwriting odom with SLAM's
pose directly, which would throw away the wheel odometry entirely.
"""

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


def quat_to_matrix(x, y, z, w):
    """Quaternion -> 4x4 homogeneous rotation matrix (translation left as identity)."""
    n = np.linalg.norm([x, y, z, w])
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2*(y*y+z*z), 2*(x*y-z*w),     2*(x*z+y*w),     0],
        [2*(x*y+z*w),     1 - 2*(x*x+z*z), 2*(y*z-x*w),     0],
        [2*(x*z-y*w),     2*(y*z+x*w),     1 - 2*(x*x+y*y), 0],
        [0, 0, 0, 1]
    ])


def matrix_to_quat(m):
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    return x, y, z, w


def pose_to_matrix(pos, quat):
    m = quat_to_matrix(quat.x, quat.y, quat.z, quat.w)
    m[0, 3], m[1, 3], m[2, 3] = pos.x, pos.y, pos.z
    return m


class MapOdomBridge(Node):
    def __init__(self):
        super().__init__('map_odom_bridge')

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # topic your SLAM wrapper publishes -- adjust if you renamed it
        self.create_subscription(Odometry, '/odom', self.slam_pose_cb, 10)

        self.odom_frame = 'odom'
        self.base_frame = 'base_footprint'
        self.map_frame = 'map'

    def slam_pose_cb(self, msg: Odometry):
        # SLAM's estimate of the camera pose in the map frame
        slam_matrix = pose_to_matrix(msg.pose.pose.position, msg.pose.pose.orientation)

        # current wheel-odometry estimate of odom -> base_footprint
        try:
            t = self.tf_buffer.lookup_transform(
                self.odom_frame, self.base_frame, Time())
        except tf2_ros.TransformException as e:
            self.get_logger().warn(f'No odom->base_footprint yet: {e}')
            return

        odom_to_base = pose_to_matrix(t.transform.translation, t.transform.rotation)

        # map -> odom = (map -> base, from SLAM) * inverse(odom -> base, from wheels)
        map_to_odom = slam_matrix @ np.linalg.inv(odom_to_base)

        x, y, z, w = matrix_to_quat(map_to_odom[:3, :3])

        tf_msg = TransformStamped()
        tf_msg.header.stamp = self.get_clock().now().to_msg()
        tf_msg.header.frame_id = self.map_frame
        tf_msg.child_frame_id = self.odom_frame
        tf_msg.transform.translation.x = float(map_to_odom[0, 3])
        tf_msg.transform.translation.y = float(map_to_odom[1, 3])
        tf_msg.transform.translation.z = float(map_to_odom[2, 3])
        tf_msg.transform.rotation.x = x
        tf_msg.transform.rotation.y = y
        tf_msg.transform.rotation.z = z
        tf_msg.transform.rotation.w = w

        self.tf_broadcaster.sendTransform(tf_msg)


def main():
    rclpy.init()
    node = MapOdomBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
