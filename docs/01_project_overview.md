# Goosebot Project Overview

## Introduction

Goosebot is a low-cost autonomous RC car research platform designed to explore robotics, embedded systems, ROS 2, and autonomous navigation.

The project uses a Radxa ROCK 5C as the main computer and integrates multiple sensors to create a complete robotic perception and localization system.

The purpose of this repository is to document the complete development process from initial hardware setup to autonomous navigation.

This documentation is written so that another person can reproduce the setup, understand each subsystem, and continue development.

---

# Project Goals

The main objective of Goosebot is to create an autonomous mobile robot capable of understanding its environment and navigating independently.

The development goals are divided into several stages.

---

# Phase 1 - Hardware Platform

## Objective

Create a working robotic vehicle platform with computer control.

## Completed

Hardware integrated:

- Radxa ROCK 5C
- DC encoder motors
- Motor driver
- PWM controller
- IMU
- GPS module

Tasks completed:

- ROCK 5C setup
- GPIO testing
- I2C communication testing
- UART communication testing
- Motor control testing

---

# Phase 2 - Sensor Integration

## Objective

Connect sensors to the ROCK 5C and verify reliable data output.

## Sensors

## IMU

Hardware:


GY-521 MPU6050


Purpose:

- Measure acceleration
- Measure angular velocity
- Estimate robot movement

Communication:


I2C


ROS output:


/imu/data


---

## GPS

Hardware:


SparkFun SAM-M8Q u-blox GPS


Purpose:

- Outdoor positioning
- Latitude and longitude tracking
- Velocity information

Communication:


UART


Device:


/dev/ttyS4


ROS output:


/fix
/heading
/vel
/time_reference


---

## Wheel Encoder

Hardware:


TT Encoder Motors


Purpose:

- Measure wheel rotation
- Calculate distance traveled
- Provide wheel odometry

Calibration:


Wheel Diameter:
2.6 inches

Encoder Resolution:
1092 counts/revolution


Future ROS output:


/odom


---

# Phase 3 - ROS 2 Integration

## Objective

Convert hardware sensor data into ROS 2 messages.

The ROS 2 architecture allows each sensor to operate independently while sharing information through topics.

---

# ROS 2 Concept

ROS 2 uses three main communication concepts:

## Nodes

A node is a program that performs a specific task.

Examples:


/mpu6050_node


Reads IMU data.


/nmea_navsat_driver


Reads GPS data.

---

## Topics

Topics are communication channels where nodes publish and receive information.

Example:

IMU node publishes:


/imu/data


GPS node publishes:


/fix


---

## Messages

Messages define the format of the data being transmitted.

Example:

IMU messages contain:

- Timestamp
- Orientation
- Angular velocity
- Linear acceleration

GPS messages contain:

- Latitude
- Longitude
- Altitude
- Position accuracy

---

# Current ROS 2 System

Current running nodes:


/mpu6050_node

/nmea_navsat_driver


Current topics:


/imu/data

/fix

/heading

/vel

/time_reference


---

# Phase 4 - Localization

## Objective

Combine multiple sensors into one reliable position estimate.

Individual sensors have limitations:

| Sensor | Strength | Weakness |
|---|---|---|
| GPS | Absolute position | Slow, requires satellites |
| IMU | Fast movement data | Drifts over time |
| Wheel Encoder | Distance traveled | Accumulates error |

Because each sensor has different errors, they are combined using sensor fusion.

---

# Robot Localization

The package used for sensor fusion is:


robot_localization


It uses an Extended Kalman Filter (EKF).

The EKF combines:


GPS
+
IMU
+
Wheel Odometry

    |

    v

Filtered Position Estimate


Output:


/odometry/filtered


---

# Future Navigation Architecture

Final intended architecture:

         GPS
          |
          |
          v

    nmea_navsat_driver

          |
          |
         /fix


         IMU
          |
          |
          v

      /imu/data


   Wheel Encoder
          |
          |
          v

         /odom



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


      ROS 2 Nav2


          |
          |
          v


   Autonomous Driving

---

# Future Development Roadmap

## Localization

Complete:

- GPS integration
- IMU integration

Remaining:

- Wheel odometry publishing
- EKF configuration
- Coordinate frame setup

---

## Navigation

Planned:

- ROS 2 Nav2
- SLAM
- Path planning
- Obstacle avoidance

---

## Autonomous Features

Future capabilities:

- Lane following
- Object detection
- GPS waypoint navigation
- Autonomous driving

---

# Design Philosophy

Goosebot is designed as a learning and research platform.

The goal is not only to build an autonomous vehicle, but to document every step:

- Hardware decisions
- Software installation
- Configuration files
- Debugging process
- ROS 2 architecture

This repository should allow another person to recreate the project from the beginning and understand why each step is required.
