# Goosebot ROS2 Packages

## Overview

This folder documents the ROS2 packages used in Goosebot.

ROS2 packages contain the software components that allow hardware drivers, sensors, localization, and robot behaviors to communicate using ROS2 topics and messages.

The goal is to eventually organize Goosebot into its own custom ROS2 package while using existing ROS2 packages for sensor drivers and localization.

---

# Current ROS2 Packages

Current workspace:

```
~/ros2_humble/src
```

Current packages:

```
src/

├── nmea_navsat_driver/
│
├── robot_localization/
│
└── goosebot/
    (future custom package)
```

---

# Package 1: nmea_navsat_driver

## Purpose

The `nmea_navsat_driver` package converts GPS NMEA serial messages into ROS2 sensor messages.

It allows GPS hardware to communicate with the ROS2 ecosystem.

---

## Hardware

GPS Module:

```
SparkFun u-blox SAM-M8Q
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

---

## Input

Raw GPS serial data:

Example:

```
$GNRMC
$GNGGA
$GNGSA
$GPGSV
```

---

## Output Topics

The driver publishes:

```
/fix
```

GPS position information.

Message type:

```
sensor_msgs/msg/NavSatFix
```

---

```
/vel
```

GPS velocity information.

---

```
/heading
```

GPS heading information.

---

```
/time_reference
```

GPS time synchronization.

---

## Running GPS Driver

Source ROS2:

```bash
source ~/ros2_humble/install/setup.bash
```

Run:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

---

## Testing GPS

Check node:

```bash
ros2 node list
```

Expected:

```
/nmea_navsat_driver
```

Check topics:

```bash
ros2 topic list
```

Expected:

```
/fix
/vel
/heading
/time_reference
```

Check GPS:

```bash
ros2 topic echo /fix --once
```

Outdoor GPS fix example:

```
latitude: xx.xxxxxx
longitude: xx.xxxxxx
altitude: xx.x
```

Indoor:

```
latitude: .nan
longitude: .nan
```

This is normal when GPS has no satellite lock.

---

# Package 2: robot_localization

## Purpose

`robot_localization` provides sensor fusion using an Extended Kalman Filter (EKF).

It combines multiple sensor sources into one estimated robot position.

---

## Sensor Inputs

Future Goosebot configuration:

```
GPS
 |
 |
 v

/ fix

+
 
IMU
 |
 |
 v

/imu/data

+

Wheel Encoder
 |
 |
 v

/odometry
```

---

## EKF Output

The filtered result:

```
/odometry/filtered
```

contains the robot's estimated:

- Position
- Orientation
- Velocity

---

## Why Use EKF?

Individual sensors have weaknesses:

GPS:

```
+ Absolute position
- Slow updates
- Indoor unavailable
- Less accurate short term
```

IMU:

```
+ Fast motion data
+ Rotation information
- Drifts over time
```

Wheel Encoder:

```
+ Accurate short distance movement
- Accumulates error
```

EKF combines them to create a better estimate.

---

# Package 3: goosebot (Future)

## Purpose

This will become Goosebot's custom ROS2 package.

It will contain:

```
goosebot/

├── nodes/
│
├── launch/
│
├── config/
│
├── msg/
│
└── scripts/
```

---

# Planned Goosebot Nodes

## IMU Node

Purpose:

Publish MPU6050 data.

Current topic:

```
/imu/data
```

---

## GPS Node

Purpose:

Publish GPS position.

Current topic:

```
/fix
```

---

## Encoder Node

Purpose:

Convert wheel encoder pulses into ROS2 odometry.

Future topic:

```
/wheel/odometry
```

---

## Motor Controller Node

Purpose:

Receive movement commands and control motors.

Future topic:

```
/cmd_vel
```

---

# Creating a ROS2 Package

Example:

Navigate:

```bash
cd ~/ros2_humble/src
```

Create package:

```bash
ros2 pkg create goosebot \
--build-type ament_python
```

Build:

```bash
cd ~/ros2_humble
colcon build --symlink-install
```

Source:

```bash
source install/setup.bash
```

---

# Package Development Workflow

Every time code changes:

1. Edit package files

2. Build:

```bash
colcon build --symlink-install
```

3. Source:

```bash
source ~/ros2_humble/install/setup.bash
```

4. Test:

```bash
ros2 node list
```

or

```bash
ros2 topic list
```

---

# Current Status

Completed:

[x] nmea_navsat_driver installed

[x] GPS communication verified

[x] GPS ROS2 topic created

[x] robot_localization installed


In Progress:

[ ] Create goosebot package

[ ] Add encoder ROS2 node

[ ] Configure EKF parameters

[ ] Connect localization system
