cmake_minimum_required(VERSION 3.8)
project(orbslam3_ros2)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
  add_compile_options(-g0 -fno-var-tracking-assignments)
endif()

# ROS 2 dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(message_filters REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

# ORB-SLAM3 dependencies
find_package(Sophus REQUIRED)
find_package(Pangolin REQUIRED)
find_package(OpenGL REQUIRED)
find_package(GLEW REQUIRED)

# Find OpenCV
find_package(OpenCV REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(Eigen3 REQUIRED)

set(ORB_SLAM3_DIR "/home/ubuntu/Dev/ORB_SLAM3")
set(PANGOLIN_LIB_DIR "/usr/local/lib/libpangolin.so")

include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(/opt/ros/humble/include/tf2_geometry_msgs)
include_directories(/usr/include/GL)

include_directories(
  ${OpenCV_INCLUDE_DIRS}
  ${cv_bridge_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIR}
  ${ORB_SLAM3_DIR}
  ${ORB_SLAM3_DIR}/include
  ${ORB_SLAM3_DIR}/include/CameraModels
  ${ORB_SLAM3_DIR}/Thirdparty/Sophus
  )

# Create three executables: mono, rgbd, stereo
add_executable(mono src/orb_slam_mono.cpp src/image_grabber_mono.cpp)
add_executable(rgbd src/orb_slam_rgbd.cpp src/image_grabber_rgbd.cpp)
add_executable(stereo src/orb_slam_stereo.cpp src/image_grabber_stereo.cpp)

link_directories(${ORB_SLAM3_DIR})

# Link the ORB_SLAM3 library and dependencies to each executable
foreach(exec mono rgbd stereo)
  target_link_libraries(${exec}
    ${OpenCV_LIBS}
    ${cv_bridge_LIBRARIES}
    ${ORB_SLAM3_DIR}/lib/libORB_SLAM3.so
    ${OPENGL_LIBRARIES}
    ${GLEW_LIBRARIES}
    ${PANGOLIN_LIB_DIR}
  )
  ament_target_dependencies(${exec}
    rclcpp
    sensor_msgs
    cv_bridge
    nav_msgs
    std_msgs
    tf2_ros
  )
endforeach()

install(TARGETS mono rgbd stereo
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/odom_to_tf_bridge.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
