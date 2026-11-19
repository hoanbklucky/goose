"""
Nav2 on hardware (Jazzy). Derived from sim nav2_bringup.launch.py with the sim-only parts removed:
 - NO ground_truth_map_odom_bridge (does not exist on hardware)
 - map comes from RTAB-Map (/rtabmap/map), which also owns map->odom
 - navigation_launch.py only (no AMCL here; hw_robot.launch.py starts AMCL itself for rtab:=false)

  ros2 launch goosebot_hw hw_nav2.launch.py                 # normal: needs RTAB-Map running
  ros2 launch goosebot_hw hw_nav2.launch.py odom_only:=true # staged test: no map, no cameras, identity map->odom
  ros2 launch goosebot_hw hw_nav2.launch.py with_lidar:=false   # drop the /scan source from costmaps + collision monitor

odom_only:=true needs: working IMU yaw rate (otherwise the EKF never sees the robot turn),
calibrated motors, an empty floor, and your hand on the kill switch. It has NO obstacle protection
unless the ToF / lidar are live. Do NOT run it together with RTAB-Map (both would publish map->odom).
"""
import os
import tempfile
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

LIDAR_SOURCE = 'lidar'     # observation source name used for /scan in the nav2 params files


def drop_source(d, name):
    """Remove observation source `name` everywhere: from `observation_sources` (space-separated string for costmap
    layers, list for collision_monitor) and its own parameter block. Without this, with_lidar:=false would leave the
    collision monitor waiting on /scan (source_timeout 0.5 s) and it would never let the robot move."""
    for k, v in list(d.items()):
        if isinstance(v, dict):
            drop_source(v, name)
        elif k == 'observation_sources':
            if isinstance(v, str):
                d[k] = ' '.join(s for s in v.split() if s != name)
            elif isinstance(v, list):
                d[k] = [s for s in v if s != name]
    if 'observation_sources' in d and name in d:
        del d[name]


def write_nav2_params(src, map_topic, with_lidar):
    """Copy `src` to a temp yaml with every `map_topic` value replaced (what RewrittenYaml's param_rewrites did), and
    return (path, data). Done by hand so the file Nav2 reads is a plain path we can print and inspect: on the robot
    Nav2 ran on its built-in defaults (no critics, max_vel_x 0.0, costmap on /map) instead of this file."""
    with open(src) as f:
        data = yaml.safe_load(f)

    def sub(d):
        for k, v in d.items():
            if isinstance(v, dict):
                sub(v)
            elif k == 'map_topic':
                d[k] = map_topic
    sub(data)
    if not with_lidar:
        drop_source(data, LIDAR_SOURCE)
    out = os.path.join(tempfile.gettempdir(), 'goosebot_nav2_params.yaml')
    with open(out, 'w') as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return out, data


def _setup(context):
    share = get_package_share_directory('goosebot_hw')
    nav2 = get_package_share_directory('nav2_bringup')
    odom_only = LaunchConfiguration('odom_only').perform(context).lower() in ('true', '1')
    with_lidar = LaunchConfiguration('with_lidar').perform(context).lower() in ('true', '1')
    fname = 'nav2_params_odom_only.yaml' if odom_only else 'nav2_params.yaml'
    map_topic = LaunchConfiguration('map_topic').perform(context)
    params, data = write_nav2_params(os.path.join(share, 'config', fname), map_topic, with_lidar)
    fp = (data.get('controller_server', {}).get('ros__parameters', {}) or {}).get('FollowPath', {}) or {}
    cm = (data.get('collision_monitor', {}).get('ros__parameters', {}) or {}).get('observation_sources')
    actions = [LogInfo(msg=f"[hw_nav2] Nav2 parameter file: {params} (from {fname}, map_topic={map_topic}); "
                           f"FollowPath.critics={fp.get('critics')}, max_vel_x={fp.get('max_vel_x')}, "
                           f"collision_monitor sources={cm}"),
               IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2, 'launch', 'navigation_launch.py')),
        launch_arguments={'use_sim_time': 'false', 'params_file': params,
                          'namespace': ''}.items())]
    if odom_only:
        actions.append(Node(
            package='tf2_ros', executable='static_transform_publisher', name='static_map_to_odom',
            arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0',
                       '--frame-id', 'map', '--child-frame-id', 'odom']))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('odom_only', default_value='false'),
        DeclareLaunchArgument('map_topic', default_value='/rtabmap/map',
                              description='where the costmap static layer reads the map (/map for map_server)'),
        DeclareLaunchArgument('with_lidar', default_value='true',
                              description='false = remove the /scan source from costmaps and collision monitor'),
        OpaqueFunction(function=_setup),
    ])
