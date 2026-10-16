#!/usr/bin/env python3
"""
MPU6050 (GY-521) -> sensor_msgs/Imu on /imu/data, frame imu_link.

Design decisions (all driven by what ekf.yaml in the sim actually consumes):
  * The EKF only fuses angular_velocity.z. So this node publishes ORIENTATION AS UNKNOWN
    (orientation_covariance[0] = -1, REP-145). The old goosebot_sensors node faked a
    quaternion from the gyro with a 0.05 covariance -- that is exactly the "confident but
    wrong yaw" failure your ekf.yaml notes found in sim. An MPU6050 has no magnetometer;
    it cannot know absolute yaw.
  * Gyro bias is measured at startup (robot MUST be still) and the measured variance is
    used for angular_velocity_covariance instead of a guessed constant.
  * One 14-byte block read per sample (the old test script did 14 separate reads).
  * Optional zero-velocity re-bias while the motor driver reports it is stopped.

I2C: bus 6, addr 0x68 per your IMU notes (pins 27/28, overlay I2C6-M0).
"""
import math
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Twist

try:
    from smbus2 import SMBus
except ImportError:  # allows import on a laptop for lint/dry runs
    SMBus = None

G = 9.80665
DEG2RAD = math.pi / 180.0


class ImuNode(Node):
    def __init__(self):
        super().__init__('imu_node')
        P = self.declare_parameter
        P('bus', 6); P('address', 0x68)
        P('rate', 100.0)
        P('frame_id', 'imu_link')
        P('gyro_range_dps', 500)         # 250/500/1000/2000; 500 -> 65.5 LSB/dps, nav2 turns <= ~60 dps
        P('dlpf_cfg', 3)                 # 3 = ~44 Hz gyro bandwidth; motors are noisy, keep it low
        P('gyro_z_sign', 1.0)            # -1 if the module is mounted upside down / flipped
        P('calib_samples', 500)
        P('calib_max_std_dps', 0.5)      # refuse to calibrate while the robot is moving
        P('gyro_cov_floor', 1e-5)        # rad^2/s^2, never publish 0
        P('rebias_when_stopped', False)  # slow EMA re-bias while /cmd_vel_applied == 0
        P('rebias_alpha', 0.002)
        g = lambda n: self.get_parameter(n).value
        self.addr = g('address')
        self.bus = SMBus(g('bus'))
        self.zsign = g('gyro_z_sign')
        rng = {250: (0, 131.0), 500: (1, 65.5), 1000: (2, 32.8), 2000: (3, 16.4)}[int(g('gyro_range_dps'))]
        self.gyro_lsb = rng[1]
        self.accel_lsb = 16384.0   # +/-2 g

        self.bus.write_byte_data(self.addr, 0x6B, 0x01)          # wake, PLL on gyro X
        time.sleep(0.1)
        self.bus.write_byte_data(self.addr, 0x1A, int(g('dlpf_cfg')))
        self.bus.write_byte_data(self.addr, 0x19, 9)             # 1 kHz/(1+9) = 100 Hz
        self.bus.write_byte_data(self.addr, 0x1B, rng[0] << 3)
        self.bus.write_byte_data(self.addr, 0x1C, 0x00)

        self.bias = [0.0, 0.0, 0.0]
        self.gyro_var = [g('gyro_cov_floor')] * 3
        self.calibrate(int(g('calib_samples')), g('calib_max_std_dps'), g('gyro_cov_floor'))

        self.rebias = g('rebias_when_stopped'); self.alpha = g('rebias_alpha')
        self.stopped_since = None
        self.create_subscription(Twist, '/cmd_vel_applied', self.applied_cb, 10)
        self.pub = self.create_publisher(Imu, '/imu/data', 20)
        self.frame = g('frame_id')
        self.create_timer(1.0 / g('rate'), self.tick)

    # ---- helpers -------------------------------------------------------
    def read_raw(self):
        d = self.bus.read_i2c_block_data(self.addr, 0x3B, 14)
        def s16(h, l):
            v = (h << 8) | l
            return v - 65536 if v >= 32768 else v
        ax, ay, az = s16(d[0], d[1]), s16(d[2], d[3]), s16(d[4], d[5])
        gx, gy, gz = s16(d[8], d[9]), s16(d[10], d[11]), s16(d[12], d[13])
        return ax, ay, az, gx, gy, gz

    def calibrate(self, n, max_std_dps, floor):
        for attempt in range(5):
            self.get_logger().info(f'Calibrating gyro bias ({n} samples) -- keep robot STILL '
                                   f'(attempt {attempt + 1}/5)')
            xs = [[], [], []]
            for _ in range(n):
                r = self.read_raw()
                for i in range(3):
                    xs[i].append(r[3 + i] / self.gyro_lsb)   # deg/s
                time.sleep(0.004)
            mean = [sum(a) / len(a) for a in xs]
            std = [math.sqrt(sum((v - m) ** 2 for v in a) / len(a)) for a, m in zip(xs, mean)]
            if max(std) <= max_std_dps:
                self.bias = [m * DEG2RAD for m in mean]
                self.gyro_var = [max((s * DEG2RAD) ** 2, floor) for s in std]
                self.get_logger().info(
                    f'gyro bias (rad/s) {self.bias}, std (dps) {std}')
                return
            self.get_logger().warn(f'robot moved during calibration (std {std} dps), retrying')
        self.get_logger().error('Gyro calibration failed 5x; running with zero bias. '
                                'Heading WILL drift.')

    def applied_cb(self, m):
        stopped = abs(m.linear.x) < 1e-4 and abs(m.angular.z) < 1e-4
        now = self.get_clock().now().nanoseconds * 1e-9
        if not stopped:
            self.stopped_since = None
        elif self.stopped_since is None:
            self.stopped_since = now

    def tick(self):
        try:
            ax, ay, az, gx, gy, gz = self.read_raw()
        except OSError as e:
            self.get_logger().warn(f'IMU read failed: {e}', throttle_duration_sec=2.0)
            return
        wx = gx / self.gyro_lsb * DEG2RAD
        wy = gy / self.gyro_lsb * DEG2RAD
        wz = gz / self.gyro_lsb * DEG2RAD

        if self.rebias and self.stopped_since is not None:
            now = self.get_clock().now().nanoseconds * 1e-9
            if now - self.stopped_since > 1.0:
                self.bias[2] += self.alpha * (wz - self.bias[2])

        m = Imu()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = self.frame
        m.orientation_covariance[0] = -1.0                 # orientation not provided
        m.angular_velocity.x = wx - self.bias[0]
        m.angular_velocity.y = wy - self.bias[1]
        m.angular_velocity.z = self.zsign * (wz - self.bias[2])
        m.angular_velocity_covariance[0] = self.gyro_var[0]
        m.angular_velocity_covariance[4] = self.gyro_var[1]
        m.angular_velocity_covariance[8] = self.gyro_var[2]
        m.linear_acceleration.x = ax / self.accel_lsb * G
        m.linear_acceleration.y = ay / self.accel_lsb * G
        m.linear_acceleration.z = az / self.accel_lsb * G
        for i in (0, 4, 8):
            m.linear_acceleration_covariance[i] = 0.1      # not fused by the EKF
        self.pub.publish(m)


def main():
    rclpy.init()
    n = ImuNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
