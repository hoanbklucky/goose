"""
Stereo RTAB-Map on hardware. Run after hw_bringup.launch.py. Derived from sim stereo_slam.launch.py:
 - no stereo_camera_info_fixer (real CameraInfo comes from your calibration)
 - consumes RECTIFIED images from stereo_image_proc
 - use_sim_time false, viz off by default (run rtabmap_viz on your laptop, not the Rock 5C)
 - mapping/localization switch + persistent database
  mapping:       ros2 launch goosebot_hw hw_slam.launch.py
  localization:  ros2 launch goosebot_hw hw_slam.launch.py localization:=true
  continue a map: ros2 launch goosebot_hw hw_slam.launch.py delete_db:=false database_path:=/path/map.db
                  (mapping that KEEPS the existing database and adds to it; default delete_db:=true is the old behaviour)
Normally started through hw_robot.launch.py, which picks the database and the mode from read:=/write:=.
"""
import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression


def load_cutoff_args(path):
    """config/slam_params.yaml -> list of RTAB-Map '--Param value' strings. 0 means no cutoff."""
    with open(path) as f:
        cut = (yaml.safe_load(f) or {}).get('cutoffs', {}) or {}
    top = float(cut.get('top', 0.0))
    if top < 0.0:
        raise RuntimeError('slam_params.yaml: cutoffs.top must be >= 0 (metres above the floor)')
    return [f'--Grid/MaxObstacleHeight {top}'] if top > 0.0 else []


def load_start_at_origin(path):
    """config/slam_params.yaml localization.start_at_origin -> bool (RTAB-Map default is false)."""
    with open(path) as f:
        return bool(((yaml.safe_load(f) or {}).get('localization', {}) or {}).get('start_at_origin', False))


def generate_launch_description():
    slam_params = os.path.join(get_package_share_directory('goosebot_hw'), 'config', 'slam_params.yaml')
    start_at_origin = load_start_at_origin(slam_params)
    cutoff_args = load_cutoff_args(slam_params)
    common = [
        '--Grid/RangeMax 2.0', '--Grid/RayTracing true',
        '--Grid/NoiseFilteringRadius 0.1', '--Grid/NoiseFilteringMinNeighbors 4',
        '--Grid/MinClusterSize 10', '--Reg/Force3DoF true',
        '--Rtabmap/DetectionRate 1',       # sim used 2 Hz; 1 Hz keeps CPU/RAM load down on the 2 GB board
    ] + cutoff_args
    mapping_args = ' '.join(['--delete_db_on_start'] + common)
    # mapping that continues an existing database: no delete, and load every old node so loop closure can
    # recognise places from earlier sessions (RAM grows with map size: fine for small maps)
    continue_args = ' '.join(common + ['--Mem/InitWMWithAllNodes true'])
    loc_args = ' '.join(common + ['--Mem/IncrementalMemory false', '--Mem/InitWMWithAllNodes true',
                                  f'--RGBD/StartAtOrigin {str(start_at_origin).lower()}'])
    loc, dele = LaunchConfiguration('localization'), LaunchConfiguration('delete_db')
    mapping_fresh = IfCondition(PythonExpression(["'", loc, "'.lower() == 'false' and '", dele, "'.lower() == 'true'"]))
    mapping_continue = IfCondition(PythonExpression(["'", loc, "'.lower() == 'false' and '", dele, "'.lower() == 'false'"]))

    def include(args_str, cond):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                get_package_share_directory('rtabmap_launch'), 'launch', 'rtabmap.launch.py'])),
            launch_arguments=[
                ('stereo', 'true'), ('use_sim_time', 'false'),
                ('frame_id', 'base_footprint'),
                ('left_image_topic', '/stereo/left/image_rect'),
                ('right_image_topic', '/stereo/right/image_rect'),
                ('left_camera_info_topic', '/stereo/left/camera_info'),
                ('right_camera_info_topic', '/stereo/right/camera_info'),
                ('approx_sync', 'true'),
                ('approx_sync_max_interval', '0.05'),
                ('wait_for_transform', '0.5'),
                ('visual_odometry', 'false'),            # EKF is the odom source (same as sim)
                ('odom_topic', '/odometry/filtered'),
                ('rtabmap_args', args_str),
                ('database_path', LaunchConfiguration('database_path')),
                ('rtabmap_viz', LaunchConfiguration('rtabmap_viz')),
                ('rviz', 'false'),
            ], condition=cond)

    return LaunchDescription([
        DeclareLaunchArgument('localization', default_value='false'),
        DeclareLaunchArgument('delete_db', default_value='true',
                              description='mapping only: true (old behaviour) wipes the database at start'),
        DeclareLaunchArgument('database_path', default_value='~/.ros/goosebot_rtabmap.db'),
        DeclareLaunchArgument('rtabmap_viz', default_value='false'),
        include(mapping_args, mapping_fresh),
        include(continue_args, mapping_continue),
        include(loc_args, IfCondition(LaunchConfiguration('localization'))),
    ])
