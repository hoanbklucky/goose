import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist

import time


class MotorNode(Node):

    def __init__(self):

        super().__init__('motor_node')


        # ==================================================
        # Subscribe to ROS2 velocity commands
        # ==================================================

        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )


        # ==================================================
        # Motor Configuration
        # ==================================================

        self.motor_driver = "L298N"

        self.pwm_controller = "PCA9685"


        # Current motor state

        self.left_speed = 0

        self.right_speed = 0



        self.get_logger().info(
            "Goosebot Motor Node Started"
        )



    def cmd_vel_callback(self, msg):

        """
        Receives ROS2 movement commands.

        Input:

        /cmd_vel

        geometry_msgs/msg/Twist


        Example:

        linear.x  = forward/backward

        angular.z = turning
        """


        linear_velocity = msg.linear.x

        turning_velocity = msg.angular.z



        # Differential drive calculation

        self.left_speed = (
            linear_velocity -
            turning_velocity
        )


        self.right_speed = (
            linear_velocity +
            turning_velocity
        )


        self.set_motor_speed(
            self.left_speed,
            self.right_speed
        )



    def set_motor_speed(
        self,
        left,
        right
    ):

        """
        Future hardware interface.

        This function will connect to:

        PCA9685 PWM

        and

        L298N motor driver.


        Current status:

        ROS2 command reception works.
        Hardware output not connected yet.
        """


        self.get_logger().info(
            f"Left: {left:.2f}  Right: {right:.2f}"
        )


        # Future:

        # PCA9685 PWM output
        #
        # Set direction pins
        #
        # Control motor speed



def main(args=None):

    rclpy.init(args=args)


    node = MotorNode()


    rclpy.spin(node)


    node.destroy_node()


    rclpy.shutdown()



if __name__ == '__main__':

    main()
