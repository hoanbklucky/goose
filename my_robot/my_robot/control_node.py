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

        self.subscription = self.create_subscription(
            Float32,
            '/lane/offset',
            self.callback,
            10
        )

        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)

        self.declare_parameter('kp', 0.001)
        self.kp = self.get_parameter('kp').value

    def callback(self, msg):
        offset = msg.data

        twist = Twist()
        twist.linear.x = 0.2
        twist.angular.z = -self.kp * offset

        self.publisher_.publish(twist)