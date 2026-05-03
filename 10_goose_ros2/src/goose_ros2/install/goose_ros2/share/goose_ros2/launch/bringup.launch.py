# bringup.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='goose_ros2',
            executable='perception_node',
            name='perception_node',
            output='screen'
        ),
        Node(
            package='goose_ros2',
            executable='control_node',
            name='control_node',
            output='screen'
        ),
        Node(
            package='goose_ros2',
            executable='motor_node',
            name='motor_node',
            output='screen'
        ),
        Node(
            package='goose_ros2',
            executable='web_stream_node',
            name='web_stream_node',
            output='screen'
        ),

    ])
