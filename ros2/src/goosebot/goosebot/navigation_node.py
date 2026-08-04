import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist


class NavigationNode(Node):

    def __init__(self):

        super().__init__('navigation_node')


        # ==================================================
        # Publisher
        # ==================================================

        self.cmd_publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )


        # ==================================================
        # Timer
        # ==================================================

        self.timer = self.create_timer(
            1.0,
            self.navigation_loop
        )


        self.get_logger().info(
            "Goosebot Navigation Node Started"
        )


    def navigation_loop(self):

        """
        Future autonomous decision making.

        This node will eventually handle:

        - Waypoints
        - Obstacle avoidance
        - Path planning
        - Autonomous driving logic


        Current test behavior:

        Publishes a slow forward command.
        """


        cmd = Twist()


        # Forward velocity

        cmd.linear.x = 0.1


        # No turning

        cmd.angular.z = 0.0



        self.cmd_publisher.publish(cmd)



def main(args=None):

    rclpy.init(args=args)


    node = NavigationNode()


    rclpy.spin(node)


    node.destroy_node()


    rclpy.shutdown()



if __name__ == '__main__':

    main()
