#!/usr/bin/env python3
"""
Startup relocalization: wait until RTAB-Map has recognised the surroundings against the loaded map, i.e. knows where
the robot is, then exit with code 0. hw_robot.launch.py starts Nav2 only when this node exits successfully, so Nav2
never plans from an unknown pose. Settings: relocalization.* in config/slam_params.yaml.

  mode auto    turns the robot in place in short steps (turn, pause, turn, ...) so the camera sees the mapped
               surroundings from many directions; stops as soon as localized or after timeout_s.
  mode manual  does not move the robot; prints a reminder while you rotate/drive it with teleop.

Localized = /rtabmap/localization_pose reports a covariance below max_covariance (RTAB-Map publishes 9999 until a
real localization against the loaded map has been computed). This signal is only meaningful while RTAB-Map is in
LOCALIZATION mode: in mapping mode RTAB-Map fills the covariance in from the first node, so it would claim "localized"
at once. That is why hw_robot.launch.py starts every loaded-map mode in localization and, for the modes that keep
learning, sets then_mapping:=true: once localized this node calls /rtabmap/set_mode_mapping (RTAB-Map then adds nodes to
the same, already aligned map) and only then exits 0. If auto times out the robot stops turning and the node KEEPS WAITING
(you can still rotate it by hand or send an initial pose from RViz); Nav2 stays off until it localizes.

Spin commands go to /cmd_vel (Nav2's slot in cmd_vel_mux), which is BELOW /cmd_vel_teleop: touching teleop overrides
the spin immediately. The mux zeroes the output 0.5 s after the last command, so a dead node means a stopped robot.
SAFETY: the robot turns in place with no obstacle check, so keep clear floor around it (at least its own radius).
"""
import math
import sys


# ----------------------------------------------------------------------------- pure logic (tested without ROS)

def is_localized(covariance_xx, max_covariance):
    """RTAB-Map sends 9999 on x/y variance until it has a localization."""
    return 0.0 < covariance_xx < max_covariance


class SpinSteps:
    """Turn `step_rad` at `speed`, hold still for `pause_s`, repeat."""

    def __init__(self, speed, step_deg, pause_s):
        self.speed = abs(float(speed))
        self.turn_s = math.radians(float(step_deg)) / self.speed
        self.pause_s = float(pause_s)

    def angular_velocity(self, elapsed):
        """Commanded angular.z (rad/s) `elapsed` seconds after spinning started."""
        cycle = self.turn_s + self.pause_s
        return self.speed if (elapsed % cycle) < self.turn_s else 0.0


class StartGate:
    """Do not start spinning until the robot is ready to move. imu_node measures the gyro bias at startup and needs
    the robot STILL (it retries up to 5x, then gives up and runs with zero bias, which makes the EKF yaw drift). It
    only creates /imu/data AFTER calibrating, so 'first /imu/data message seen' means calibration is finished.
    Also waits for RTAB-Map to be up (its localization_pose publisher exists), then `settle_s` more seconds.
    After `timeout_s` it opens anyway (e.g. no IMU fitted), so a missing sensor cannot block relocalization forever."""

    def __init__(self, need_imu, settle_s, timeout_s):
        self.need_imu, self.settle_s, self.timeout_s = bool(need_imu), float(settle_s), float(timeout_s)
        self.ready_t = None

    def update(self, t, imu_seen, rtabmap_up):
        """t = seconds since the node started. Returns (open, reason)."""
        if t >= self.timeout_s:
            return True, f'gave up waiting after {self.timeout_s:.0f} s'
        if self.need_imu and not imu_seen:
            return False, 'waiting for the IMU to finish calibrating (first /imu/data)'
        if not rtabmap_up:
            return False, 'waiting for RTAB-Map to start'
        if self.ready_t is None:
            self.ready_t = t
        if t - self.ready_t < self.settle_s:
            return False, 'settling'
        return True, 'ready'


# ----------------------------------------------------------------------------- ROS node

