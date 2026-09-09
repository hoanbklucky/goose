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
    && rm -rf /var/lib/apt/lists/*