# web_stream_node

import threading
import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from flask import Flask, Response

from goose_ros2.config import HOST_IP, HOST_PORT

app = Flask(__name__)

latest_frame = None
frame_lock = threading.Lock()


class WebStreamNode(Node):
    def __init__(self):
        super().__init__('web_stream_node')

        self.subscription = self.create_subscription(
            CompressedImage,
            '/camera/debug/compressed',
            self.image_callback,
            1
        )

        self.get_logger().info('Web stream node started')

    def image_callback(self, msg):
        global latest_frame

        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                return

            with frame_lock:
                latest_frame = buffer.tobytes()

        except Exception as e:
            self.get_logger().error(f'Failed to process frame: {e}')


@app.route('/')
def index():
    return """
    <html>
      <head>
        <title>Goose Camera Stream</title>
      </head>
      <body>
        <h1>Goose Camera Stream</h1>
        <img src='/video_feed' width='800'>
      </body>
    </html>
    """


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


def generate_frames():
    global latest_frame

    while True:
        with frame_lock:
            frame = latest_frame

        if frame is None:
            time.sleep(0.05)
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
        )


def main(args=None):
    rclpy.init(args=args)

    ros_node = WebStreamNode()

    ros_thread = threading.Thread(
        target=rclpy.spin,
        args=(ros_node,),
        daemon=True
    )
    ros_thread.start()

    print('Starting Web Server at http://0.0.0.0:5000')

    try:
        app.run(
            host=HOST_IP,
            port=HOST_PORT,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        pass
    finally:
        ros_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
