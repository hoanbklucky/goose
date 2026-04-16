# teleop_node.py
# Teleop Node (Keyboard Override)
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys, tty, termios

class TeleopNode(Node):
    def __init__(self):
        super().__init__('teleop_node')
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)

    def get_key(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch

    def run(self):
        while True:
            key = self.get_key()

            twist = Twist()

            if key == 'w':
                twist.linear.x = 0.2
            elif key == 'a':
                twist.angular.z = 0.5
            elif key == 'd':
                twist.angular.z = -0.5
            elif key == 's':
                twist.linear.x = 0.0
            else:
                break

            self.publisher_.publish(twist)