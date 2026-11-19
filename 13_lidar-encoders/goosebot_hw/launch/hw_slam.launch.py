"""
Stereo (+ 2D lidar) RTAB-Map on hardware. Run after hw_bringup.launch.py. Derived from sim stereo_slam.launch.py:
 - no stereo_camera_info_fixer (real CameraInfo comes from your calibration)
 - consumes RECTIFIED images from stereo_image_proc
 - use_sim_time false, viz off by default (run rtabmap_viz on your laptop, not the Rock 5C)
 - mapping/localization switch + persistent database
 - with_lidar (default true): also subscribes to the RPLIDAR C1 /scan. Scans refine odometry between map nodes
   (ICP), refine loop closures, and (by default) build the occupancy grid. Settings: `lidar:` in slam_params.yaml.
   with_lidar MUST match hw_bringup: if RTAB-Map waits for /scan and nothing publishes it, no map is ever made.
  mapping:       ros2 launch goosebot_hw hw_slam.launch.py
  localization:  ros2 launch goosebot_hw hw_slam.launch.py localization:=true
  continue a map: ros2 launch goosebot_hw hw_slam.launch.py delete_db:=false database_path:=/path/map.db
                  (mapping that KEEPS the existing database and adds to it; default delete_db:=true is the old behaviour)
  no lidar:      ros2 launch goosebot_hw hw_slam.launch.py with_lidar:=false
Normally started through hw_robot.launch.py, which picks the database and the mode from read:=/write:=.
"""
import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

GRID_SENSORS = {'lidar': 0, 'stereo': 1, 'both': 2}     # RTAB-Map Grid/Sensor: 0 laser scan, 1 depth, 2 both


def load_cfg(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def cutoff_args(cfg):
    """`cutoffs:` -> list of RTAB-Map '--Param value' strings. 0 means no cutoff."""
    cut = cfg.get('cutoffs', {}) or {}
    top = float(cut.get('top', 0.0))
    if top < 0.0:
        raise RuntimeError('slam_params.yaml: cutoffs.top must be >= 0 (metres above the floor)')
    return [f'--Grid/MaxObstacleHeight {top}'] if top > 0.0 else []


def lidar_args(cfg):
    """`lidar:` -> (list of '--Param value' strings, grid range max, summary). Only used with with_lidar:=true."""
    li = cfg.get('lidar', {}) or {}
    sensor = str(li.get('grid_sensor', 'lidar')).lower()
    if sensor not in GRID_SENSORS:
        raise RuntimeError(f"slam_params.yaml lidar.grid_sensor must be lidar, stereo or both, not '{sensor}'")
    rng = float(li.get('grid_range_max', 0) or 0)
    if rng <= 0:                      # auto: stereo depth is poor past ~2 m, the lidar is good to several metres
        rng = 5.0 if sensor == 'lidar' else 2.0
    strategy = int(li.get('reg_strategy', 2))
    if strategy not in (0, 1, 2):
        raise RuntimeError('slam_params.yaml lidar.reg_strategy must be 0 (visual), 1 (ICP) or 2 (visual + ICP)')
    refine = bool(li.get('icp_refining', True))
    args = [f'--Grid/Sensor {GRID_SENSORS[sensor]}',
            f'--Reg/Strategy {strategy}',
            f'--RGBD/NeighborLinkRefining {str(refine).lower()}',
            f"--Icp/VoxelSize {float(li.get('icp_voxel_size', 0.05))}",
            f"--Icp/MaxCorrespondenceDistance {float(li.get('icp_max_correspondence', 0.1))}",
            '--Icp/PointToPlane false']
    summary = f'grid from {sensor} (RangeMax {rng} m), Reg/Strategy {strategy}, NeighborLinkRefining {refine}'
    return args, rng, summary


def _setup(context):
    lc = lambda n: LaunchConfiguration(n).perform(context).strip().lower()
    slam_params = os.path.join(get_package_share_directory('goosebot_hw'), 'config', 'slam_params.yaml')
    cfg = load_cfg(slam_params)
    start_at_origin = bool((cfg.get('localization', {}) or {}).get('start_at_origin', False))
    with_lidar = lc('with_lidar') in ('true', '1', 'yes')
    localization = lc('localization') in ('true', '1', 'yes')
    delete_db = lc('delete_db') in ('true', '1', 'yes')

    if with_lidar:
        l_args, range_max, l_summary = lidar_args(cfg)
    else:
        l_args, range_max, l_summary = [], 2.0, 'no lidar (stereo only)'

    common = [
        f'--Grid/RangeMax {range_max}', '--Grid/RayTracing true',
        '--Grid/NoiseFilteringRadius 0.1', '--Grid/NoiseFilteringMinNeighbors 4',
        '--Grid/MinClusterSize 10', '--Reg/Force3DoF true',
        '--Rtabmap/DetectionRate 1',       # sim used 2 Hz; 1 Hz keeps CPU/RAM load down on the 2 GB board
    ] + cutoff_args(cfg) + l_args

    if localization:
        # Localization: never adds to the map
        args = common + ['--Mem/IncrementalMemory false', '--Mem/InitWMWithAllNodes true',
                         f'--RGBD/StartAtOrigin {str(start_at_origin).lower()}']
        mode = 'localization'
    elif delete_db:
        args = ['--delete_db_on_start'] + common
        mode = 'mapping (fresh database)'
    else:
        # mapping that continues an existing database: no delete, and load every old node so loop closure can
        # recognise places from earlier sessions (RAM grows with map size: fine for small maps)
        args = common + ['--Mem/InitWMWithAllNodes true']
        mode = 'mapping (continue database)'

    launch_args = [
        ('stereo', 'true'), ('use_sim_time', 'false'),
        ('frame_id', 'base_footprint'),
        ('left_image_topic', '/stereo/left/image_rect'),
        ('right_image_topic', '/stereo/right/image_rect'),
        ('left_camera_info_topic', '/stereo/left/camera_info'),
        ('right_camera_info_topic', '/stereo/right/camera_info'),
        ('approx_sync', 'true'),
        # 10 Hz lidar: the nearest scan can be up to ~50 ms from an image pair, so 0.05 s would drop many frames.
        ('approx_sync_max_interval', '0.1' if with_lidar else '0.05'),
        ('wait_for_transform', '0.5'),
        ('visual_odometry', 'false'),            # EKF is the odom source (same as sim)
        ('odom_topic', '/odometry/filtered'),
        ('subscribe_scan', 'true' if with_lidar else 'false'),
        ('scan_topic', '/scan'),
        ('rtabmap_args', ' '.join(args)),
        ('database_path', LaunchConfiguration('database_path').perform(context)),
        ('rtabmap_viz', LaunchConfiguration('rtabmap_viz').perform(context)),
        ('rviz', 'false'),
    ]
    return [
        LogInfo(msg=f'[hw_slam] {mode}; {l_summary}'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('rtabmap_launch'), 'launch', 'rtabmap.launch.py')),
            launch_arguments=launch_args),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('localization', default_value='false'),
        DeclareLaunchArgument('delete_db', default_value='true',
                              description='mapping only: true (old behaviour) wipes the database at start'),
        DeclareLaunchArgument('database_path', default_value='~/.ros/goosebot_rtabmap.db'),
        DeclareLaunchArgument('rtabmap_viz', default_value='false'),
        DeclareLaunchArgument('with_lidar', default_value='true',
                              description='subscribe to /scan (must match hw_bringup with_lidar)'),
        OpaqueFunction(function=_setup),
    ])
