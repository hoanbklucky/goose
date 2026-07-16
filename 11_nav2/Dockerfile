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


# --- ORB-SLAM3 + orbslam3_ros2 stack ---
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    ros-humble-vision-opencv \
    ros-humble-message-filters \
    ros-humble-octomap-* \
    libeigen3-dev \
    libgl1-mesa-dev libglew-dev \
    && rm -rf /var/lib/apt/lists/*

# Pangolin (pinned to v0.6, required by ORB-SLAM3)
RUN git clone https://github.com/stevenlovegrove/Pangolin /opt/Pangolin \
    && cd /opt/Pangolin && git checkout v0.6 \
    && sed -i '1i #include <limits>' include/pangolin/gl/colour.h \
    && mkdir build && cd build && cmake .. && make -j2 && make install

# ORB-SLAM3 (c++14_comp branch, required for this wrapper)
RUN git clone -b c++14_comp https://github.com/UZ-SLAMLab/ORB_SLAM3.git /opt/ORB_SLAM3 \
    && cd /opt/ORB_SLAM3 && chmod +x build.sh && ./build.sh
RUN cd /opt/ORB_SLAM3/Thirdparty/Sophus/build && make install
RUN mkdir -p /home/ubuntu && echo 'export LD_LIBRARY_PATH=/opt/ORB_SLAM3/lib:/usr/local/lib:$LD_LIBRARY_PATH' >> /home/ubuntu/.bashrc
