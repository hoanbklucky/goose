"""
One launch for the whole robot: hw_bringup + hw_slam + hw_nav2, with map handling.

  ros2 launch goosebot_hw hw_robot.launch.py                                  # new map, auto-named, no Nav2
  ros2 launch goosebot_hw hw_robot.launch.py write:=lab                       # new map 'lab'
  ros2 launch goosebot_hw hw_robot.launch.py read:=lab                        # navigate on 'lab', keep learning, DON'T save
  ros2 launch goosebot_hw hw_robot.launch.py read:=lab write:=lab             # update 'lab' in place (backup kept)
  ros2 launch goosebot_hw hw_robot.launch.py read:=lab write:=lab2            # duplicate: updated copy saved as 'lab2'
  ros2 launch goosebot_hw hw_robot.launch.py read:=lab static:=true           # RTAB-Map localizes only; map never changes
  ros2 launch goosebot_hw hw_robot.launch.py read:=lab rtab:=false            # no RTAB-Map: trust the saved grid; robot assumed to start at the map origin

Other arguments: overwrite:=true (skip the "replace existing map?" question, for non-interactive use),
  with_imu / with_tof / with_stereo (stereo defaults to off when rtab:=false), with_nav2 (defaults to off for a new map).
Maps live in the folder set by maps.dir in config/slam_params.yaml. See goosebot_hw/map_session.py for the rules.
Startup relocalization (config/slam_params.yaml, relocalization.mode = auto | manual | off): when a map is loaded with
RTAB-Map on, Nav2 starts only after the robot has recognised its surroundings on that map. auto turns the robot in place
to look around; manual waits while you rotate it by hand; off starts Nav2 immediately. dynamic/update/duplicate start
RTAB-Map in localization mode and switch it to mapping only after the robot has localized; with mode off they start
mapping at once, and the new session only joins the old map when RTAB-Map happens to recognise a place.
Stop with ONE Ctrl+C and wait: saving a map (update/duplicate) happens after RTAB-Map has shut down.
"""
import atexit
import datetime
import os
import sys

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from goosebot_hw.map_session import (PlanError, ask_confirm_factory, finalize, make_plan, prepare)


