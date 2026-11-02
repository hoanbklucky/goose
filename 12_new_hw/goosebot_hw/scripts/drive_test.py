#!/usr/bin/env python3
"""
Calibration helper for README steps 4-5.

  python3 drive.py lin SPEED SECONDS [--topic T]   # SPEED in m/s
  python3 drive.py ang SPEED SECONDS [--topic T]   # SPEED in rad/s, + = counterclockwise
  python3 drive.py watch SECONDS                   # publishes nothing; just measures (move the robot by hand)

Publishes a constant Twist at ~20 Hz for SECONDS, then zeros for 1.5 s, then prints:
  * what was commanded (lin: SPEED*SECONDS metres, ang: SPEED*SECONDS degrees)
  * EKF motion over the whole move, from /odometry/filtered (dx, dy, distance, unwrapped yaw change)
  * gyro-integrated rotation from /imu/data (independent of the EKF)
  * the EKF's absolute end pose
Tape-measure / mark the real motion yourself and compare.

Topic: use --topic /cmd_vel_teleop when hw_bringup is running (goes through the mux, default here),
or --topic /cmd_vel_mux when motor_driver_node runs alone. Needs imu_node and the EKF running for the
gyro/EKF numbers; missing data is reported as n/a.
"""
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


class Drive(Node):
    def __init__(self, topic):
        super().__init__('drive_helper')
        self.pub = self.create_publisher(Twist, topic, 10)
        self.create_subscription(Imu, '/imu/data', self.imu_cb, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odometry/filtered', self.odom_cb, 10)
        self.run = False
        self.gyro_yaw, self.gyro_t, self.gyro_n = 0.0, None, 0
        self.pose = None            # latest (x, y, yaw)
        self.start = None           # pose when the run began
        self.yaw_acc, self.prev_yaw, self.odom_n = 0.0, None, 0

    def imu_cb(self, m):
        t = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        if self.run and self.gyro_t is not None:
            self.gyro_yaw += m.angular_velocity.z * (t - self.gyro_t)
            self.gyro_n += 1
        self.gyro_t = t

    def odom_cb(self, m):
        q = m.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        if self.run and self.prev_yaw is not None:
            self.yaw_acc += wrap(yaw - self.prev_yaw)      # accumulate so 360 deg does not wrap to 0
            self.odom_n += 1
        self.prev_yaw = yaw
        self.pose = (m.pose.pose.position.x, m.pose.pose.position.y, yaw)


def spin_for(n, secs, msg=None):
    t0 = time.monotonic()
    while time.monotonic() - t0 < secs:
        if msg is not None:
            n.pub.publish(msg)
        rclpy.spin_once(n, timeout_sec=0.05)


def main():
    args = list(sys.argv[1:])
    topic = '/cmd_vel_teleop'
    if '--topic' in args:
        i = args.index('--topic')
        topic = args[i + 1]
        del args[i:i + 2]
    if not args or args[0] not in ('lin', 'ang', 'watch') or \
            (args[0] == 'watch' and len(args) != 2) or (args[0] != 'watch' and len(args) != 3):
        print(__doc__)
        sys.exit(1)
    mode = args[0]
    secs = float(args[-1])
    speed = float(args[1]) if mode != 'watch' else 0.0

    rclpy.init()
    n = Drive(topic)
    spin_for(n, 1.0)                         # discovery + first messages

    cmd = None
    if mode == 'lin':
        cmd = Twist(); cmd.linear.x = speed
    elif mode == 'ang':
        cmd = Twist(); cmd.angular.z = speed

    n.start = n.pose
    n.run = True
    spin_for(n, secs, cmd)
    if mode != 'watch':
        spin_for(n, 1.5, Twist())            # zeros, and let the robot settle
    else:
        spin_for(n, 0.5)
    n.run = False

    if mode == 'lin':
        print(f'commanded distance: {speed * secs:.3f} m')
    elif mode == 'ang':
        print(f'commanded rotation: {math.degrees(speed * secs):.1f} deg')
    if n.start is not None and n.pose is not None:
        dx, dy = n.pose[0] - n.start[0], n.pose[1] - n.start[1]
        print(f'EKF motion: dx={dx:.3f} dy={dy:.3f} distance={math.hypot(dx, dy):.3f} m, '
              f'yaw change={math.degrees(n.yaw_acc):.1f} deg')
        print(f'EKF end pose: x={n.pose[0]:.3f} y={n.pose[1]:.3f} yaw={math.degrees(n.pose[2]):.1f} deg')
    else:
        print('EKF motion: n/a (no /odometry/filtered; is the bringup running?)')
    if n.gyro_n:
        print(f'gyro-integrated rotation: {math.degrees(n.gyro_yaw):.1f} deg')
    else:
        print('gyro-integrated rotation: n/a (no /imu/data)')
    n.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
