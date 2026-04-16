# motor_node.py
# Subscribes: /cmd_vel
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class MotorNode(Node):
    def __init__(self):
        super().__init__('motor_node')

        self.sub = self.create_subscription(
            Twist, '/cmd_vel', self.callback, 10
        )

    def callback(self, msg):
        linear = msg.linear.x
        angular = msg.angular.z

        left = linear - angular
        right = linear + angular

        # === STUDENTS CONNECT TO GPIO HERE ===
        self.get_logger().info(f'L: {left:.2f}, R: {right:.2f}')

def main(args=None):
    rclpy.init(args=args)
    node = MotorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

