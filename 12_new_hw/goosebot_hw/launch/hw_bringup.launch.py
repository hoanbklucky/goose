"""
Base hardware bringup: drivers + TF + EKF.
  ros2 launch goosebot_hw hw_bringup.launch.py with_imu:=false with_tof:=false with_stereo:=false   # motors only
Args (all default true): with_imu, with_tof, with_stereo, cam_controls
Camera lock args: cam_exposure (default 80, units of 100 us), cam_gain (32), cam_wb (4600 K),
  cam_controls_script (default ../calibration/set_cam_controls.sh, relative to this launch file)

Changes vs the original:
  * with_imu / with_tof switches, so you can bench the parts that are installed. imu_node and tof_node
    raise on start when their hardware is missing (SMBus write fails / VL53L1X not found).
  * stereo_image_proc: the standalone `stereo_image_proc` executable does not exist in Jazzy (docs say use
    stereo_image_proc.launch.py), so the old Node(...) would fail with "executable not found". Now included.
  * cam_controls: a few seconds after the camera node starts, runs set_cam_controls.sh to lock auto exposure /
    white balance / dynamic framerate on both webcams. Skipped if with_stereo:=false or cam_controls:=false.
  * Removed use_system_default_qos:=True. stereo_camera_node publishes with sensor-data QoS (BEST_EFFORT);
    a RELIABLE subscriber cannot match a BEST_EFFORT publisher, so nothing would be received.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('goosebot_hw')
    params = os.path.join(share, 'config', 'hw_params.yaml')
    ekf = os.path.join(share, 'config', 'ekf_hw.yaml')
    xacro_file = os.path.join(share, 'urdf', 'robot_hw.urdf.xacro')
    with_stereo = LaunchConfiguration('with_stereo')
    # ../calibration relative to THIS launch file (works from the source tree with --symlink-install, and from the
    # installed share/ dir otherwise, since setup.py installs calibration/* next to launch/).
    cam_script_default = os.path.normpath(os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'calibration', 'set_camera_controls.sh'))

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

    # Lock the webcams' auto controls. Runs after the camera node has opened the devices, so settings the
    # camera resets on stream start get re-applied. Harmless if the script is missing (bash just prints an error).
    cam_controls = TimerAction(period=6.0, actions=[
        ExecuteProcess(
            cmd=['bash', LaunchConfiguration('cam_controls_script'),
                 LaunchConfiguration('cam_exposure'), LaunchConfiguration('cam_gain'),
                 LaunchConfiguration('cam_wb')],
            output='screen',
            condition=IfCondition(PythonExpression([
                "'", with_stereo, "'.lower() == 'true' and '", LaunchConfiguration('cam_controls'),
                "'.lower() == 'true'"]))),
    ])

    return LaunchDescription([
        DeclareLaunchArgument('with_imu', default_value='true'),
        DeclareLaunchArgument('with_tof', default_value='true'),
        DeclareLaunchArgument('with_stereo', default_value='true'),
        DeclareLaunchArgument('cam_controls', default_value='true'),
        DeclareLaunchArgument('cam_controls_script',
                              default_value=cam_script_default),
        DeclareLaunchArgument('cam_exposure', default_value='80'),
        DeclareLaunchArgument('cam_gain', default_value='32'),
        DeclareLaunchArgument('cam_wb', default_value='4600'),
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
        cam_controls,
    ])