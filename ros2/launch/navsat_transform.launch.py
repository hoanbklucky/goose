from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    return LaunchDescription([


        # ==================================================
        # GPS Coordinate Conversion
        # ==================================================
        #
        # Converts:
        #
        # Latitude / Longitude
        #
        # into:
        #
        # Local Cartesian X/Y position
        #
        # Output:
        #
        # /gps/odometry
        #
        # Used by robot_localization EKF
        #
        # ==================================================


        Node(

            package='robot_localization',

            executable='navsat_transform_node',

            name='navsat_transform',

            output='screen',


            parameters=[{

                # Robot frames

                'frequency': 30.0,


                'delay': 3.0,


                'magnetic_declination_radians': 0.0,


                'yaw_offset': 0.0,


                'zero_altitude': True,


                'broadcast_utm_transform': True,


                'publish_filtered_gps': True,


                'use_odometry_yaw': True,


                'wait_for_datum': False,


                # Frames

                'map_frame': 'map',

                'odom_frame': 'odom',

                'base_link_frame': 'base_link',


            }]

        )

    ])
