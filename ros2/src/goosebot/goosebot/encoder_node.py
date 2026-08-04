import rclpy
from rclpy.node import Node

from nav_msgs.msg import Odometry

import time
import math


class EncoderNode(Node):

    def __init__(self):

        super().__init__('encoder_node')


        # ==================================================
        # Publisher
        # ==================================================

        self.odom_publisher = self.create_publisher(
            Odometry,
            '/wheel/odometry',
            10
        )


        # ==================================================
        # Encoder Calibration Values
        # ==================================================

        self.counts_per_revolution = 1092

        self.wheel_diameter_inches = 2.6

        self.wheel_circumference_inches = (
            math.pi *
            self.wheel_diameter_inches
        )


        # Current encoder count

        self.left_count = 0

        self.right_count = 0


        # Previous values

        self.previous_time = time.time()


        # ==================================================
        # Timer
        # ==================================================

        self.timer = self.create_timer(
            0.05,
            self.publish_odometry
        )


        self.get_logger().info(
            "Goosebot Encoder Node Started"
        )



    def publish_odometry(self):

        """
        Convert encoder counts into ROS2 odometry.

        Currently:
        - ROS2 publisher created
        - Calibration values added
        - Hardware reading not connected yet

        Future:
        - Read GPIO encoder pins
        - Calculate wheel velocity
        - Publish real odometry
        """


        current_time = self.get_clock().now()


        msg = Odometry()


        # Header

        msg.header.stamp = current_time.to_msg()

        msg.header.frame_id = "odom"

        msg.child_frame_id = "base_link"



        # ==================================================
        # Distance Calculation
        # ==================================================

        left_distance = (
            self.left_count /
            self.counts_per_revolution
        ) * self.wheel_circumference_inches


        right_distance = (
            self.right_count /
            self.counts_per_revolution
        ) * self.wheel_circumference_inches



        # Average distance

        distance = (
            left_distance +
            right_distance
        ) / 2



        # Convert inches to meters

        distance_meters = (
            distance *
            0.0254
        )


        msg.pose.pose.position.x = distance_meters

        msg.pose.pose.position.y = 0.0

        msg.pose.pose.position.z = 0.0



        # Orientation

        msg.pose.pose.orientation.w = 1.0



        # Publish

        self.odom_publisher.publish(msg)



def main(args=None):

    rclpy.init(args=args)


    node = EncoderNode()


    rclpy.spin(node)


    node.destroy_node()


    rclpy.shutdown()



if __name__ == '__main__':

    main()
