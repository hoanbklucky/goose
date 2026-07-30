#!/bin/bash
source /opt/ros/humble/setup.bash

CAM_DEVICE="/dev/v4l/by-id/usb-icSpring_icspring_camera_2409181858122-video-index0"

if [ ! -e "$CAM_DEVICE" ]; then
    echo "ERROR: ICSpring camera not found at $CAM_DEVICE"
    echo "Is it plugged in? Check with: ls -la /dev/v4l/by-id/"
    exit 1
fi

echo "Using camera device: $CAM_DEVICE"

ros2 run v4l2_camera v4l2_camera_node --ros-args \
  --remap image_raw:=/camera/rgb/image_color \
  -p video_device:="$CAM_DEVICE" \
  -p image_size:="[640,480]"
