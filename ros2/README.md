# Goosebot ROS2 Integration

## Overview

This folder contains the ROS2 implementation for Goosebot.

The purpose of this section is to document the transition from individual Python sensor tests into a complete ROS2 robotic software architecture.

ROS2 allows Goosebot's sensors, controllers, localization, and navigation systems to communicate through standardized topics and messages.

---

# Current ROS2 Milestone

Current system status:

✅ ROS2 Humble workspace created  
✅ ROS2 packages installed  
✅ MPU6050 IMU publishing data  
✅ SparkFun SAM-M8Q GPS publishing data  
✅ NMEA GPS driver integrated  
✅ robot_localization installed  
✅ Sensor topics verified  

Current active ROS2 nodes:

```
/mpu6050_node
/nmea_navsat_driver
```

Current active ROS2 topics:

```
/imu/data
/fix
/heading
/vel
/time_reference
```

---

# ROS2 Architecture

Goosebot follows the standard robotics pipeline:

```
Sensors
   |
   |
   v

ROS2 Drivers

   |
   |
   v

ROS2 Topics

   |
   |
   v

robot_localization (EKF)

   |
   |
   v

Filtered Odometry

   |
   |
   v

Navigation Stack (Nav2)

   |
   |
   v

Autonomous Robot
```

---

# ROS2 Workspace

The main ROS2 workspace is:

```
~/ros2_humble
```

Structure:

```
ros2_humble/

├── src/
│
│   ├── nmea_navsat_driver/
│   │
│   ├── robot_localization/
│   │
│   └── goosebot packages (future)
│
├── build/
│
├── install/
│
└── log/
```

---

# ROS2 Packages

## nmea_navsat_driver

Purpose:

Reads GPS NMEA messages and converts them into ROS2 GPS messages.

Hardware:

```
SparkFun u-blox SAM-M8Q GPS
```

Connection:

```
GPS TX → ROCK 5C RX
GPS RX → ROCK 5C TX
```

UART:

```
/dev/ttyS4
```

Baud rate:

```
9600
```

Published topics:

```
/fix
/vel
/heading
/time_reference
```

---

# MPU6050 IMU

Purpose:

Provides acceleration and angular velocity data.

Hardware:

```
GY-521 MPU6050
```

Communication:

```
I2C
```

ROS2 node:

```
/mpu6050_node
```

Published topic:

```
/imu/data
```

Message type:

```
sensor_msgs/msg/Imu
```

---

# robot_localization

Purpose:

Combines multiple sensors using an Extended Kalman Filter (EKF).

The EKF will combine:

```
GPS
+
IMU
+
Wheel Encoder
```

to estimate the robot's position and movement.

Future output:

```
/odometry/filtered
```

This output will be used by:

```
Nav2
```

for autonomous navigation.

---

# Building ROS2 Workspace

Navigate to workspace:

```bash
cd ~/ros2_humble
```

Build packages:

```bash
colcon build --symlink-install
```

Load workspace:

```bash
source ~/ros2_humble/install/setup.bash
```

---

# Useful ROS2 Commands

Check ROS version:

```bash
echo $ROS_DISTRO
```

Expected:

```
humble
```

---

List installed packages:

```bash
ros2 pkg list
```

---

List active nodes:

```bash
ros2 node list
```

Example:

```
/mpu6050_node
/nmea_navsat_driver
```

---

List topics:

```bash
ros2 topic list
```

---

View IMU data:

```bash
ros2 topic echo /imu/data --once
```

---

View GPS data:

```bash
ros2 topic echo /fix --once
```

---

# Development Roadmap

## Completed

[x] Create ROS2 Humble workspace

[x] Build ROS2 environment

[x] Install required packages

[x] Connect MPU6050

[x] Publish IMU messages

[x] Connect GPS UART

[x] Publish GPS messages

[x] Verify ROS2 topics


---

## Current Work

[ ] Create Goosebot ROS2 package

[ ] Add wheel encoder node

[ ] Configure robot_localization EKF

[ ] Publish filtered odometry


---

## Future Goals

[ ] Integrate Nav2

[ ] Add SLAM

[ ] Add autonomous waypoint navigation

[ ] Full autonomous driving system


---

# Related Documentation

Detailed documentation:

```
../docs/
```

Sensor documentation:

```
../docs/03_sensors/
```

Localization documentation:

```
../docs/04_localization/
```

Troubleshooting:

```
../docs/06_troubleshooting/
```

---

# Planned ROS2 Folder Structure

Future structure:

```
ros2/

├── README.md
│
├── packages/
│
├── launch/
│
├── config/
│
├── nodes/
│
└── scripts/
```

These folders will contain Goosebot's custom ROS2 implementation.
