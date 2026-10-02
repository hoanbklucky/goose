#!/usr/bin/env python3
"""
Republishes Gazebo's CameraInfo for a simulated stereo pair with a proper
rectified-stereo projection matrix.

Why this exists: gz camera_info carries the intrinsics (K) but no stereo
baseline term, so P[0,3] (Tx) is 0 on both cameras. Stereo consumers that
read the baseline from the right camera's P matrix (the ROS convention:
Tx = -fx * baseline) would see a zero baseline and produce no depth.

The simulated imagers are parallel and distortion-free, so the images are
already rectified: D = [], R = I, P = [K | 0] for the left camera and
P = [K | (-fx*B, 0, 0)] for the right one.

Subscribes : stereo/left/camera_info_raw,  stereo/right/camera_info_raw
Publishes  : stereo/left/camera_info,      stereo/right/camera_info
Parameters : baseline (double, m, must match stereo_baseline in the xacro)
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo


class StereoCameraInfoFixer(Node):
    def __init__(self):
        super().__init__('stereo_camera_info_fixer')
        self.declare_parameter('baseline', 0.09)
        self.baseline = float(self.get_parameter('baseline').value)

        self.pubs = {}
        for side in ('left', 'right'):
            self.pubs[side] = self.create_publisher(
                CameraInfo, f'stereo/{side}/camera_info', 10)
            self.create_subscription(
                CameraInfo, f'stereo/{side}/camera_info_raw',
                lambda msg, s=side: self.cb(s, msg), 10)
        self.get_logger().info(
            f'Fixing stereo CameraInfo with baseline={self.baseline:.4f} m')

    def cb(self, side, msg):
        out = CameraInfo()
        out.header = msg.header
        out.height = msg.height
        out.width = msg.width
        out.distortion_model = 'plumb_bob'
        out.d = []
        out.k = list(msg.k)
        out.r = [1.0, 0.0, 0.0,
                 0.0, 1.0, 0.0,
                 0.0, 0.0, 1.0]
        fx, cx, fy, cy = msg.k[0], msg.k[2], msg.k[4], msg.k[5]
        tx = -fx * self.baseline if side == 'right' else 0.0
        out.p = [fx, 0.0, cx, tx,
                 0.0, fy, cy, 0.0,
                 0.0, 0.0, 1.0, 0.0]
        out.binning_x = msg.binning_x
        out.binning_y = msg.binning_y
        out.roi = msg.roi
        self.pubs[side].publish(out)


def main():
    rclpy.init()
    node = StereoCameraInfoFixer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
