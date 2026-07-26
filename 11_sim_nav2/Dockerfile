# Built on top of Tiryoh's maintained ROS2-desktop-over-browser image.
# This gives every teammate identical Ubuntu 22.04 + ROS2 Humble desktop,
# accessed via a browser tab (noVNC) -- no X11/XQuartz/VcXsrv host config needed.
# https://github.com/Tiryoh/docker-ros2-desktop-vnc
FROM ghcr.io/tiryoh/ros2-desktop-vnc:humble

# Add the nav stack packages on top of the base ros-humble-desktop install
RUN apt-get update && apt-get install -y \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-slam-toolbox \
    ros-humble-robot-localization \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-gazebo-ros2-control \
    ros-humble-xacro \
	ros-humble-turtlebot3 \
    ros-humble-turtlebot3-simulations \
    ros-humble-turtlebot3-msgs \
    && rm -rf /var/lib/apt/lists/*
	