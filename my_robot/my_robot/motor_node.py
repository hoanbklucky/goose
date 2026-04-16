# motor_node.py
# Subscribes: /cmd_vel

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class MotorNode(Node):
    def __init__(self):
        super().__init__('motor_node')

        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.callback,
            10
        )

    def callback(self, msg):
        linear = msg.linear.x
        angular = msg.angular.z

        left_speed = linear - angular
        right_speed = linear + angular

        # TODO: Replace with real motor control
        self.get_logger().info(
            f'Left: {left_speed:.2f}, Right: {right_speed:.2f}'
        )