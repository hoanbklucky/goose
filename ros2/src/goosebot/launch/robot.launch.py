from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    return LaunchDescription([


        # ==================================================
        # MPU6050 IMU Node
        # ==================================================

        Node(
            package='mpu6050_node',
            executable='mpu6050_node',
            name='mpu6050_node',
            output='screen'
        ),



        # ==================================================
        # GPS NMEA Driver
        # ==================================================

        Node(
            package='nmea_navsat_driver',
            executable='nmea_serial_driver',
            name='nmea_navsat_driver',
            output='screen',

            parameters=[{

                'port': '/dev/ttyS4',

                'baud': 9600

            }]

        ),



        # ==================================================
        # Future Goosebot Encoder Node
        # ==================================================

        # Disabled until encoder_node.py exists
        #
        # Node(
        #     package='goosebot',
        #     executable='encoder_node',
        #     name='encoder_node',
        #     output='screen'
        # ),



        # ==================================================
        # Future Motor Controller Node
        # ==================================================

        # Disabled until motor_node.py exists
        #
        # Node(
        #     package='goosebot',
        #     executable='motor_node',
        #     name='motor_node',
        #     output='screen'
        # ),



        # ==================================================
        # Future Robot Localization EKF
        # ==================================================

        # Disabled until ekf.yaml is created
        #
        # Node(
        #     package='robot_localization',
        #     executable='ekf_node',
        #     name='ekf_filter_node',
        #     output='screen',
        #     parameters=[
        #         'config/ekf.yaml'
        #     ]
        # ),


    ])
