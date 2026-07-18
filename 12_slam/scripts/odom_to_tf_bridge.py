#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped

class OdomToTF(Node):
    def __init__(self):
        super().__init__('odom_to_tf_bridge')
        self.br = TransformBroadcaster(self)
        self.sub = self.create_subscription(
            Odometry, '/slam/odometry', self.callback, 10)
        self.get_logger().info('odom_to_tf_bridge node started, subscribed to /slam/odometry')

    def callback(self, msg: Odometry):
        self.get_logger().info('Received odometry, broadcasting transform')
        try:
            t = TransformStamped()
            t.header.stamp = msg.header.stamp
            t.header.frame_id = 'map'
            t.child_frame_id = 'base_footprint'
            t.transform.translation.x = msg.pose.pose.position.x
            t.transform.translation.y = msg.pose.pose.position.y
            t.transform.translation.z = msg.pose.pose.position.z
            t.transform.rotation = msg.pose.pose.orientation
            self.br.sendTransform(t)
        except Exception as e:
            self.get_logger().error(f'Failed to broadcast transform: {e}')

def main():
    rclpy.init()
    node = OdomToTF()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
