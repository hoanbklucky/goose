#!/usr/bin/env python3
"""
Integrates commanded velocity (/cmd_vel) into an open-loop odometry
estimate. This is a stand-in for wheel-encoder odometry on hardware that
has no encoders -- it measures nothing about the real world, it only
assumes the commanded velocity was actually achieved. Slip, motor lag,
terrain, and any other disturbance are completely invisible to this node
by construction; error will accumulate without bound over time and
distance. This is a deliberate, known tradeoff, not a bug -- see the
project notes on why (no encoders on this hardware revision).

STEP 1 OF THE SWAP-IN: this node publishes to a *separate* topic
(default /odom_cmdvel) with TF broadcasting off by default, specifically
so it can be tested against ground truth in isolation before it ever
touches the real /odom topic or the odom->base_footprint TF that Gazebo's
diff-drive plugin currently owns. Do not point this at /odom or enable
publish_tf until that comparison looks acceptable -- two publishers of
the same topic/TF is a silent, hard-to-debug failure mode, not a graceful
one.

Parameters:
  cmd_vel_topic   (string, default '/cmd_vel')   -- velocity command to integrate
  odom_topic      (string, default '/odom_cmdvel') -- where to publish the estimate
  odom_frame      (string, default 'odom')
  base_frame      (string, default 'base_footprint')
  publish_rate    (double, default 50.0)          -- integration/publish rate, Hz
  cmd_vel_timeout (double, default 0.5)           -- seconds; treat velocity as
                                                       zero if no command received
                                                       within this window, so a
                                                       stalled upstream doesn't
                                                       make the robot think it's
                                                       still driving forever
  publish_tf      (bool, default False)           -- broadcast odom->base_frame TF.
                                                       Leave False until this is
                                                       confirmed as the sole TF
                                                       source for that transform.

Integration uses the exact unicycle-model arc update (not naive Euler),
which is standard practice for diff-drive odometry and meaningfully
reduces *additional* numerical error on top of the fundamental,
unavoidable open-loop error -- worth doing right since it's the one
source of error actually within this node's control.

Covariance values below are rough, hand-picked placeholders indicating
"trust this quite a bit less than real wheel odometry would be trusted."
They are not derived from any real error model -- there isn't one to
derive them from without ground truth on real hardware. Expect to revisit
these once SLAM/VIO gives you something to compare against.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
import tf2_ros


class CmdVelToOdom(Node):
    def __init__(self):
        super().__init__('cmd_vel_to_odom')

        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom_cmdvel')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('cmd_vel_timeout', 0.5)
        self.declare_parameter('publish_tf', False)

        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value
        self.publish_tf = self.get_parameter('publish_tf').value
        publish_rate = self.get_parameter('publish_rate').value

        # Integrated pose state. Starts at the odom frame's origin, matching
        # the standard convention wheel odometry also follows: odom is
        # wherever the robot booted up, not a global reference.
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        # Last commanded velocity, held (zero-order hold) between messages.
        self.last_v = 0.0
        self.last_w = 0.0
        self.last_cmd_time = None

        self.odom_pub = self.create_publisher(
            Odometry, self.get_parameter('odom_topic').value, 10)
        
        # Only create the broadcaster if explicitly requested
        if self.publish_tf:
            self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        else:
            self.tf_broadcaster = None

        self.create_subscription(
            Twist, self.get_parameter('cmd_vel_topic').value, self.cmd_vel_cb, 10)

        self.last_update_time = self.get_clock().now()
        period = 1.0 / publish_rate
        self.create_timer(period, self.update)

        self.get_logger().info(
            f'cmd_vel_to_odom: integrating {self.get_parameter("cmd_vel_topic").value} '
            f'-> {self.get_parameter("odom_topic").value} '
            f'(publish_tf={self.publish_tf}). '
            'Open-loop dead reckoning -- treat as approximate only.'
        )

    def cmd_vel_cb(self, msg: Twist):
        self.last_v = msg.linear.x
        self.last_w = msg.angular.z
        self.last_cmd_time = self.get_clock().now()

    def update(self):
        now = self.get_clock().now()
        dt = (now - self.last_update_time).nanoseconds * 1e-9
        self.last_update_time = now

        if dt <= 0.0:
            return

        # Safety/correctness watchdog: if we haven't heard a command
        # recently, don't keep integrating the last nonzero velocity --
        # that would make the robot appear to drive forever if the
        # upstream controller stalls or crashes.
        v, w = self.last_v, self.last_w
        if self.last_cmd_time is None:
            v, w = 0.0, 0.0
        else:
            age = (now - self.last_cmd_time).nanoseconds * 1e-9
            if age > self.cmd_vel_timeout:
                v, w = 0.0, 0.0

        # Exact unicycle-model arc integration (avoids extra numerical
        # error from naive Euler integration, standard practice for
        # diff-drive odometry).
        if abs(w) > 1e-6:
            dx = (v / w) * (math.sin(self.theta + w * dt) - math.sin(self.theta))
            dy = (v / w) * (-math.cos(self.theta + w * dt) + math.cos(self.theta))
        else:
            dx = v * math.cos(self.theta) * dt
            dy = v * math.sin(self.theta) * dt

        self.x += dx
        self.y += dy
        self.theta += w * dt
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))  # wrap to [-pi, pi]

        qz = math.sin(self.theta / 2.0)
        qw = math.cos(self.theta / 2.0)

        msg = Odometry()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = self.odom_frame
        msg.child_frame_id = self.base_frame
        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.x = 0.0
        msg.pose.pose.orientation.y = 0.0
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.twist.twist.linear.x = v
        msg.twist.twist.linear.y = 0.0
        msg.twist.twist.angular.z = w

        # Rough placeholder covariances -- see module docstring. Order is
        # [x, y, z, roll, pitch, yaw] on the diagonal of a 6x6 row-major
        # matrix; off-diagonal terms left at zero for simplicity.
        pose_cov = [0.0] * 36
        pose_cov[0] = 0.05    # x
        pose_cov[7] = 0.05    # y
        pose_cov[14] = 1e6    # z -- unobservable/irrelevant for a planar robot
        pose_cov[21] = 1e6    # roll -- unobservable
        pose_cov[28] = 1e6    # pitch -- unobservable
        pose_cov[35] = 0.05   # yaw
        msg.pose.covariance = pose_cov

        twist_cov = [0.0] * 36
        twist_cov[0] = 0.05
        twist_cov[7] = 1e6
        twist_cov[14] = 1e6
        twist_cov[21] = 1e6
        twist_cov[28] = 1e6
        twist_cov[35] = 0.05
        msg.twist.covariance = twist_cov

        self.odom_pub.publish(msg)

        if self.publish_tf:
            t = TransformStamped()
            t.header.stamp = now.to_msg()
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = self.x
            t.transform.translation.y = self.y
            t.transform.translation.z = 0.0
            t.transform.rotation.x = 0.0
            t.transform.rotation.y = 0.0
            t.transform.rotation.z = qz
            t.transform.rotation.w = qw
            self.tf_broadcaster.sendTransform(t)


def main():
    rclpy.init()
    node = CmdVelToOdom()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