def main():
    import rclpy
    from geometry_msgs.msg import Twist
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from sensor_msgs.msg import Imu
    from rclpy.node import Node

    class Relocalize(Node):
        def __init__(self):
            super().__init__('relocalize')
            P = self.declare_parameter
            P('mode', 'auto'); P('timeout_s', 90.0); P('spin_speed', 0.8); P('step_deg', 30.0); P('pause_s', 2.0)
            P('max_covariance', 1.0); P('pose_topic', '/rtabmap/localization_pose'); P('cmd_topic', '/cmd_vel')
            P('then_mapping', False); P('mapping_service', '/rtabmap/set_mode_mapping')
            P('wait_for_imu', True); P('imu_topic', '/imu/data'); P('settle_s', 2.0); P('gate_timeout_s', 60.0)
            g = lambda n: self.get_parameter(n).value
            self.mode = str(g('mode')).lower()
            if self.mode not in ('auto', 'manual'):
                raise RuntimeError(f"relocalize: mode must be auto or manual, got '{self.mode}'")
            self.max_cov = float(g('max_covariance')); self.timeout = float(g('timeout_s'))
            self.spin = SpinSteps(g('spin_speed'), g('step_deg'), g('pause_s'))
            self.localized = False
            self.node_t0 = self.get_clock().now()
            self.t0 = self.node_t0        # spin clock: reset when the start gate opens
            self.imu_seen = False
            self.pose_topic = g('pose_topic')
            self.gate = StartGate(g('wait_for_imu'), g('settle_s'), g('gate_timeout_s'))
            self.started = self.mode != 'auto'      # manual mode never moves the robot, nothing to wait for
            self.last_gate_log = -10.0
            self.timed_out = False
            self.last_msg_t = 0.0
            self.cmd = self.create_publisher(Twist, g('cmd_topic'), 10)
            self.create_subscription(PoseWithCovarianceStamped, g('pose_topic'), self.on_pose, 5)
            self.create_subscription(Imu, g('imu_topic'), self.on_imu, 5)
            self.create_timer(0.1, self.tick)
            self.get_logger().info(
                f'waiting for RTAB-Map to localize on the loaded map (mode {self.mode}, '
                + (f'turning in {g("step_deg")} deg steps at {g("spin_speed")} rad/s, give up turning after '
                   f'{self.timeout:.0f} s)' if self.mode == 'auto' else 'rotate the robot yourself with teleop)'))

        def on_imu(self, _msg):
            self.imu_seen = True

        def on_pose(self, msg):
            if is_localized(msg.pose.covariance[0], self.max_cov):
                if not self.localized:
                    p = msg.pose.pose.position
                    self.get_logger().info(f'LOCALIZED at map x={p.x:.2f} y={p.y:.2f} '
                                           f'(variance {msg.pose.covariance[0]:.3g}). Starting Nav2 if enabled.')
                self.localized = True

        def switch_to_mapping(self):
            """Flip the running RTAB-Map to mapping mode (Mem/IncrementalMemory true). True on success."""
            from std_srvs.srv import Empty
            name = self.get_parameter('mapping_service').value
            cli = self.create_client(Empty, name)
            if not cli.wait_for_service(timeout_sec=10.0):
                self.get_logger().error(f'service {name} not available: cannot switch to mapping. Nav2 not started.')
                return False
            fut = cli.call_async(Empty.Request())
            rclpy.spin_until_future_complete(self, fut, timeout_sec=10.0)
            ok = fut.done() and fut.exception() is None
            self.get_logger().info('RTAB-Map switched to mapping mode: the loaded map is now being updated' if ok
                                   else 'switching to mapping mode FAILED. Nav2 not started.')
            return ok

        def elapsed(self):
            return (self.get_clock().now() - self.t0).nanoseconds * 1e-9

        def tick(self):
            if self.localized:
                return
            if not self.started:
                tn = (self.get_clock().now() - self.node_t0).nanoseconds * 1e-9
                ok, why = self.gate.update(tn, self.imu_seen, self.count_publishers(self.pose_topic) > 0)
                if not ok:
                    if tn - self.last_gate_log >= 5.0:
                        self.last_gate_log = tn
                        self.get_logger().info(f'not spinning yet: {why} ({tn:.0f} s)')
                    return
                self.started = True
                self.t0 = self.get_clock().now()
                self.get_logger().info(f'start gate open ({why}): starting to turn')
            t = self.elapsed()
            if self.mode == 'auto' and not self.timed_out:
                if t > self.timeout:
                    self.timed_out = True
                    self.cmd.publish(Twist())
                    self.get_logger().error(
                        f'not localized after {self.timeout:.0f} s of turning. Stopped turning; still waiting. Move the '
                        f'robot by hand so the camera sees mapped areas (or send a 2D Pose Estimate in RViz). '
                        f'Nav2 will not start until localized.')
                else:
                    m = Twist(); m.angular.z = self.spin.angular_velocity(t); self.cmd.publish(m)
            if t - self.last_msg_t >= 10.0:
                self.last_msg_t = t
                self.get_logger().info(f'still not localized ({t:.0f} s)'
                                       + ('. Rotate/drive the robot with teleop so the camera sees mapped areas.'
                                          if self.mode == 'manual' or self.timed_out else ''),)

    rclpy.init()
    node = Relocalize()
    code = 1                                       # anything but "localized" is a non-zero exit => Nav2 stays off
    try:
        while rclpy.ok() and not node.localized:
            rclpy.spin_once(node, timeout_sec=0.1)
        if node.localized:
            code = 0
            if bool(node.get_parameter('then_mapping').value) and not node.switch_to_mapping():
                code = 1
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            for _ in range(5):
                node.cmd.publish(Twist())          # make sure we leave the robot stopped
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(code)


if __name__ == '__main__':
    main()
