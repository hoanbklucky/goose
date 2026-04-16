# control_node.py
# Subscribes: /lane/offset
# Publishes: /cmd_vel

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Twist

class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')

        self.declare_parameter('kp', 0.002)
        self.declare_parameter('base_speed', 0.2)

        self.kp = self.get_parameter('kp').value
        self.base_speed = self.get_parameter('base_speed').value

        self.sub = self.create_subscription(
            Float32, '/lane/offset', self.callback, 10
        )

        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def callback(self, msg):
        offset = msg.data

        twist = Twist()
        twist.linear.x = self.base_speed
        twist.angular.z = -self.kp * offset

        self.pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()