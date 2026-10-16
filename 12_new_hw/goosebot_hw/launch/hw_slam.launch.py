"""
Stereo RTAB-Map on hardware. Run after hw_bringup.launch.py. Derived from sim stereo_slam.launch.py:
 - no stereo_camera_info_fixer (real CameraInfo comes from your calibration)
 - consumes RECTIFIED images from stereo_image_proc
 - use_sim_time false, viz off by default (run rtabmap_viz on your laptop, not the Rock 5C)
 - mapping/localization switch + persistent database
  mapping:       ros2 launch goosebot_hw hw_slam.launch.py
  localization:  ros2 launch goosebot_hw hw_slam.launch.py localization:=true
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution


def generate_launch_description():
    common = [
        '--Grid/RangeMax 2.0', '--Grid/RayTracing true',
        '--Grid/NoiseFilteringRadius 0.1', '--Grid/NoiseFilteringMinNeighbors 4',
        '--Grid/MinClusterSize 10', '--Reg/Force3DoF true',
        '--Rtabmap/DetectionRate 1',       # sim used 2 Hz; 1 Hz for a 4 GB board sharing the NPU job
    ]
    mapping_args = ' '.join(['--delete_db_on_start'] + common)
    loc_args = ' '.join(common + ['--Mem/IncrementalMemory false', '--Mem/InitWMWithAllNodes true'])

    def include(args_str, cond):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                get_package_share_directory('rtabmap_launch'), 'launch', 'rtabmap.launch.py'])),
            launch_arguments=[
                ('stereo', 'true'), ('use_sim_time', 'false'),
                ('frame_id', 'base_footprint'),
                ('left_image_topic', '/stereo/left/image_rect_color'),
                ('right_image_topic', '/stereo/right/image_rect'),
                ('left_camera_info_topic', '/stereo/left/camera_info'),
                ('right_camera_info_topic', '/stereo/right/camera_info'),
                ('approx_sync', 'true'),
                ('visual_odometry', 'false'),            # EKF is the odom source (same as sim)
                ('odom_topic', '/odometry/filtered'),
                ('rtabmap_args', args_str),
                ('database_path', LaunchConfiguration('database_path')),
                ('rtabmap_viz', LaunchConfiguration('rtabmap_viz')),
                ('rviz', 'false'),
            ], condition=cond)

    return LaunchDescription([
        DeclareLaunchArgument('localization', default_value='false'),
        DeclareLaunchArgument('database_path', default_value='~/.ros/goosebot_rtabmap.db'),
        DeclareLaunchArgument('rtabmap_viz', default_value='false'),
        include(mapping_args, UnlessCondition(LaunchConfiguration('localization'))),
        include(loc_args, IfCondition(LaunchConfiguration('localization'))),
    ])
