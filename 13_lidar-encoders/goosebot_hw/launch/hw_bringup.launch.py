"""
Base hardware bringup: drivers + TF + EKF.
  ros2 launch goosebot_hw hw_bringup.launch.py with_imu:=false with_tof:=false with_stereo:=false   # motors only
Args (all default true): with_imu, with_tof, with_stereo, with_lidar, with_encoders, cam_controls
odom_source (default auto): what gives the EKF its forward speed. auto = wheel encoders when with_encoders is true,
  otherwise open-loop cmd_vel; encoders | cmd_vel force one. cmd_vel_to_odom always runs (for comparison).
lidar_odom (default false): run RTAB-Map's icp_odometry on /scan and fuse its velocity into the EKF (README).
  Needs with_lidar. Turn it on only after the plain lidar checks pass.
Settings files: hw_params.yaml (motors, IMU, ToF, cameras; yours, never shipped in updates), lidar_params.yaml,
  encoder_params.yaml (both loaded after hw_params.yaml).
stereo_proc (default minimal): minimal = only two rectify nodes (image_raw -> image_rect, what RTAB-Map reads);
  full = the stock stereo_image_proc launch (debayer, colour rectify, disparity, point cloud: ~6 extra nodes,
  only useful for RViz point clouds / debugging; costs a lot of CPU on the 2 GB board).
Camera image filter settings come from config/slam_params.yaml `image_filter:` (read at launch).
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
  * RPLIDAR C1 (sllidar_ros2, /scan) and optional lidar odometry (icp_odometry -> /odom_icp -> EKF odom1).
  * Front-wheel encoders (encoder_node -> /wheel/odom -> EKF odom0 in place of cmd_vel odometry).
"""
import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, LogInfo,
                            OpaqueFunction, TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterValue


def load_filter_params(path):
    """config/slam_params.yaml `image_filter:` -> stereo_camera node parameter dict (later params override hw_params).
    Unknown keys raise, so a typo cannot silently do nothing. Empty dict if the section is absent (code defaults apply)."""
    with open(path) as f:
        sec = (yaml.safe_load(f) or {}).get('image_filter', {}) or {}
    try:
        from goosebot_hw.image_filter import FilterParams
        known = set(vars(FilterParams()))
    except Exception:          # cv2 missing at launch time: skip validation, the node will still run
        known = None
    out = {}
    for k, v in sec.items():
        if k == 'enable':
            out['filter_enable'] = bool(v)
        elif k == 'log_period_s':
            out['filter_log_period_s'] = float(v)
        else:
            if known is not None and k not in known:
                raise RuntimeError(f'slam_params.yaml image_filter: unknown key {k!r}')
            out['filter.' + k] = v
    return out


# Lidar odometry: RTAB-Map's icp_odometry on the 2D scan. Starting values for a 10 Hz 2D lidar indoors; tune on the
# robot. publish_tf false: the EKF stays the only owner of odom->base_footprint. publish_null_when_lost false: when ICP
# loses track it publishes NOTHING, so the EKF times the source out (sensor_timeout) and falls back to cmd_vel + gyro,
# instead of being fed zero velocity.
ICP_ODOM_PARAMS = {
    'use_sim_time': False,
    'frame_id': 'base_footprint',
    'odom_frame_id': 'odom_icp',
    'publish_tf': False,
    'publish_null_when_lost': False,
    'wait_for_transform': 0.2,
    'Reg/Force3DoF': 'true',
    'Icp/VoxelSize': '0.05',
    'Icp/MaxCorrespondenceDistance': '0.1',
    'Icp/PointToPlane': 'false',
    'Odom/ScanKeyFrameThr': '0.6',
    'OdomF2M/ScanSubtractRadius': '0.05',
    'OdomF2M/ScanMaxSize': '2000',
}

# EKF override when the wheel encoders give the forward speed: same odom0 slot and config (vx only) as cmd_vel odometry,
# different topic. Using the encoders AND cmd_vel together would let the open-loop guess (which says "moving" during a
# stall) pull against the measurement, so it is one or the other.
EKF_ENCODERS = {'odom0': 'wheel/odom'}

# EKF additions when lidar_odom is on (merged over ekf_hw.yaml). Fuses forward velocity and yaw rate from scan
# matching. The gyro (imu0) keeps fusing yaw rate as well; the EKF weighs the two by their covariances.
EKF_LIDAR_ODOM = {
    'odom1': 'odom_icp',
    'odom1_config': [False, False, False,
                     False, False, False,
                     True,  False, False,
                     False, False, True,
                     False, False, False],
    'odom1_differential': False,
    'odom1_relative': False,
    'odom1_queue_size': 10,
}


def _ekf(context, ekf):
    """Pick the EKF inputs from the launch arguments: odom0 = encoders or cmd_vel, odom1 = lidar odometry or nothing."""
    lc = lambda n: LaunchConfiguration(n).perform(context).strip().lower()
    on = lambda n: lc(n) in ('true', '1', 'yes')
    src = lc('odom_source')
    if src not in ('auto', 'encoders', 'cmd_vel'):
        raise RuntimeError(f"odom_source must be auto, encoders or cmd_vel, not '{src}'")
    use_enc = on('with_encoders') if src == 'auto' else src == 'encoders'
    if use_enc and not on('with_encoders'):
        raise RuntimeError('odom_source:=encoders needs with_encoders:=true')
    use_icp = on('with_lidar') and on('lidar_odom')
    extra = ([EKF_ENCODERS] if use_enc else []) + ([EKF_LIDAR_ODOM] if use_icp else [])
    desc = (f"forward speed from {'wheel encoders (/wheel/odom)' if use_enc else 'open-loop cmd_vel (/odom_cmdvel)'}"
            f", yaw rate from gyro{' + lidar odometry (/odom_icp)' if use_icp else ''}")
    return [LogInfo(msg=f'[hw_bringup] EKF: {desc}'),
            Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
                 output='screen', parameters=[ekf] + extra)]


