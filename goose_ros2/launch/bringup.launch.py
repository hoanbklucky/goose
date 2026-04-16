# bringup.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

        Node(
            package='goose_ros2',
            executable='camera_node',
            parameters=['config/params.yaml']
        ),

        Node(
            package='goose_ros2',
            executable='lane_node'
        ),

        Node(
            package='goose_ros2',
            executable='control_node',
            parameters=['config/params.yaml']
        ),

        Node(
            package='goose_ros2',
            executable='motor_node'
        ),
    ])