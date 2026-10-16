"""
Base hardware bringup: drivers + TF + EKF.
  ros2 launch goosebot_hw hw_bringup.launch.py with_imu:=false with_tof:=false with_stereo:=false   # motors only
Args (all default true): with_imu, with_tof, with_stereo

Changes vs the original:
  * with_imu / with_tof switches, so you can bench the parts that are installed. imu_node and tof_node
    raise on start when their hardware is missing (SMBus write fails / VL53L1X not found).
  * stereo_image_proc: the standalone `stereo_image_proc` executable does not exist in Jazzy (docs say use
    stereo_image_proc.launch.py), so the old Node(...) would fail with "executable not found". Now included.
  * Removed use_system_default_qos:=True. stereo_camera_node publishes with sensor-data QoS (BEST_EFFORT);
    a RELIABLE subscriber cannot match a BEST_EFFORT publisher, so nothing would be received.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('goosebot_hw')
    params = os.path.join(share, 'config', 'hw_params.yaml')
    ekf = os.path.join(share, 'config', 'ekf_hw.yaml')
    xacro_file = os.path.join(share, 'urdf', 'robot_hw.urdf.xacro')
    with_stereo = LaunchConfiguration('with_stereo')

    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               parameters=[{'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str),
                            'use_sim_time': False}])

    def n(exe, name, **kw):
        return Node(package='goosebot_hw', executable=exe, name=name, output='screen',
                    parameters=[params], **kw)

    stereo_proc = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            get_package_share_directory('stereo_image_proc'), 'launch', 'stereo_image_proc.launch.py'])),
        launch_arguments=[('namespace', 'stereo'), ('approximate_sync', 'True')],
        condition=IfCondition(with_stereo))

    return LaunchDescription([
        DeclareLaunchArgument('with_imu', default_value='true'),
        DeclareLaunchArgument('with_tof', default_value='true'),
        DeclareLaunchArgument('with_stereo', default_value='true'),
        rsp,
        n('motor_driver_node', 'motor_driver'),
        n('cmd_vel_mux_node', 'cmd_vel_mux'),
        n('imu_node', 'imu_node', condition=IfCondition(LaunchConfiguration('with_imu'))),
        n('tof_node', 'tof_node', condition=IfCondition(LaunchConfiguration('with_tof'))),
        n('cmd_vel_to_odom', 'cmd_vel_to_odom',
          remappings=[('/odom_cmdvel', '/odom_cmdvel')]),
        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
             output='screen', parameters=[ekf]),
        Node(package='goosebot_hw', executable='stereo_camera_node', name='stereo_camera',
             output='screen', parameters=[params], condition=IfCondition(with_stereo)),
        stereo_proc,
    ])
