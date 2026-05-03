import time
import cv2
import rclpy
import numpy as np

from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Float32, Bool
from ultralytics import YOLO

from goose_ros2.config import *

class PerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')

        self.lane_error_pub = self.create_publisher(Float32, '/lane/error', 10)
        self.stop_pub = self.create_publisher(Bool, '/stop_requested', 10)
        self.debug_pub = self.create_publisher(
            CompressedImage,
            '/camera/debug/compressed',
            10
        )

        self.last_stop_time = 0.0

        self.model = YOLO(MODEL_PATH, task='detect')

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, 15)

        if not self.cap.isOpened():
            raise RuntimeError('Could not open camera')

        self.timer = self.create_timer(0.1, self.process_frame)

        self.get_logger().info('Perception node started')

    def process_frame(self):

        ok, frame = self.cap.read()

        if not ok or frame is None:
            self.get_logger().warn('Failed to capture frame')
            return

        frame = cv2.flip(frame, 1)

        results = self.model.predict(
            source=frame,
            conf=0.5,
            imgsz=640,
            verbose=False
        )

        result = results[0]
        annotated_frame = result.plot()

        best_y_x = None
        best_w_x = None
        max_y_area = 0
        max_w_area = 0
        stop_requested = False

        current_time = time.time()
        cutoff_pixel = int(CAMERA_HEIGHT * ROI_VERTICAL_CUTOFF)

        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = self.model.names[cls_id]

            x, y, w, h = box.xywh[0].tolist()
            area = w * h

            if cls_name == 'redline':
                if y > STOP_THRESHOLD_Y:
                    if (current_time - self.last_stop_time) > STOP_COOLDOWN:
                        stop_requested = True
                        self.last_stop_time = current_time

            if y < cutoff_pixel:
                continue

            if cls_name == 'yellowline' and area > max_y_area:
                max_y_area = area
                best_y_x = x

            elif cls_name == 'whiteline' and area > max_w_area:
                max_w_area = area
                best_w_x = x

        if best_y_x is not None and best_w_x is not None:
            target_x = (best_y_x + best_w_x) / 2.0
        elif best_y_x is not None:
            target_x = best_y_x + (LANE_WIDTH_PIXELS / 2)
        elif best_w_x is not None:
            target_x = best_w_x - (LANE_WIDTH_PIXELS / 2)
        else:
            target_x = CENTER_X

        error = target_x - CENTER_X

        lane_msg = Float32()
        lane_msg.data = float(error)
        self.lane_error_pub.publish(lane_msg)

        stop_msg = Bool()
        stop_msg.data = stop_requested
        self.stop_pub.publish(stop_msg)

        cv2.circle(
            annotated_frame,
            (int(target_x), cutoff_pixel + 20),
            10,
            (0, 255, 0),
            -1
        )

        cv2.line(
            annotated_frame,
            (int(CENTER_X), 0),
            (int(CENTER_X), CAMERA_HEIGHT),
            (255, 255, 255),
            1
        )

        debug_lines = [
            f'best_w_x: {best_w_x}',
            f'best_y_x: {best_y_x}',
            f'target_x: {target_x:.1f}',
            f'CENTER_X: {CENTER_X:.1f}',
            f'error: {error:.1f}',
            f'stop_requested: {stop_requested}'
        ]

        for i, line in enumerate(debug_lines):
            y_text = 25 + i * 22

            cv2.putText(
                annotated_frame,
                line,
                (10, y_text),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                3,
                cv2.LINE_AA
            )

            cv2.putText(
                annotated_frame,
                line,
                (10, y_text),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        self.publish_debug_frame(annotated_frame)

    def publish_debug_frame(self, frame):
        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.format = 'jpeg'

        success, encoded = cv2.imencode('.jpg', frame)

        if success:
            msg.data = encoded.tobytes()
            self.debug_pub.publish(msg)

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()

        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    node = PerceptionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