def _setup(context):
    lc = lambda n: LaunchConfiguration(n).perform(context).strip()
    flag = lambda s: s.lower() in ('true', '1', 'yes')
    share = get_package_share_directory('goosebot_hw')
    with open(os.path.join(share, 'config', 'slam_params.yaml')) as f:
        cfg = yaml.safe_load(f) or {}
    maps_cfg = cfg.get('maps', {}) or {}
    maps_dir = os.path.expanduser(maps_cfg.get('dir', '~/goosebot_maps'))
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    rl = cfg.get('relocalization', {}) or {}
    rl_mode = str(rl.get('mode', 'auto')).lower()
    if rl_mode not in ('auto', 'manual', 'off'):
        print(f"\nERROR: slam_params.yaml relocalization.mode must be auto, manual or off, not '{rl_mode}'\n",
              file=sys.stderr)
        sys.exit(1)

    try:
        plan = make_plan(lc('read'), lc('write'), flag(lc('static')), flag(lc('rtab')), maps_dir, stamp,
                         ask_confirm_factory(flag(lc('overwrite'))),
                         copy_for_static=bool(maps_cfg.get('copy_for_static', True)))
        prepare(plan, maps_dir, stamp)
    except PlanError as e:
        print(f'\nERROR: {e}\n', file=sys.stderr)
        sys.exit(1)
    atexit.register(finalize, plan, maps_dir, stamp)       # runs after the launch (and RTAB-Map) has shut down
    print(f'\n[maps] {plan.summary}\n[maps] folder: {maps_dir}\n')

    with_stereo = flag(lc('with_stereo')) if lc('with_stereo') else plan.rtab
    with_nav2 = flag(lc('with_nav2')) if lc('with_nav2') else plan.mode != 'new_map'

    def inc(name, args):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(share, 'launch', name)),
            launch_arguments={k: str(v) for k, v in args.items()}.items())

    actions = [inc('hw_bringup.launch.py', {'with_imu': lc('with_imu'), 'with_tof': lc('with_tof'),
                                            'with_stereo': str(with_stereo).lower()})]
    relocalize = plan.rtab and bool(plan.read) and rl_mode != 'off'
    learns = plan.mode in ('dynamic', 'update', 'duplicate')
    if plan.rtab:
        # With relocalization on, a loaded map that keeps learning STARTS in localization mode (nothing is added, so
        # the original map cannot be polluted before the robot has found itself); relocalize_node flips it to mapping.
        slam_localization = plan.localization or (relocalize and learns)
        actions.append(inc('hw_slam.launch.py', {
            'localization': str(slam_localization).lower(), 'delete_db': str(plan.delete_db).lower(),
            'database_path': plan.db_path}))
    if plan.export_prefix:
        actions.append(Node(package='goosebot_hw', executable='map_export_node', name='map_export', output='screen',
                            parameters=[{'prefix': plan.export_prefix,
                                         'period_s': float(maps_cfg.get('autosave_period_s', 30.0))}]))
    nav2_actions = []
    if with_nav2:
        nav2_actions.append(inc('hw_nav2.launch.py', {'map_topic': '/rtabmap/map' if plan.rtab else '/map'}))
        if not plan.rtab:
            nav2_actions += [
                Node(package='nav2_map_server', executable='map_server', name='map_server', output='screen',
                     parameters=[{'yaml_filename': plan.map_yaml, 'use_sim_time': False}]),
                Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_map',
                     output='screen', parameters=[{'autostart': True, 'node_names': ['map_server'],
                                                   'use_sim_time': False}]),
                # no RTAB-Map => no vision => nobody publishes map->odom. The robot is assumed to start at the map
                # origin, so map->odom is the identity. Nothing corrects drift afterwards.
                Node(package='tf2_ros', executable='static_transform_publisher', name='static_map_to_odom',
                     arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0',
                                '--frame-id', 'map', '--child-frame-id', 'odom']),
            ]
    if relocalize:
        reloc = Node(package='goosebot_hw', executable='relocalize_node', name='relocalize', output='screen',
                     parameters=[{'mode': rl_mode, 'timeout_s': float(rl.get('timeout_s', 90.0)),
                                  'spin_speed': float(rl.get('spin_speed', 0.8)),
                                  'step_deg': float(rl.get('step_deg', 30.0)),
                                  'pause_s': float(rl.get('pause_s', 2.0)),
                                  'max_covariance': float(rl.get('max_covariance', 1.0)),
                                  'then_mapping': learns}])
        actions.append(reloc)
        if nav2_actions:
            # Nav2 starts only if the node exits with code 0 (= localized), never on a crash or during shutdown
            actions.append(RegisterEventHandler(OnProcessExit(
                target_action=reloc,
                on_exit=lambda event, ctx: (nav2_actions if event.returncode == 0
                                            and not getattr(ctx, 'is_shutdown', False) else None))))
    else:
        actions += nav2_actions
    return actions


def generate_launch_description():
    D = DeclareLaunchArgument
    return LaunchDescription([
        D('read', default_value='', description='existing map to start from'),
        D('write', default_value='', description='name to save the (updated) map under'),
        D('static', default_value='false', description='localize on the map but never change it'),
        D('rtab', default_value='true', description='false = no RTAB-Map; trust the saved grid and a fixed start pose'),
        D('overwrite', default_value='false', description='true = do not ask before replacing an existing map'),
        D('with_imu', default_value='true'),
        D('with_tof', default_value='true'),
        D('with_stereo', default_value='', description='default: on with rtab:=true, off with rtab:=false'),
        D('with_nav2', default_value='', description='default: off for a new map, on otherwise'),
        OpaqueFunction(function=_setup),
    ])
