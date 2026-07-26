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

    # Defaults to brick_area.world since that's what the baked ground-truth
    # map (goosebot_0/maps/map.yaml) matches. Resolved relative to this launch
    # file's own location, which only works because commands.txt builds with
    # --symlink-install (the installed file is a symlink back into src/).
    # If you ever build without --symlink-install, pass world:=/path/to/brick_area.world
    # explicitly instead, same as commands.txt already does.
    default_world_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'brick_area.world')
    )

    world_arg = DeclareLaunchArgument(
        'world',
        default_value=default_world_file,
        description='Full path to the Gazebo world file to load'
    )

    world_file = LaunchConfiguration('world')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'),
                         'launch', 'gazebo.launch.py')
        ),
        launch_arguments={'world': world_file}.items()
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

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'custom_bot',
                   '-x', '0', '-y', '0', '-z', '0.05'],
        output='screen'
    )

    return LaunchDescription([
        world_arg,
        gazebo,
        robot_state_publisher,
        spawn_entity,
    ])