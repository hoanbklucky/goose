from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    return LaunchDescription([


        # ==================================================
        # MPU6050 IMU
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
        # Goosebot Encoder Node
        # ==================================================

        Node(
            package='goosebot',
            executable='encoder_node',
            name='encoder_node',
            output='screen'
        ),



        # ==================================================
        # Goosebot Motor Node
        # ==================================================

        Node(
            package='goosebot',
            executable='motor_node',
            name='motor_node',
            output='screen'
        ),



        # ==================================================
        # Robot State Monitor
        # ==================================================

        Node(
            package='goosebot',
            executable='robot_state_node',
            name='robot_state_node',
            output='screen'
        ),



        # ==================================================
        # Robot Localization EKF
        # ==================================================

        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',

            parameters=[

                'config/ekf.yaml'

            ]

        ),


    ])
