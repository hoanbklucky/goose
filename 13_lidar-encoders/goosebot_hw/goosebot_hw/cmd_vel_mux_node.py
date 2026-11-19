#!/usr/bin/env python3
"""
Priority mux so teleop, Nav2 and the old YOLO lane follower can coexist.
  /cmd_vel_teleop  (highest)
  /cmd_vel         (Nav2 output)
  /cmd_vel_lane    (old control_node; remap its output here)
Output: /cmd_vel_mux -> motor_driver. A source is ignored if older than `timeout`.
If nothing is fresh it publishes zero (so the robot stops if Nav2 dies).
lane_angular_sign: the old stack used +z = RIGHT turn. -1.0 converts to REP-103
(VERIFY on the bench -- I could not confirm the sign of the old lane error from the code).
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class Mux(Node):
    def __init__(self):
        super().__init__('cmd_vel_mux')
        self.declare_parameter('timeout', 0.5)
        self.declare_parameter('lane_angular_sign', -1.0)
        self.timeout = self.get_parameter('timeout').value
        self.lsign = self.get_parameter('lane_angular_sign').value
        self.srcs = {}   # name -> (Twist, time)
        for name, topic in (('teleop', '/cmd_vel_teleop'), ('nav', '/cmd_vel'),
                            ('lane', '/cmd_vel_lane')):
            self.create_subscription(Twist, topic, lambda m, n=name: self.cb(n, m), 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel_mux', 10)
        self.create_timer(0.05, self.tick)

    def cb(self, name, msg):
        if name == 'lane':
            msg.angular.z *= self.lsign
        self.srcs[name] = (msg, self.get_clock().now())

    def tick(self):
        now = self.get_clock().now()
        for name in ('teleop', 'nav', 'lane'):
            if name in self.srcs:
                msg, t = self.srcs[name]
                if (now - t).nanoseconds * 1e-9 < self.timeout:
                    self.pub.publish(msg)
                    return
        self.pub.publish(Twist())


def main():
    rclpy.init()
    n = Mux()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
