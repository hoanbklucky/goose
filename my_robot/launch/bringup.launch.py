# bringup.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package='my_robot', executable='camera_node'),
        Node(package='my_robot', executable='lane_node'),
        Node(package='my_robot', executable='control_node'),
        Node(package='my_robot', executable='motor_node'),
    ])