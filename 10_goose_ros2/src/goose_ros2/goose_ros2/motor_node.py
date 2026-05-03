# motor_node.py
# Subscribes: /cmd_vel
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from goose_ros2.goose_adapter import set_drive


class MotorNode(Node):

    def __init__(self):
        super().__init__('motor_node')

        self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )

    def cmd_callback(self, msg):
        forward = msg.linear.x
        steer = msg.angular.z
        set_drive(forward, steer)


def main(args=None):
    rclpy.init(args=args)
    node = MotorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
