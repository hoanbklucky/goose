cmake_minimum_required(VERSION 3.8)
project(goosebot_0)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf launch config maps
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/ground_truth_map_odom_bridge.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
