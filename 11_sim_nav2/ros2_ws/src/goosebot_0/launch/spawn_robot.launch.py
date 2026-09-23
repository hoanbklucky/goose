import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('goosebot_0')
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    bridge_config = os.path.join(pkg_share, 'config', 'ros_gz_bridge.yaml')
    ekf_config = os.path.join(pkg_share, 'config', 'ekf.yaml')

    # Defaults to maze.world since that's what the baked ground-truth map
    # (goosebot_0/maps/map.yaml) matches. Uses get_package_share_directory,
    # same as xacro_file above, which correctly resolves to worlds/maze.world
    # as installed by CMakeLists.txt's `install(DIRECTORY ... worlds ...)` --
    # works whether or not you built with --symlink-install, unlike the old
    # __file__-relative '..'/'..' trick this replaces.
    default_world_file = os.path.join(pkg_share, 'worlds', 'maze.world')

    world_arg = DeclareLaunchArgument(
        'world',
        default_value=default_world_file,
        description='Full path to the Gazebo (gz-sim) world file to load'
    )

    # --- Spawn pose, now overridable instead of hardcoded ---
    # Defaults are placeholders (0,0,0.05) and may well land inside a maze
    # wall depending on how maze.world's geometry sits relative to the
    # origin -- verify visually in the gz-sim GUI (or against map.pgm)
    # before trusting a default, and override with x:=... y:=... yaw:=...
    # on the command line for any spot other than "known good".
    x_arg = DeclareLaunchArgument('x', default_value='0.0', description='Spawn X (m, world frame)')
    y_arg = DeclareLaunchArgument('y', default_value='0.0', description='Spawn Y (m, world frame)')
    z_arg = DeclareLaunchArgument('z', default_value='0.05', description='Spawn Z (m, world frame)')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0', description='Spawn yaw (rad)')
    entity_name_arg = DeclareLaunchArgument(
        'entity_name', default_value='custom_bot',
        description='Name the robot is spawned under in gz-sim'
    )

    world_file = LaunchConfiguration('world')
    spawn_x = LaunchConfiguration('x')
    spawn_y = LaunchConfiguration('y')
    spawn_z = LaunchConfiguration('z')
    spawn_yaw = LaunchConfiguration('yaw')
    entity_name = LaunchConfiguration('entity_name')

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'),
                         'launch', 'gz_sim.launch.py')
        ),
        # -r auto-starts the sim; drop it if you'd rather have gz-sim load
        # paused so you can eyeball the spawn point before it can drive off
        launch_arguments={'gz_args': [world_file, ' -r']}.items()
    )

    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }]
    )

    # ros_gz_sim's "create" replaces gazebo_ros's spawn_entity.py.
    # Same -x/-y/-z/-R/-P/-Y flag names as the old node, just now fed from
    # LaunchConfigurations instead of literals.
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', entity_name,
            '-x', spawn_x,
            '-y', spawn_y,
            '-z', spawn_z,
            '-Y', spawn_yaw,
        ],
        output='screen'
    )

    # gz <-> ROS bridge for cmd_vel, odom, tf, ground-truth pose, sensors, clock
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        parameters=[{'config_file': bridge_config, 'use_sim_time': True}],
        output='screen',
    )

    # Open-loop dead-reckoning source (STEP 5). Publishes /odom_cmdvel only --
    # its own TF broadcast stays off (default publish_tf:=False); the EKF
    # below owns odom->base_footprint instead (STEP 6/7). Do not add
    # publish_tf:=True here, or you get the double-publisher bug again.
    cmd_vel_to_odom = Node(
        package='goosebot_0',
        executable='cmd_vel_to_odom.py',
        name='cmd_vel_to_odom',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # STEP 6: fuses /odom_cmdvel (translation only) + IMU (heading) into
    # /odometry/filtered, and owns odom->base_footprint TF (ekf.yaml sets
    # publish_tf: true). Must start after cmd_vel_to_odom is publishing, or
    # it'll simply see no odom0 input -- order in this list doesn't
    # guarantee startup order, but both are lightweight/fast nodes and this
    # hasn't needed an explicit delay in practice.
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config],
    )

    return LaunchDescription([
        world_arg,
        x_arg,
        y_arg,
        z_arg,
        yaw_arg,
        entity_name_arg,
        gz_sim,
        robot_state_publisher,
        spawn_entity,
        bridge,
        cmd_vel_to_odom,
        ekf_node,
    ])