def generate_launch_description():
    share = get_package_share_directory('goosebot_hw')
    params = os.path.join(share, 'config', 'hw_params.yaml')
    lidar_params = os.path.join(share, 'config', 'lidar_params.yaml')
    encoder_params = os.path.join(share, 'config', 'encoder_params.yaml')
    ekf = os.path.join(share, 'config', 'ekf_hw.yaml')
    filter_params = load_filter_params(os.path.join(share, 'config', 'slam_params.yaml'))
    xacro_file = os.path.join(share, 'urdf', 'robot_hw.urdf.xacro')
    with_stereo = LaunchConfiguration('with_stereo')
    with_lidar = LaunchConfiguration('with_lidar')
    lidar_odom = LaunchConfiguration('lidar_odom')
    # ../calibration relative to THIS launch file (works from the source tree with --symlink-install, and from the
    # installed share/ dir otherwise, since setup.py installs calibration/* next to launch/).
    cam_script_default = os.path.normpath(os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'calibration', 'set_cam_controls.sh'))

    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               parameters=[{'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str),
                            'use_sim_time': False}])

    def n(exe, name, **kw):
        return Node(package='goosebot_hw', executable=exe, name=name, output='screen',
                    parameters=[params], **kw)

    stereo_mode = LaunchConfiguration('stereo_proc')
    cond_full = IfCondition(PythonExpression([
        "'", with_stereo, "'.lower() == 'true' and '", stereo_mode, "'.lower() == 'full'"]))
    cond_min = IfCondition(PythonExpression([
        "'", with_stereo, "'.lower() == 'true' and '", stereo_mode, "'.lower() == 'minimal'"]))
    use_lidar_odom = PythonExpression([
        "'", with_lidar, "'.lower() == 'true' and '", lidar_odom, "'.lower() == 'true'"])

    # full: the stock pipeline (debayer + colour/mono rectify + disparity + point cloud)
    stereo_proc = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            get_package_share_directory('stereo_image_proc'), 'launch', 'stereo_image_proc.launch.py'])),
        launch_arguments=[('namespace', 'stereo'), ('approximate_sync', 'True')],
        condition=cond_full)

    # minimal: same image_proc::RectifyNode plugin the stock launch uses for rectify_mono_node, fed straight from
    # image_raw (frames are already mono8, so debayer is pointless). Output: /stereo/{left,right}/image_rect.
    def rectify(side):
        return ComposableNode(
            package='image_proc', plugin='image_proc::RectifyNode',
            name=f'rectify_{side}', namespace=f'stereo/{side}',
            remappings=[('image', 'image_raw'), ('camera_info', 'camera_info'), ('image_rect', 'image_rect')])

    stereo_min = ComposableNodeContainer(
        name='stereo_rectify_container', namespace='stereo',
        package='rclcpp_components', executable='component_container_mt',
        composable_node_descriptions=[rectify('left'), rectify('right')],
        output='screen', condition=cond_min)

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

    # RPLIDAR C1. Parameters (port, baud 460800, frame lidar_link) live in config/lidar_params.yaml.
    lidar = Node(package='sllidar_ros2', executable='sllidar_node', name='lidar', output='screen',
                 parameters=[lidar_params], condition=IfCondition(with_lidar))

    # Front-wheel hall encoders -> /wheel/odom. Exits with an error until counts_per_rev is calibrated.
    encoders = Node(package='goosebot_hw', executable='encoder_node', name='encoder_node', output='screen',
                    parameters=[encoder_params], condition=IfCondition(LaunchConfiguration('with_encoders')))

    icp_odom = Node(package='rtabmap_odom', executable='icp_odometry', name='icp_odometry', output='screen',
                    parameters=[ICP_ODOM_PARAMS],
                    remappings=[('scan', '/scan'), ('odom', '/odom_icp')],
                    condition=IfCondition(use_lidar_odom))


    return LaunchDescription([
        DeclareLaunchArgument('with_imu', default_value='true'),
        DeclareLaunchArgument('with_tof', default_value='true'),
        DeclareLaunchArgument('with_stereo', default_value='true'),
        DeclareLaunchArgument('with_lidar', default_value='true',
                              description='RPLIDAR C1 on /scan (needs sllidar_ros2 built, README Part 6)'),
        DeclareLaunchArgument('with_encoders', default_value='true',
                              description='front-wheel encoders on /wheel/odom (needs counts_per_rev calibrated)'),
        DeclareLaunchArgument('odom_source', default_value='auto',
                              description='EKF forward speed: auto | encoders | cmd_vel'),
        DeclareLaunchArgument('lidar_odom', default_value='false',
                              description='fuse icp_odometry (scan matching) velocity into the EKF'),
        DeclareLaunchArgument('cam_controls', default_value='true'),
        DeclareLaunchArgument('stereo_proc', default_value='minimal',
                              description='minimal (rectify only) | full (stock stereo_image_proc)'),
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
        OpaqueFunction(function=_ekf, args=[ekf]),
        lidar,
        encoders,
        icp_odom,
        Node(package='goosebot_hw', executable='stereo_camera_node', name='stereo_camera',
             output='screen', parameters=[params] + ([filter_params] if filter_params else []),
             condition=IfCondition(with_stereo)),
        stereo_proc,
        stereo_min,
        cam_controls,
    ])
