#!/usr/bin/env python3
"""
Two USB webcams -> /stereo/{left,right}/image_raw + /stereo/{left,right}/camera_info.
Replaces the sim's gz bridge + stereo_camera_info_fixer.py. Rectification is NOT done here:
stereo_image_proc (see hw_bringup.launch.py) consumes these and publishes image_rect_color,
which is what rtabmap's stereo mode expects (the sim images were already rectified, real ones
are not).

Images are published as mono8 (gray): RTAB-Map extracts features from gray anyway, and mono8 is 3x smaller.

Filter layer (goosebot_hw/image_filter.py), applied to the gray frame before publishing, identical on both eyes:
despeckle -> glare (reflection) removal -> gentle shadow / uneven-light correction. Settings come from the
`image_filter:` section of config/slam_params.yaml (read by hw_bringup.launch.py and passed in as `filter.*`
parameters); `enable: false` there restores raw gray. The startup log prints the settings actually in use.

Honest limitations:
  * Two free-running USB webcams are NOT hardware-synchronised. We call grab() on both
    back-to-back then retrieve(), which gets skew down to roughly one USB frame period at best,
    and we stamp both with the SAME time. Fast rotation still produces bad depth.
  * Use stable device paths (udev symlinks / /dev/v4l/by-path/...). /dev/video index order can
    change between boots, which silently swaps left and right.
  * Build the message by hand (no cv_bridge) so there is nothing extra to compile on Debian.
"""
import os
import yaml
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo
import time
import goosebot_hw.image_filter as image_filter_mod
from goosebot_hw.image_filter import FilterParams, ImageFilter


def load_info(path, frame):
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        y = yaml.safe_load(f)
    m = CameraInfo()
    m.header.frame_id = frame
    m.width, m.height = int(y['image_width']), int(y['image_height'])
    m.distortion_model = y.get('distortion_model', 'plumb_bob')
    m.d = [float(v) for v in y['distortion_coefficients']['data']]
    m.k = [float(v) for v in y['camera_matrix']['data']]
    m.r = [float(v) for v in y['rectification_matrix']['data']]
    m.p = [float(v) for v in y['projection_matrix']['data']]
    return m


class Stereo(Node):
    def __init__(self):
        super().__init__('stereo_camera')
        P = self.declare_parameter
        P('left_device', '/dev/v4l/by-path/CHANGE_ME_LEFT')
        P('right_device', '/dev/v4l/by-path/CHANGE_ME_RIGHT')
        P('width', 640); P('height', 480); P('fps', 15)
        P('fourcc', 'MJPG')            # YUYV at 2 cams on one USB2 controller will not fit
        P('exposure_abs', -1)          # >0 : fix manual exposure (V4L2 units); -1 leave auto
        P('latency_s', 0.0)            # subtract known capture latency from the stamp
        P('left_info', ''); P('right_info', '')   # camera_calibration YAMLs
        P('filter_enable', True)
        P('filter_log_period_s', 10.0)  # 0 = never log filter stats
        P('left_frame', 'camera_left_optical_link')
        P('right_frame', 'camera_right_optical_link')
        g = lambda n: self.get_parameter(n).value
        self.caps = []
        for dev in (g('left_device'), g('right_device')):
            cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*g('fourcc')))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, g('width'))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, g('height'))
            cap.set(cv2.CAP_PROP_FPS, g('fps'))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if g('exposure_abs') > 0:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)       # 1 = manual on most UVC drivers
                cap.set(cv2.CAP_PROP_EXPOSURE, g('exposure_abs'))
            if not cap.isOpened():
                raise RuntimeError(f'cannot open {dev}')
            self.caps.append(cap)
        self.info = [load_info(g('left_info'), g('left_frame')),
                     load_info(g('right_info'), g('right_frame'))]
        if None in self.info:
            self.get_logger().warn('camera_info YAML missing: publishing images WITHOUT camera_info. '
                                   'stereo_image_proc/rtabmap will not work until you calibrate.')
        self.filt = ImageFilter(FilterParams.from_node(self)) if g('filter_enable') else None
        self.log_period = g('filter_log_period_s')
        self.last_log = self.get_clock().now()
        self.tick_ms = []          # per-tick PROCESSING time (decode + gray + filter + publish, excludes the grab wait)
        self.fps_budget_ms = 1000.0 / g('fps')
        if self.filt is not None:
            self.get_logger().info(f'image filter ON, code: {image_filter_mod.__file__}')
            self.get_logger().info(f'image filter settings: {self.filt.p.describe()}')
        else:
            self.get_logger().info('image filter OFF (filter_enable false)')
        self.frames = (g('left_frame'), g('right_frame'))
        self.latency = g('latency_s')
        self.pi = [self.create_publisher(Image, f'stereo/{s}/image_raw', qos_profile_sensor_data)
                   for s in ('left', 'right')]
        # camera_info must be RELIABLE (default QoS): image_proc/rectify and rtabmap subscribe to it
        # RELIABLE, and a BEST_EFFORT publisher cannot match them (no camera_info -> no image_rect).
        self.pc = [self.create_publisher(CameraInfo, f'stereo/{s}/camera_info', 10)
                   for s in ('left', 'right')]
        self.create_timer(1.0 / g('fps'), self.tick)

    def tick(self):
        ok = [c.grab() for c in self.caps]      # blocks until the next camera frame arrives: NOT counted as processing
        t_start = time.perf_counter()
        t = self.get_clock().now()
        if not all(ok):
            self.get_logger().warn('grab failed', throttle_duration_sec=2.0)
            return
        stamp = (t - rclpy.duration.Duration(seconds=self.latency)).to_msg()
        for i, cap in enumerate(self.caps):
            ok, frame = cap.retrieve()
            if not ok:
                return
            m = Image()
            m.header.stamp = stamp
            m.header.frame_id = self.frames[i]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)   # rtabmap uses gray features; mono8 is 3x smaller than bgr8
            if self.filt is not None:
                gray = self.filt(gray)
            m.height, m.width = gray.shape
            m.encoding = 'mono8'
            m.step = m.width
            m.data = gray.tobytes()
            self.pi[i].publish(m)
            if self.info[i] is not None:
                self.info[i].header.stamp = stamp
                self.pc[i].publish(self.info[i])
        self.tick_ms.append((time.perf_counter() - t_start) * 1000.0)
        if self.log_period > 0 and (t - self.last_log).nanoseconds * 1e-9 > self.log_period:
            self.last_log = t
            ms = self.tick_ms
            self.tick_ms = []
            msg = (f'timing: processing avg {sum(ms) / len(ms):.1f} ms, max {max(ms):.1f} ms per frame pair '
                   f'(frame period {self.fps_budget_ms:.1f} ms), {len(ms) / self.log_period:.1f} frame pairs/s')
            if self.filt is not None:
                msg += f'; glare {self.filt.last_glare_frac * 100:.1f}%'
            if sum(ms) / len(ms) > 0.6 * self.fps_budget_ms:
                msg += '  <-- processing is using most of the frame period: rate will drop (try norm_downscale 8, or enable false)'
            self.get_logger().info(msg)


def main():
    rclpy.init()
    n = Stereo()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        for c in n.caps:
            c.release()
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
