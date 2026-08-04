from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

import os



def generate_launch_description():


    # ======================================================
    # Goosebot Full Robot Launch
    # ======================================================
    #
    # Starts the complete autonomous robot stack:
    #
    #   Sensors
    #      |
    #      v
    #   Localization
    #      |
    #      v
    #   Navigation
    #      |
    #      v
    #   Motors
    #
    # ======================================================



    goosebot_launch = IncludeLaunchDescription(

        PythonLaunchDescriptionSource(

            os.path.join(

                '/home/radxa/goosebot/ros2/launch',

                'goosebot.launch.py'

            )

        )

    )



    navsat_launch = IncludeLaunchDescription(

        PythonLaunchDescriptionSource(

            os.path.join(

                '/home/radxa/goosebot/ros2/launch',

                'navsat_transform.launch.py'

            )

        )

    )



    nav2_launch = IncludeLaunchDescription(

        PythonLaunchDescriptionSource(

            os.path.join(

                '/home/radxa/goosebot/ros2/launch',

                'nav2.launch.py'

            )

        )

    )



    return LaunchDescription([


        goosebot_launch,


        navsat_launch,


        nav2_launch


    ])
