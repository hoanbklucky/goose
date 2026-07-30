#!/bin/bash
source /opt/ros/humble/setup.bash
source ~/colcon_ws/install/setup.bash

trap 'kill $(jobs -p)' EXIT

# Start camera
~/start_camera.sh &
sleep 2

# Start IMU driver
ros2 launch mpu6050driver mpu6050driver_launch.py &
sleep 2

# Start SLAM + octomap
ros2 launch orbslam3_ros2 orbslam3_ros2.launch.py \
  camera_type:=mono \
  visualize:=false \
  start_octomap:=true 2>&1 | tee ~/slam_logs/run_$(date +%Y%m%d_%H%M%S).log
