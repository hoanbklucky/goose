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

    # Default to the same turtlebot3 world you already tested with,
    # but allow overriding it with world:=/path/to/your.world
    tb3_gazebo_share = get_package_share_directory('turtlebot3_gazebo')
    default_world_file = os.path.join(tb3_gazebo_share, 'worlds', 'turtlebot3_world.world')

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