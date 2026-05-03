# control_node.py
# Subscribes: /lane/offset
# Publishes: /cmd_vel

import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Bool
from geometry_msgs.msg import Twist

from goose_ros2.config import Kp, Kd, BASE_SPEED, MAX_STEER, STOP_DURATION


class ControlNode(Node):

    def __init__(self):
        super().__init__('control_node')

        self.prev_error = 0.0
        self.stop_requested = False
        self.last_stop_time = 0.0

        self.create_subscription(Float32, '/lane/error', self.error_callback, 10)
        self.create_subscription(Bool, '/stop_requested', self.stop_callback, 10)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def stop_callback(self, msg):
        self.stop_requested = msg.data

    def error_callback(self, msg):
        twist = Twist()

        if self.stop_requested:
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.cmd_pub.publish(twist)
            time.sleep(STOP_DURATION)
            self.stop_requested = False
            return

        error = msg.data
        derivative = error - self.prev_error
        self.prev_error = error

        steering = (error * Kp) + (derivative * Kd)
        steering = max(min(steering, MAX_STEER), -MAX_STEER)

        twist.linear.x = BASE_SPEED
        twist.angular.z = steering

        self.cmd_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
