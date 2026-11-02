import math, rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
 
class Drift(Node):
    def __init__(self):
        super().__init__('imu_drift')
        self.t0 = self.t = None
        self.yaw = 0.0
        self.create_subscription(Imu, '/imu/data', self.cb, qos_profile_sensor_data)
    def cb(self, m):
        t = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        if self.t is None:
            self.t0 = t
        else:
            self.yaw += m.angular_velocity.z * (t - self.t)
        self.t = t

rclpy.init()
n = Drift()
try:
    rclpy.spin(n)
except KeyboardInterrupt:
    pass
mins = (n.t - n.t0) / 60.0
print(f'{mins:.1f} min, drift {math.degrees(n.yaw):.2f} deg = {math.degrees(n.yaw)/mins:.2f} deg/min')
