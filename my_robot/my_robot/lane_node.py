# lane_node.py
# Subscribes: /camera/image_raw
# Publishes: /lane/offset
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from cv_bridge import CvBridge
import cv2
import numpy as np

class LaneNode(Node):
    def __init__(self):
        super().__init__('lane_node')

        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

        self.publisher_ = self.create_publisher(Float32, '/lane/offset', 10)
        self.bridge = CvBridge()

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        # SIMPLE placeholder logic (students replace with their model)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        h, w = thresh.shape
        left = np.sum(thresh[:, :w//2])
        right = np.sum(thresh[:, w//2:])

        offset = float(right - left)

        msg_out = Float32()
        msg_out.data = offset
        self.publisher_.publish(msg_out)