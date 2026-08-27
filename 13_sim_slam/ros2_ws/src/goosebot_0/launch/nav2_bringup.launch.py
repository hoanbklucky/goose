import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node


def generate_launch_description():
    goosebot_share = get_package_share_directory('goosebot_0')
    nav2_bringup_share = get_package_share_directory('nav2_bringup')

    default_params_file = os.path.join(goosebot_share, 'config', 'nav2_params.yaml')
    default_map_file = os.path.join(goosebot_share, 'maps', 'map.yaml')

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to the Nav2 params file'
    )
    map_file_arg = DeclareLaunchArgument(
        'map',
        default_value=default_map_file,
        description='Full path to the baked ground-truth map yaml'
    )

    # navigation_launch.py only -- NOT bringup_launch.py, since bringup_launch.py
    # also starts its own AMCL, which we don't want: localization here comes
    # from Gazebo ground truth via ground_truth_map_odom_bridge below, and the
    # map is a pre-baked ground-truth map, not something built live by SLAM.
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_share, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'params_file': LaunchConfiguration('params_file'),
        }.items()
    )

    # Serves the baked ground-truth map. Remapped so it publishes on
    # /projected_map -- matches what nav2_params.yaml's static_layer already
    # expects, no params file changes needed for this swap.
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'yaml_filename': LaunchConfiguration('map'),
            'use_sim_time': True,
        }],
        remappings=[('/map', '/projected_map')],
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server'],
        }],
    )

    ground_truth_bridge = Node(
        package='goosebot_0',
        executable='ground_truth_map_odom_bridge.py',
        name='ground_truth_map_odom_bridge',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        params_file_arg,
        map_file_arg,
        map_server,
        lifecycle_manager,
        ground_truth_bridge,
        nav2_navigation,
    ])
