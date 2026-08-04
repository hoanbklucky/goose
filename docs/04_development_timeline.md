# Goosebot Development Timeline

## Overview

This document records the development process of Goosebot from initial hardware testing to ROS 2 sensor integration.

The purpose is to document not only the final result, but also the steps, problems, solutions, and decisions made during development.

This allows future developers to reproduce the setup and understand why each step was required.

---

# Phase 1 - Initial Hardware Setup

## Goal

Create the physical robot platform and verify that the hardware can communicate with the Radxa ROCK 5C.

---

## Hardware Setup

Main computer:


Radxa ROCK 5C


Operating System:


Debian 12 KDE


Main connections:


I2C
UART
GPIO
PWM


---

# Phase 2 - GPIO and Communication Testing

## Goal

Verify that the ROCK 5C could communicate with external hardware.

---

## I2C Testing

Tools used:


i2cdetect


Purpose:

- Find connected I2C devices
- Verify communication

Detected devices included:


PCA9685 PWM Controller


The PCA9685 was used for PWM motor control.

---

## UART Testing

UART was used for GPS communication.

GPS connection:


SparkFun SAM-M8Q


Device:


/dev/ttyS4


Testing method:


cat /dev/ttyS4


Successful output:


$GNRMC
$GNGGA
$GNGSA


This confirmed that the GPS module was communicating.

---

# Phase 3 - Motor Control System

## Goal

Control the RC car motors using the ROCK 5C.

---

## Motor Hardware

Components:


TT Encoder Motors

L298N Motor Driver

PCA9685 PWM Controller


---

## Motor Testing

Tested:

- Forward movement
- Reverse movement
- Steering
- PWM control

---

## Encoder Testing

Encoder type:


Hall-effect quadrature encoder


Purpose:

Measure:

- Wheel rotation
- Distance
- Velocity

---

## Encoder Calibration

Final calibration:


Wheel Diameter:

2.6 inches

Counts Per Revolution:

1092


These values will be used for ROS odometry.

---

# Phase 4 - IMU Integration

## Goal

Connect the IMU and publish motion data through ROS 2.

---

## IMU Hardware

Sensor:


GY-521 MPU6050


Communication:


I2C


---

## ROS 2 Integration

Created IMU node:


/mpu6050_node


Published topic:


/imu/data


Message type:


sensor_msgs/msg/Imu


---

## Verified Output

The IMU successfully published:


angular_velocity

linear_acceleration


Example:


angular_velocity:
x:
y:
z:

linear_acceleration:
x:
y:
z:


---

# Phase 5 - GPS Integration

## Goal

Connect GPS data into ROS 2.

---

## Initial Attempt

The u-blox ROS driver was tested.

Problem:


Could not configure serial baud rate


Cause:

The configuration was designed for a different u-blox device setup.

---

## Solution

The NMEA driver was used instead.

Installed:


nmea_navsat_driver


ROS 2 branch:


git clone -b ros2 https://github.com/ros-drivers/nmea_navsat_driver.git


---

## Successful GPS Node

Node:


/nmea_navsat_driver


Command:


ros2 run nmea_navsat_driver nmea_serial_driver
--ros-args
-p port:=/dev/ttyS4
-p baud:=9600


---

## GPS Topics

Published:


/fix

/heading

/vel

/time_reference


---

## Outdoor Testing

GPS successfully received:

- Latitude
- Longitude
- Position updates

Indoor behavior:


latitude: .nan
longitude: .nan


Reason:

No satellite fix.

---

# Phase 6 - ROS 2 Workspace Setup

## Goal

Create a ROS 2 Humble development environment.

---

## Workspace

Created:


~/ros2_humble


Structure:


ros2_humble/

├── src

├── build

├── install

└── log


---

## Building Packages

Build command:


colcon build --symlink-install


After building:


source ~/ros2_humble/install/setup.bash


---

# Phase 7 - Robot Localization Setup

## Goal

Combine all sensors into one position estimate.

Installed:


robot_localization


---

## Current Status

Available:


robot_localization


Verified:


ros2 pkg list | grep robot_localization


---

## Planned Sensor Fusion

Inputs:


/imu/data

/fix

/odom


Output:


/odometry/filtered


---

# Current System Status

## Working

✅ ROCK 5C  
✅ ROS 2 Humble  
✅ IMU publishing  
✅ GPS publishing  
✅ NMEA driver working  
✅ GPS outdoor fix  
✅ Wheel encoder calibration  

---

# Current Development Stage

The project is currently transitioning from:


Sensor Testing


to:


Robot Localization


---

# Next Development Steps

## 1. Create Wheel Encoder ROS Node

Goal:

Publish:


/odom


---

## 2. Configure robot_localization EKF

Create:


ekf.yaml


Configure:

- IMU input
- GPS input
- Wheel odometry input

---

## 3. Setup TF Frames

Create transforms:


map

odom

base_link

imu_link

gps_link


---

## 4. Integrate Nav2

Final goal:


Localization

    |

    v

Navigation

    |

    v

Autonomous Driving


---

# Conclusion

Goosebot has progressed from a manually controlled RC platform into a ROS 2-based robotic system.

The foundation is complete:

- Hardware communication
- Sensor integration
- ROS 2 architecture
- GPS localization
- IMU data streaming

The next phase focuses on combining these systems into a fully autonomous robot.
