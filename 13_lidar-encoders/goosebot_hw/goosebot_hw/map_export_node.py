#!/usr/bin/env python3
"""
Keeps NAME.yaml + NAME.pgm (the grid Nav2's map_server loads) up to date from /rtabmap/map.

Writes every `period_s` seconds if the map changed, and once more on shutdown, so a crash loses at most
`period_s` of mapping and a clean Ctrl+C always gets the final map. Started by hw_robot.launch.py whenever a map
is being written. Parameters: prefix (path without extension), period_s, topic.
"""
import hashlib
import math

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from goosebot_hw.map_session import write_map

try:
    from rclpy.executors import ExternalShutdownException
except ImportError:                      # older rclpy
    class ExternalShutdownException(Exception):
        pass


class Exporter(Node):
    def __init__(self):
        super().__init__('map_export')
        self.declare_parameter('prefix', '')
        self.declare_parameter('period_s', 30.0)
        self.declare_parameter('topic', '/rtabmap/map')
        self.prefix = self.get_parameter('prefix').value
        if not self.prefix:
            raise RuntimeError('map_export: parameter "prefix" is required')
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.latest = None
        self.last_sig = None
        self.create_subscription(OccupancyGrid, self.get_parameter('topic').value, self.on_map, qos)
        self.create_timer(float(self.get_parameter('period_s').value), self.flush)
        self.get_logger().info(f'exporting {self.get_parameter("topic").value} -> {self.prefix}.yaml/.pgm')

    def on_map(self, msg):
        self.latest = msg

    def flush(self):
        m = self.latest
        if m is None:
            return
        i = m.info
        sig = (i.width, i.height, i.resolution, i.origin.position.x, i.origin.position.y,
               hashlib.md5(bytes(m.data)).hexdigest())
        if sig == self.last_sig:
            return
        q = i.origin.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        write_map(self.prefix, i.width, i.height, i.resolution,
                  i.origin.position.x, i.origin.position.y, yaw, m.data)
        self.last_sig = sig
        self.get_logger().info(f'map written ({i.width}x{i.height})', throttle_duration_sec=60.0)


def main():
    rclpy.init()
    n = Exporter()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            n.flush()                    # final write: uses the last map received, needs no live ROS
        except Exception as e:           # noqa: BLE001
            print(f'map_export: final write failed: {e}')
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
