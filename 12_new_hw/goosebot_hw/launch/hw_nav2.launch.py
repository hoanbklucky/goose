"""
Nav2 on hardware (Jazzy). Derived from sim nav2_bringup.launch.py with the sim-only parts removed:
 - NO ground_truth_map_odom_bridge (does not exist on hardware)
 - map comes from RTAB-Map (/rtabmap/map), which also owns map->odom
 - navigation_launch.py only (no AMCL), like the sim

  ros2 launch goosebot_hw hw_nav2.launch.py                 # normal: needs RTAB-Map running
  ros2 launch goosebot_hw hw_nav2.launch.py odom_only:=true # staged test: no map, no cameras, identity map->odom

odom_only:=true needs: working IMU yaw rate (otherwise the EKF never sees the robot turn),
calibrated motors, an empty floor, and your hand on the kill switch. It has NO obstacle protection
unless the ToFs are live. Do NOT run it together with RTAB-Map (both would publish map->odom).
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def _setup(context):
    share = get_package_share_directory('goosebot_hw')
    nav2 = get_package_share_directory('nav2_bringup')
    odom_only = LaunchConfiguration('odom_only').perform(context).lower() in ('true', '1')
    fname = 'nav2_params_odom_only.yaml' if odom_only else 'nav2_params.yaml'
    params = RewrittenYaml(
        source_file=os.path.join(share, 'config', fname),
        root_key='', param_rewrites={'map_topic': '/rtabmap/map'}, convert_types=True)
    actions = [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2, 'launch', 'navigation_launch.py')),
        launch_arguments={'use_sim_time': 'false', 'params_file': params}.items())]
    if odom_only:
        actions.append(Node(
            package='tf2_ros', executable='static_transform_publisher', name='static_map_to_odom',
            arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0',
                       '--frame-id', 'map', '--child-frame-id', 'odom']))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('odom_only', default_value='false'),
        OpaqueFunction(function=_setup),
    ])
