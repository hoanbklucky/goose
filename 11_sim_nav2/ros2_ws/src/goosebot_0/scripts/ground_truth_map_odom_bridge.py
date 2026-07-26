#!/usr/bin/env python3
"""
Publishes the map -> odom transform Nav2 requires, using Gazebo's
ground-truth pose instead of live SLAM.

map->odom = (map->base_link)_groundtruth composed with the inverse of
(odom->base_link)_wheelodom. This keeps localization exact even as wheel
odom drifts, and matches Nav2's expected map/odom/base_link TF chain
without needing AMCL or a saved-map + particle filter.

Quaternion<->matrix math is implemented inline (no tf_transformations /
transforms3d dependency) since the apt-packaged transforms3d build breaks
under NumPy 2.0 (calls the removed np.maximum_sctype).
"""

import numpy as np
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


def quaternion_matrix(q):
    """q = [x, y, z, w] -> 4x4 homogeneous rotation matrix."""
    x, y, z, w = q
    n = x*x + y*y + z*z + w*w
    if n < 1e-12:
        return np.identity(4)
    s = 2.0 / n
    X, Y, Z = x*s, y*s, z*s
    wX, wY, wZ = w*X, w*Y, w*Z
    xX, xY, xZ = x*X, x*Y, x*Z
    yY, yZ, zZ = y*Y, y*Z, z*Z
    m = np.identity(4)
    m[0, 0] = 1.0 - (yY + zZ); m[0, 1] = xY - wZ;       m[0, 2] = xZ + wY
    m[1, 0] = xY + wZ;         m[1, 1] = 1.0 - (xX + zZ); m[1, 2] = yZ - wX
    m[2, 0] = xZ - wY;         m[2, 1] = yZ + wX;       m[2, 2] = 1.0 - (xX + yY)
    return m


def quaternion_from_matrix(m):
    """3x3 (or 4x4, upper-left 3x3 used) rotation matrix -> [x, y, z, w]."""
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        S = np.sqrt(tr + 1.0) * 2
        w = 0.25 * S
        x = (m[2, 1] - m[1, 2]) / S
        y = (m[0, 2] - m[2, 0]) / S
        z = (m[1, 0] - m[0, 1]) / S
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        S = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / S
        x = 0.25 * S
        y = (m[0, 1] + m[1, 0]) / S
        z = (m[0, 2] + m[2, 0]) / S
    elif m[1, 1] > m[2, 2]:
        S = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / S
        x = (m[0, 1] + m[1, 0]) / S
        y = 0.25 * S
        z = (m[1, 2] + m[2, 1]) / S
    else:
        S = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / S
        x = (m[0, 2] + m[2, 0]) / S
        y = (m[1, 2] + m[2, 1]) / S
        z = 0.25 * S
    return np.array([x, y, z, w])


def pose_to_matrix(pose):
    t = pose.position
    q = pose.orientation
    m = quaternion_matrix([q.x, q.y, q.z, q.w])
    m[0:3, 3] = [t.x, t.y, t.z]
    return m


class GroundTruthMapOdomBridge(Node):
    def __init__(self):
        super().__init__('ground_truth_map_odom_bridge')
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.latest_odom = None
        self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.create_subscription(Odometry, '/ground_truth/pose', self.gt_cb, 10)

    def odom_cb(self, msg: Odometry):
        self.latest_odom = msg

    def gt_cb(self, msg: Odometry):
        if self.latest_odom is None:
            return

        map_to_base = pose_to_matrix(msg.pose.pose)
        odom_to_base = pose_to_matrix(self.latest_odom.pose.pose)
        map_to_odom = map_to_base @ np.linalg.inv(odom_to_base)

        trans = map_to_odom[0:3, 3]
        quat = quaternion_from_matrix(map_to_odom[0:3, 0:3])

        tf_msg = TransformStamped()
        tf_msg.header.stamp = msg.header.stamp
        tf_msg.header.frame_id = 'map'
        tf_msg.child_frame_id = 'odom'
        tf_msg.transform.translation.x = float(trans[0])
        tf_msg.transform.translation.y = float(trans[1])
        tf_msg.transform.translation.z = float(trans[2])
        tf_msg.transform.rotation.x = float(quat[0])
        tf_msg.transform.rotation.y = float(quat[1])
        tf_msg.transform.rotation.z = float(quat[2])
        tf_msg.transform.rotation.w = float(quat[3])
        self.tf_broadcaster.sendTransform(tf_msg)


def main():
    rclpy.init()
    node = GroundTruthMapOdomBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
