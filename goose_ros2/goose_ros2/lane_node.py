# lane_node.py
# Subscribes: /camera/image_raw
# Publishes: /lane/offset

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from cv_bridge import CvBridge

from .goose_adapter import GooseAdapter

class LaneNode(Node):
    def __init__(self):
        super().__init__('lane_node')

        self.bridge = CvBridge()
        self.adapter = GooseAdapter()

        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.callback, 10
        )

        self.pub_offset = self.create_publisher(Float32, '/lane/offset', 10)

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        offset, angle = self.adapter.process(frame)

        out = Float32()
        out.data = float(offset)
        self.pub_offset.publish(out)

def main(args=None):
    rclpy.init(args=args)
    node = LaneNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

