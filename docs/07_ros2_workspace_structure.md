# ROS2 Workspace Structure

This document explains the organization of the Goosebot ROS2 Humble workspace.

The purpose is to show:

- Where ROS2 packages are stored
- How packages are built
- Where configurations go
- How nodes communicate

---

# 1. ROS2 Workspace Overview

Goosebot uses a standard ROS2 workspace:

```
ros2_humble/

├── build/
├── install/
├── log/
└── src/
```

---

# 2. Workspace Folders

## src/

Contains all ROS2 packages.

Example:

```
ros2_humble/src/
```

Packages are cloned or created here.

Example:

```
src/
│
├── ublox/
│
├── nmea_navsat_driver/
│
├── robot_localization/
│
└── goosebot/
```

---

## build/

Created automatically by colcon.

Contains:

- Temporary compilation files
- CMake build information

Do not edit manually.

---

## install/

Contains:

- Built ROS2 packages
- Environment setup files

After building:

```bash
source install/setup.bash
```

allows ROS2 to find packages.

---

## log/

Contains:

- Build logs
- Error messages

Useful for debugging.

---

# 3. Creating a ROS2 Workspace

Create workspace:

```bash
mkdir -p ~/ros2_humble/src
```

Enter workspace:

```bash
cd ~/ros2_humble
```

---

# 4. Building the Workspace

Build all packages:

```bash
colcon build
```

Recommended:

```bash
colcon build --symlink-install
```

Why:

```
--symlink-install
```

allows Python files to update without reinstalling.

---

# 5. Sourcing ROS2

After every build:

```bash
source ~/ros2_humble/install/setup.bash
```

Without sourcing:

ROS2 cannot find newly built packages.

---

# 6. Checking Installed Packages

List packages:

```bash
ros2 pkg list
```

Example:

```
robot_localization
nmea_navsat_driver
mpu6050_node
```

---

# 7. Goosebot ROS2 Package Layout

Final planned structure:

```
ros2_humble/

└── src/

    ├── goosebot/
    │
    │   ├── goosebot_description/
    │   │
    │   ├── goosebot_bringup/
    │   │
    │   ├── goosebot_navigation/
    │   │
    │   └── goosebot_sensors/
    │
    ├── nmea_navsat_driver/
    │
    ├── robot_localization/
    │
    └── mpu6050_driver/
```

---

# 8. Goosebot Packages Explained

## goosebot_description

Contains robot model.

Includes:

- URDF
- Mesh files
- Robot dimensions

Used by:

- RViz
- Gazebo
- TF system

---

## goosebot_bringup

Starts the robot.

Contains:

- Launch files
- Startup configuration

Example:

```
bringup.launch.py
```

Starts:

```
IMU node

GPS node

Encoder node

EKF node
```

---

## goosebot_sensors

Contains sensor drivers.

Examples:

```
imu_node.py

gps_node.py

encoder_node.py
```

Publishes:

```
/imu/data

/fix

/odom
```

---

## goosebot_navigation

Contains:

- Nav2 configuration
- Path planning
- Autonomous movement

---

# 9. ROS2 Nodes

A node is a running program.

Example:

```
mpu6050_node
```

publishes:

```
/imu/data
```

GPS node:

```
nmea_navsat_driver
```

publishes:

```
/fix
```

---

# 10. ROS2 Topics

Topics allow nodes to communicate.

Example:

```
MPU6050 Node

       |
       |
       v

 /imu/data

       |
       |
       v

robot_localization

       |
       |
       v

/odometry/filtered
```

---

# 11. ROS2 Launch Files

Launch files start multiple nodes together.

Example:

Instead of:

```bash
ros2 run mpu6050 mpu6050_node
```

and:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver
```

use:

```bash
ros2 launch goosebot_bringup robot.launch.py
```

---

# 12. Configuration Files

Configuration files control nodes.

Example:

```
config/

├── ekf.yaml
├── gps.yaml
└── imu.yaml
```

They define:

- Topics
- Frames
- Sensor settings
- Update rates

---

# 13. Current Goosebot ROS2 Status

Completed:

```
ROS2 Humble installed

Workspace created

GPS driver installed

IMU node running

robot_localization installed
```

Current topics:

```
/fix

/imu/data
```

---

# 14. Next Development Structure

The next packages to create:

```
goosebot/

├── goosebot_sensors

    ├── gps publisher

    ├── imu publisher

    └── encoder publisher


├── goosebot_bringup

    └── launch files


└── goosebot_navigation

    └── Nav2 configs
```

---

# Goal

The finished ROS2 system should allow:

```
Sensors
   |
   |
ROS2 Topics
   |
   |
robot_localization
   |
   |
Nav2
   |
   |
Autonomous Driving
```

This structure keeps Goosebot modular, repeatable, and easy to debug.
