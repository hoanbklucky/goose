# Goosebot ROS2 Launch System

## Overview

This folder contains ROS2 launch files for starting Goosebot's software system.

ROS2 launch files allow multiple nodes to be started together using a single command.

Instead of manually running:

- IMU node
- GPS driver
- Localization
- Robot controllers

each time, a launch file can start the entire robot system automatically.

---

# Planned Launch Structure

Future structure:

```
launch/

├── sensors.launch.py
│
├── localization.launch.py
│
├── robot.launch.py
│
└── autonomous.launch.py
```

---

# Current ROS2 Startup Process

Currently, Goosebot nodes are started manually.

Example:

## Start ROS2 Environment

```bash
source ~/ros2_humble/install/setup.bash
```

---

## Start IMU Node

Example:

```bash
ros2 run mpu6050_node mpu6050_node
```

Current output:

```
/imu/data
```

---

## Start GPS Driver

Example:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

Current outputs:

```
/fix
/heading
/vel
/time_reference
```

---

# Future Sensor Launch File

Planned file:

```
sensors.launch.py
```

Purpose:

Start all sensor drivers.

Example:

```
sensors.launch.py

        |
        |
        +---- MPU6050 IMU
        |
        |
        +---- GPS Driver
        |
        |
        +---- Encoder Node
```

---

# Future Localization Launch File

Planned file:

```
localization.launch.py
```

Purpose:

Start robot localization.

Includes:

```
robot_localization EKF
```

Input topics:

```
/imu/data
/fix
/wheel/odometry
```

Output:

```
/odometry/filtered
```

---

# Full Robot Launch

Planned file:

```
robot.launch.py
```

Purpose:

Start the complete Goosebot system.

Future startup:

```
robot.launch.py

        |
        |
        +---- Sensors
        |
        +---- Motor Controller
        |
        +---- Encoder
        |
        +---- EKF
        |
        +---- Nav2
        |
        +---- SLAM
```

---

# Launch Workflow

After creating or editing a launch file:

Build:

```bash
cd ~/ros2_humble

colcon build --symlink-install
```

Source:

```bash
source install/setup.bash
```

Run:

```bash
ros2 launch <package_name> <launch_file>
```

Example:

```bash
ros2 launch goosebot robot.launch.py
```

---

# Why Use Launch Files?

Without launch files:

```
Terminal 1:
start IMU

Terminal 2:
start GPS

Terminal 3:
start EKF

Terminal 4:
start motors
```

With launch files:

```
One command:

ros2 launch goosebot robot.launch.py
```

starts the entire robot.

---

# Current Status

Completed:

[x] ROS2 workspace created

[x] Sensor nodes verified

[x] GPS driver working

[x] IMU node working


In Progress:

[ ] Create Goosebot ROS2 package

[ ] Create first launch file

[ ] Add sensor startup

[ ] Add EKF startup

[ ] Add full robot launch

---

# Related Documentation

ROS2 packages:

```
../packages/
```

Configuration:

```
../config/
```

Nodes:

```
../nodes/
```

Scripts:

```
../scripts/
```
