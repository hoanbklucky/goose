# Goosebot Autonomous RC Car

![ROS2](https://img.shields.io/badge/ROS2-Humble-orange)
![Platform](https://img.shields.io/badge/Platform-Radxa%20ROCK%205C-green)
![Project](https://img.shields.io/badge/Project-Autonomous%20RC%20Car-blue)

# Overview

Goosebot is an autonomous RC car development platform built around a Radxa ROCK 5C single-board computer running ROS 2 Humble.

The objective of this project is to create a low-cost autonomous vehicle capable of:

- Autonomous navigation
- Sensor fusion
- GPS localization
- IMU motion tracking
- Wheel odometry
- Obstacle detection
- SLAM and Nav2 integration

This repository documents the complete process from a fresh ROCK 5C setup to a working ROS 2 robotic system.

The goal of this documentation is to allow another person to reproduce the setup, understand the architecture, and continue development.

---

# Current System Status

## Computer

| Component | Specification |
|---|---|
| SBC | Radxa ROCK 5C |
| OS | Debian 12 KDE |
| ROS Version | ROS 2 Humble |

---

# Sensors

## MPU6050 IMU

Sensor:

- GY-521 MPU6050

Connection:

- I2C

ROS Node:


/mpu6050_node


ROS Topic:


/imu/data


Current outputs:

- Angular velocity
- Linear acceleration
- Timestamped IMU messages

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

## SparkFun SAM-M8Q GPS

Sensor:

- SparkFun SAM-M8Q u-blox GPS Module

Connection:

- UART

Device:


/dev/ttyS4


ROS Node:


/nmea_navsat_driver


ROS Topics:


/fix
/heading
/vel
/time_reference


Provides:

- Latitude
- Longitude
- Altitude
- Velocity

GPS works outdoors with satellite visibility.

Indoor operation may result in:


latitude: .nan
longitude: .nan
status: -1


This is expected behavior when no GPS fix is available.

---

# Wheel Encoder System

Hardware:

- TT Encoder Motors
- Hall-effect quadrature encoders

Current calibration:


Wheel diameter:
2.6 inches

Encoder counts:
1092 counts/revolution


The wheel encoder system will provide odometry information for ROS localization.

Target topic:


/odom


---

# ROS 2 Architecture

Current sensor flow:

            SAM-M8Q GPS
                 |
                 |
                 v
        nmea_navsat_driver
                 |
                 |
               /fix

MPU6050 IMU
|
|
v
/imu/data

Wheel Encoder
|
|
v
/odom

    All Sensors
         |
         |
         v

 robot_localization EKF

         |
         |
         v

/odometry/filtered

         |
         |
         v

    Nav2 / SLAM

---

# Repository Structure


Goosebot/

├── README.md
│
├── docs/
│ ├── Project documentation
│ ├── ROS2 architecture
│ └── Sensor fusion explanation
│
├── ros2/
│ ├── ROS2 installation
│ ├── Workspace setup
│ ├── Package building
│ └── robot_localization
│
├── sensors/
│ ├── MPU6050 IMU
│ ├── SAM-M8Q GPS
│ ├── Wheel Encoder
│ └── Ultrasonic Sensor
│
├── hardware/
│ ├── ROCK 5C setup
│ ├── Motor system
│ └── Wiring
│
├── config/
│ ├── GPS configuration
│ └── EKF configuration
│
└── code/
└── Python and ROS nodes


---

# Development Progress

## Phase 1 - Hardware Setup

Completed:

- ROCK 5C installation
- GPIO testing
- I2C testing
- UART testing
- Motor hardware testing

---

## Phase 2 - Sensor Integration

Completed:

- MPU6050 IMU connected
- SAM-M8Q GPS connected
- GPS NMEA communication verified
- Wheel encoder tested

---

## Phase 3 - ROS 2 Integration

Completed:

ROS 2 workspace:


~/ros2_humble


Working nodes:


/mpu6050_node
/nmea_navsat_driver


Working topics:


/imu/data
/fix
/heading
/vel
/time_reference


---

## Phase 4 - Localization

Current progress:

- robot_localization installed
- IMU publishing
- GPS publishing
- Wheel encoder calibration complete

Next steps:

- Create EKF configuration
- Fuse IMU + GPS
- Add wheel odometry
- Publish filtered position

---

# Hardware List

## Main Computer

- Radxa ROCK 5C

## Sensors

- SparkFun SAM-M8Q GPS
- GY-521 MPU6050 IMU
- Wheel encoder motors
- Ultrasonic sensor

## Motor System

- TT encoder motors
- L298N motor driver
- PCA9685 PWM controller

---

# Troubleshooting Notes

## GPS

Problem:


latitude: .nan
longitude: .nan


Cause:

No satellite fix.

Solution:

Move outdoors with clear sky visibility.

---

## ROS Package Compatibility

Some ROS repositories contain ROS1-only code.

Example:

The original nmea_navsat_driver repository used:


catkin


which is ROS1.

The ROS2 branch was required:


git clone -b ros2 https://github.com/ros-drivers/nmea_navsat_driver.git


---

# Future Goals

## Localization

- EKF sensor fusion
- GPS + IMU + wheel odometry
- Stable robot position estimate

## Navigation

- ROS2 Nav2
- SLAM
- Autonomous waypoint navigation

## Autonomy

- Lane following
- Obstacle avoidance
- Full autonomous driving

---

# Project Philosophy

Goosebot is designed as an educational autonomous robotics platform.

Every hardware connection, software installation, configuration file, and troubleshooting step is documented so the entire system can be rebuilt from the beginning.

