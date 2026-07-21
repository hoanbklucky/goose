cmake_minimum_required(VERSION 3.8)
project(goosebot_0)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
