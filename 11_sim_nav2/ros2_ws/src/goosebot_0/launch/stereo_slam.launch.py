"""
Stereo RTAB-Map SLAM for goosebot_0 (sim).

Run AFTER (or alongside) spawn_robot.launch.py:
  ros2 launch goosebot_0 spawn_robot.launch.py
  ros2 launch goosebot_0 stereo_slam.launch.py
  (optional, Nav2 on top of the SLAM map)
  ros2 launch goosebot_0 nav2_bringup.launch.py slam:=true

Design choices (see chat notes for the tradeoffs):
  * Odometry comes from the existing EKF (/odometry/filtered, TF
    odom->base_footprint). RTAB-Map's own visual odometry is OFF so it does
    not publish a second odom->base_footprint and recreate the
    double-publisher bug ekf.yaml warns about.
  * RTAB-Map owns map->odom. Do not run the ground-truth bridge at the same
    time (nav2_bringup.launch.py slam:=true already skips it).
  * No stereo_image_proc: sim images are distortion-free and parallel.
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def ParameterValueFloat(sub):
    return ParameterValue(sub, value_type=float)


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')

    args = [
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'baseline', default_value='0.09',
            description='Stereo baseline in m; must equal stereo_baseline in robot.urdf.xacro'),
        DeclareLaunchArgument('rtabmap_viz', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument(
            'rtabmap_args',
            default_value=' '.join([
                '--delete_db_on_start',       # fresh map each run
                '--Grid/RangeMax 2.0',        # stereo depth is noisy past ~2 m
                '--Grid/RayTracing true',     # clear stray obstacle cells
                '--Grid/NoiseFilteringRadius 0.1',
                '--Grid/NoiseFilteringMinNeighbors 4',
                '--Grid/MinClusterSize 10',   # drop small isolated blobs
                '--Reg/Force3DoF true',       # planar robot: no z/roll/pitch (also sets 2D optimizer)
                '--Rtabmap/DetectionRate 2',  # 2 Hz (stereo images arrive ~5 Hz)
            ]),
            description='Extra RTAB-Map args; default starts a fresh map each '
                        'run and applies stereo-noise / planar-robot tuning'),
        DeclareLaunchArgument('approx_sync', default_value='true'),
    ]

    info_fixer = Node(
        package='goosebot_0',
        executable='stereo_camera_info_fixer.py',
        name='stereo_camera_info_fixer',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'baseline': ParameterValueFloat(LaunchConfiguration('baseline')),
        }],
    )

    rtabmap = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            get_package_share_directory('rtabmap_launch'),
            'launch', 'rtabmap.launch.py'])),
        launch_arguments=[
            ('stereo', 'true'),
            ('use_sim_time', use_sim_time),
            ('frame_id', 'base_footprint'),
            ('left_image_topic', '/stereo/left/image_raw'),
            ('right_image_topic', '/stereo/right/image_raw'),
            ('left_camera_info_topic', '/stereo/left/camera_info'),
            ('right_camera_info_topic', '/stereo/right/camera_info'),
            ('approx_sync', LaunchConfiguration('approx_sync')),
            # external odometry from the EKF, not RTAB-Map's own VO
            ('visual_odometry', 'false'),
            ('odom_topic', '/odometry/filtered'),
            ('rtabmap_args', LaunchConfiguration('rtabmap_args')),
            ('rtabmap_viz', LaunchConfiguration('rtabmap_viz')),
            ('rviz', LaunchConfiguration('rviz')),
        ],
    )

    return LaunchDescription(args + [info_fixer, rtabmap])
