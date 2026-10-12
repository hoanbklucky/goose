# Built on top of Tiryoh's maintained ROS2-desktop-over-browser image.
# https://github.com/Tiryoh/docker-ros2-desktop-vnc
#
# NOTE: Jazzy dropped Gazebo Classic. There is no ros-jazzy-gazebo-ros-pkgs or
# ros-jazzy-gazebo-ros2-control package -- Jazzy pairs with Gazebo Harmonic via
# the ros_gz bridge instead.
#
FROM ghcr.io/tiryoh/ros2-desktop-vnc:jazzy
RUN apt-get update && apt-get install -y \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-map-server \
    ros-jazzy-nav2-lifecycle-manager \
    ros-jazzy-slam-toolbox \
    ros-jazzy-robot-localization \
    ros-jazzy-ros-gz \
    ros-jazzy-gz-ros2-control \
    ros-jazzy-xacro \
    ros-jazzy-turtlebot3 \
    ros-jazzy-turtlebot3-simulations \
    ros-jazzy-turtlebot3-msgs \
    # --- added for goosebot_0 ---
    # RTAB-Map stereo SLAM (stereo_slam.launch.py, nav2_bringup.launch.py slam:=true)
    ros-jazzy-rtabmap-ros \
    # keyboard driving (ros2 run teleop_twist_keyboard teleop_twist_keyboard)
    ros-jazzy-teleop-twist-keyboard \
    # Imu display plugin used by configwimu.rviz
    ros-jazzy-imu-tools \
    # sdf_to_map.py (world -> occupancy-grid map baker)
    python3-lxml \
    python3-pil \
    python3-numpy \
    && rm -rf /var/lib/apt/lists/*
