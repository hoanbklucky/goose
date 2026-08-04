from launch import LaunchDescription
from launch_ros.actions import Node



def generate_launch_description():


    # ======================================================
    # SLAM Toolbox Launch
    # ======================================================
    #
    # Starts mapping mode.
    #
    # Inputs:
    #
    #   /scan
    #   /imu/data
    #   /wheel/odometry
    #
    # Output:
    #
    #   /map
    #
    # ======================================================



    slam_node = Node(

        package='slam_toolbox',

        executable='sync_slam_toolbox_node',

        name='slam_toolbox',

        output='screen',


        parameters=[

            '/home/radxa/goosebot/ros2/config/slam_toolbox.yaml'

        ]

    )



    return LaunchDescription([

        slam_node

    ])
