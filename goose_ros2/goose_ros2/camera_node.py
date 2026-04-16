# camera_node.py
# Publishes: /camera/image_raw
import rclpy
from rclpy.node import Node
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.declare_parameter('camera_index', 0)
        self.declare_parameter('fps', 10)

        idx = self.get_parameter('camera_index').value
        fps = self.get_parameter('fps').value

        self.cap = cv2.VideoCapture(idx)
        self.bridge = CvBridge()

        self.publisher_ = self.create_publisher(Image, '/camera/image_raw', 10)
        self.timer = self.create_timer(1.0 / fps, self.loop)

    def loop(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warning('Camera read failed')
            return

        msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()