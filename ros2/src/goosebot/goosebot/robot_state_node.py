import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Imu
from sensor_msgs.msg import NavSatFix

from nav_msgs.msg import Odometry


class RobotStateNode(Node):

    def __init__(self):

        super().__init__('robot_state_node')


        # ==================================================
        # Sensor Status Tracking
        # ==================================================

        self.imu_active = False

        self.gps_active = False

        self.encoder_active = False



        # ==================================================
        # Subscribers
        # ==================================================

        self.imu_subscription = self.create_subscription(
            Imu,
            '/imu/data',
            self.imu_callback,
            10
        )


        self.gps_subscription = self.create_subscription(
            NavSatFix,
            '/fix',
            self.gps_callback,
            10
        )


        self.encoder_subscription = self.create_subscription(
            Odometry,
            '/wheel/odometry',
            self.encoder_callback,
            10
        )



        # ==================================================
        # Status Timer
        # ==================================================

        self.timer = self.create_timer(
            5.0,
            self.publish_status
        )


        self.get_logger().info(
            "Goosebot Robot State Node Started"
        )



    # ======================================================
    # Sensor Callbacks
    # ======================================================


    def imu_callback(self, msg):

        self.imu_active = True



    def gps_callback(self, msg):

        if msg.status.status >= 0:

            self.gps_active = True

        else:

            self.gps_active = False



    def encoder_callback(self, msg):

        self.encoder_active = True



    # ======================================================
    # Status Output
    # ======================================================


    def publish_status(self):

        self.get_logger().info(
            "\n"
            "===== Goosebot Status =====\n"
            f"IMU: {self.imu_active}\n"
            f"GPS: {self.gps_active}\n"
            f"Encoder: {self.encoder_active}\n"
            "==========================="
        )



def main(args=None):

    rclpy.init(args=args)


    node = RobotStateNode()


    rclpy.spin(node)


    node.destroy_node()


    rclpy.shutdown()



if __name__ == '__main__':

    main()
