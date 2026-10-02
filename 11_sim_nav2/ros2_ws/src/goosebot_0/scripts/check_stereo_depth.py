#!/usr/bin/env python3
"""
Compares the distance RTAB-Map's stereo pipeline reports for whatever is
straight ahead against the front ToF's range to the same thing.

In sim the ToF is an exact single-beam range, so it works as a ground-truth
ruler. Run it with the robot STATIONARY, facing a wall 0.5-2 m away, so that
odometry drift cannot contribute: any disagreement is stereo depth error.

  python3 check_stereo_depth.py            # (ROS 2 environment sourced)

Prints, for each obstacle cloud RTAB-Map publishes:
  stereo : median / 10th / 90th percentile forward distance (m) of points
           within +/-15 cm of the robot's forward axis, and the point count
  ToF    : the latest front range (m)
The two medians should agree to a few cm (the camera sits ~5 cm ahead of
base_footprint, so expect a small constant offset). A wide 10th-90th spread
on a flat wall means noisy stereo depth.
"""
import math

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan, PointCloud2
from sensor_msgs_py import point_cloud2 as pc2


class CheckStereoDepth(Node):
    def __init__(self):
        super().__init__('check_stereo_depth')
        self.tof_range = None
        self.frame_reported = False
        self.create_subscription(
            LaserScan, '/tof_front/scan', self.on_tof, qos_profile_sensor_data)
        self.create_subscription(
            PointCloud2, '/rtabmap/local_grid_obstacle', self.on_cloud,
            qos_profile_sensor_data)
        self.get_logger().info(
            'Waiting for /rtabmap/local_grid_obstacle (published when RTAB-Map '
            'adds a node) and /tof_front/scan ...')

    def on_tof(self, msg):
        finite = [r for r in msg.ranges if math.isfinite(r)]
        self.tof_range = min(finite) if finite else None

    def on_cloud(self, msg):
        if not self.frame_reported:
            self.get_logger().info(
                f'cloud frame_id = "{msg.header.frame_id}" '
                '(forward = +x assumed; expected base_footprint)')
            self.frame_reported = True
        pts = pc2.read_points(msg, field_names=['x', 'y'], skip_nans=True)
        x = np.asarray(pts['x'], dtype=float)
        y = np.asarray(pts['y'], dtype=float)
        ahead = x[(x > 0.05) & (np.abs(y) < 0.15)]
        tof = 'none in range' if self.tof_range is None else f'{self.tof_range:.3f} m'
        if ahead.size < 5:
            self.get_logger().info(
                f'stereo: only {ahead.size} points ahead | ToF: {tof}')
            return
        p10, med, p90 = np.percentile(ahead, [10, 50, 90])
        self.get_logger().info(
            f'stereo: median {med:.3f} m  (p10 {p10:.3f}, p90 {p90:.3f}, '
            f'n={ahead.size}) | ToF: {tof}')


def main():
    rclpy.init()
    node = CheckStereoDepth()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
