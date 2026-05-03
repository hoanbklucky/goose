import sys
import select
import termios
import tty
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32


class KeyboardNode(Node):
    def __init__(self):
        super().__init__('keyboard_node')

        self.stop_pub = self.create_publisher(Bool, '/stop_requested', 10)
        self.lane_pub = self.create_publisher(Float32, '/lane/error', 10)

        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        self.timer = self.create_timer(0.05, self.check_keyboard)

        self.get_logger().info('Press q to stop robot and shutdown')

    def check_keyboard(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)

            if key == 'q':
                self.get_logger().info('Q pressed')

                stop_msg = Bool()
                stop_msg.data = True
                self.stop_pub.publish(stop_msg)

                lane_msg = Float32()
                lane_msg.data = 0.0
                self.lane_pub.publish(lane_msg)

                time.sleep(0.5)

                rclpy.shutdown()

    def destroy_node(self):
        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            self.old_settings
        )
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    node = KeyboardNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
