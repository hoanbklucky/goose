import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Imu

import time
import math


class IMUNode(Node):

    def __init__(self):

        super().__init__('imu_node')


        # ==================================================
        # Publisher
        # ==================================================

        self.publisher = self.create_publisher(

            Imu,

            '/imu/data',

            10

        )



        # ==================================================
        # Update Rate
        # ==================================================

        self.timer = self.create_timer(

            0.02,

            self.publish_imu

        )


        self.get_logger().info(

            "Goosebot MPU6050 IMU Node Started"

        )



    def publish_imu(self):


        msg = Imu()



        # ==================================================
        # Header
        # ==================================================

        msg.header.stamp = self.get_clock().now().to_msg()

        msg.header.frame_id = "imu_link"



        # ==================================================
        # Placeholder IMU Data
        # ==================================================
        #
        # Replace with actual MPU6050 readings.
        #
        # Current purpose:
        #
        # ROS2 topic testing
        #
        # ==================================================



        # Orientation

        msg.orientation.x = 0.0

        msg.orientation.y = 0.0

        msg.orientation.z = 0.0

        msg.orientation.w = 1.0



        # Angular velocity

        msg.angular_velocity.x = 0.0

        msg.angular_velocity.y = 0.0

        msg.angular_velocity.z = 0.0



        # Linear acceleration

        msg.linear_acceleration.x = 0.0

        msg.linear_acceleration.y = 0.0

        msg.linear_acceleration.z = 9.81



        # ==================================================
        # Publish
        # ==================================================


        self.publisher.publish(msg)



def main(args=None):


    rclpy.init(args=args)


    node = IMUNode()


    rclpy.spin(node)


    node.destroy_node()


    rclpy.shutdown()



if __name__ == '__main__':

    main()
