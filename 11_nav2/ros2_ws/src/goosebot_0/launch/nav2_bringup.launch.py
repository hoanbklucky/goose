import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    goosebot_share = get_package_share_directory('goosebot_0')
    nav2_bringup_share = get_package_share_directory('nav2_bringup')

    default_params_file = os.path.join(goosebot_share, 'config', 'nav2_params.yaml')

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to the Nav2 params file'
    )

    # navigation_launch.py only -- NOT bringup_launch.py. bringup_launch.py
    # would also try to start map_server/amcl or slam_toolbox, which we
    # don't want: localization here comes from our own SLAM + map_odom_bridge,
    # already running as separate nodes.
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_share, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'params_file': LaunchConfiguration('params_file'),
        }.items()
    )

    return LaunchDescription([
        params_file_arg,
        nav2_navigation,
    ])
