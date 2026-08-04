from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare

import os



def generate_launch_description():


    # ======================================================
    # Find Nav2 bringup package
    # ======================================================


    nav2_bringup_dir = FindPackageShare(
        package='nav2_bringup'
    ).find('nav2_bringup')



    # ======================================================
    # Nav2 Bringup Launch
    # ======================================================


    nav2_launch = IncludeLaunchDescription(

        PythonLaunchDescriptionSource(

            os.path.join(

                nav2_bringup_dir,

                'launch',

                'bringup_launch.py'

            )

        ),


        launch_arguments={


            # Use robot map

            'map':

            '/home/radxa/goosebot/maps/map.yaml',



            # Nav2 parameters

            'params_file':

            '/home/radxa/goosebot/ros2/config/nav2_params.yaml',



            'use_sim_time':

            'false'

        }.items()

    )



    return LaunchDescription([

        nav2_launch

    ])
