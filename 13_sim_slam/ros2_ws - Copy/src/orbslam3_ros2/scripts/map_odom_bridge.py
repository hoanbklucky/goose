#!/usr/bin/env python3
"""
Publishes the map -> odom transform Nav2 requires.

The SLAM wrapper's /slam/odometry topic is already published with
frame_id: map, child_frame_id: odom -- meaning its pose IS the map->odom
correction directly, not a raw camera pose needing further combination
with wheel odometry. This node just republishes it as a TF broadcast,
since Nav2 needs it on /tf, not as a plain topic.
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


class MapOdomBridge(Node):
    def __init__(self):
        super().__init__('map_odom_bridge')
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.create_subscription(Odometry, '/slam/odometry', self.slam_pose_cb, 10)

    def slam_pose_cb(self, msg: Odometry):
        tf_msg = TransformStamped()
        tf_msg.header.stamp = msg.header.stamp
        tf_msg.header.frame_id = msg.header.frame_id      # 'map'
        tf_msg.child_frame_id = msg.child_frame_id         # 'odom'
        tf_msg.transform.translation.x = msg.pose.pose.position.x
        tf_msg.transform.translation.y = msg.pose.pose.position.y
        tf_msg.transform.translation.z = msg.pose.pose.position.z
        tf_msg.transform.rotation = msg.pose.pose.orientation
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

