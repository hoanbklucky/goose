#!/usr/bin/env python3
"""
Calibration helper (README steps 4-5, GOOSEBOT_TODO steps 6-8).

  python3 drive_test.py lin SPEED SECONDS [--topic T]   # SPEED in m/s
  python3 drive_test.py ang SPEED SECONDS [--topic T]   # SPEED in rad/s, + = counterclockwise
  python3 drive_test.py watch SECONDS                   # publishes nothing; just measures (move the robot by hand)

Publishes a constant Twist at 20 Hz for SECONDS, then zeros for 1.5 s, then prints:
  * what was commanded (lin: SPEED*SECONDS metres, ang: SPEED*SECONDS degrees)
  * encoder distance from /wheel/odom (front wheels, independent of the EKF)
  * EKF motion over the whole move, from /odometry/filtered (dx, dy, distance, unwrapped yaw change)
  * gyro-integrated rotation from /imu/data (independent of the EKF)
  * the EKF's absolute end pose, and how many messages arrived from each topic
Tape-measure / mark the real motion yourself and compare.

2026-11-19: ROS callbacks now run in a background thread (the old single spin_once loop could miss
/odometry/filtered entirely), waits up to 5 s for all three topics before driving, and adds /wheel/odom.
Topic: --topic /cmd_vel_teleop (default, goes through the mux) or /cmd_vel_mux when motor_driver_node runs alone.
"""
import math
import sys
import threading
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class Drive(Node):
    def __init__(self, topic):
        super().__init__('drive_helper')
        self.lock = threading.Lock()
        self.pub = self.create_publisher(Twist, topic, 10)
        self.create_subscription(Imu, '/imu/data', self.imu_cb, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odometry/filtered', self.odom_cb, 10)
        self.create_subscription(Odometry, '/wheel/odom', self.wheel_cb, 10)
        self.run = False
        self.n = {'imu': 0, 'ekf': 0, 'wheel': 0}
        self.gyro_yaw, self.gyro_t = 0.0, None
        self.pose = None            # latest EKF (x, y, yaw)
        self.yaw_acc, self.prev_yaw = 0.0, None
        self.wheel = None           # latest encoder (x, y)
        self.wheel_dist, self.prev_wheel = 0.0, None

    def imu_cb(self, m):
        t = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        with self.lock:
            self.n['imu'] += 1
            if self.run and self.gyro_t is not None:
                self.gyro_yaw += m.angular_velocity.z * (t - self.gyro_t)
            self.gyro_t = t

    def odom_cb(self, m):
        yaw = yaw_of(m.pose.pose.orientation)
        with self.lock:
            self.n['ekf'] += 1
            if self.run and self.prev_yaw is not None:
                self.yaw_acc += wrap(yaw - self.prev_yaw)      # accumulate so 360 deg does not wrap to 0
            self.prev_yaw = yaw
            self.pose = (m.pose.pose.position.x, m.pose.pose.position.y, yaw)

    def wheel_cb(self, m):
        p = (m.pose.pose.position.x, m.pose.pose.position.y)
        with self.lock:
            self.n['wheel'] += 1
            if self.run and self.prev_wheel is not None:
                # signed path length along the encoder track (forward +, backward -)
                step = math.hypot(p[0] - self.prev_wheel[0], p[1] - self.prev_wheel[1])
                self.wheel_dist += math.copysign(step, m.twist.twist.linear.x) if step > 0 else 0.0
            self.prev_wheel = p
            self.wheel = p


def publish_for(n, secs, msg):
    t0 = time.monotonic()
    while time.monotonic() - t0 < secs:
        n.pub.publish(msg)
        time.sleep(0.05)


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
    ex = SingleThreadedExecutor()
    ex.add_node(n)
    th = threading.Thread(target=ex.spin, daemon=True)
    th.start()

    # wait (up to 5 s) until every input has delivered at least one message
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5.0:
        with n.lock:
            if all(v > 0 for v in n.n.values()):
                break
        time.sleep(0.05)
    with n.lock:
        missing = [k for k, v in n.n.items() if v == 0]
    if missing:
        print(f'WARNING: no messages yet from: {", ".join(missing)} (continuing; those results will be n/a)')
    time.sleep(0.5)                           # a few more samples so the start pose is fresh

    cmd = Twist()
    if mode == 'lin':
        cmd.linear.x = speed
    elif mode == 'ang':
        cmd.angular.z = speed

    with n.lock:
        start = n.pose
        n.run = True
    if mode != 'watch':
        publish_for(n, secs, cmd)
        publish_for(n, 1.5, Twist())          # zeros, and let the robot settle
    else:
        time.sleep(secs + 0.5)
    with n.lock:
        n.run = False
        end, counts = n.pose, dict(n.n)
        yaw_acc, gyro_yaw, wheel_dist = n.yaw_acc, n.gyro_yaw, n.wheel_dist

    if mode == 'lin':
        print(f'commanded distance: {speed * secs:.3f} m')
    elif mode == 'ang':
        print(f'commanded rotation: {math.degrees(speed * secs):.1f} deg')
    print(f'encoder distance (/wheel/odom): {wheel_dist:.3f} m' if counts['wheel'] else
          'encoder distance: n/a (no /wheel/odom; is encoder_node running?)')
    if start is not None and end is not None:
        dx, dy = end[0] - start[0], end[1] - start[1]
        print(f'EKF motion: dx={dx:.3f} dy={dy:.3f} distance={math.hypot(dx, dy):.3f} m, '
              f'yaw change={math.degrees(yaw_acc):.1f} deg')
        print(f'EKF end pose: x={end[0]:.3f} y={end[1]:.3f} yaw={math.degrees(end[2]):.1f} deg')
    else:
        print('EKF motion: n/a (no /odometry/filtered)')
    print(f'gyro-integrated rotation: {math.degrees(gyro_yaw):.1f} deg' if counts['imu'] else
          'gyro-integrated rotation: n/a (no /imu/data)')
    print(f"messages received: imu {counts['imu']}, ekf {counts['ekf']}, wheel {counts['wheel']}")
    # stop the background spin thread cleanly before tearing down (exiting with it still inside rclpy's C++ wait
    # aborts with "terminate called without an active exception")
    ex.shutdown(timeout_sec=2.0)
    th.join(timeout=2.0)
    n.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
