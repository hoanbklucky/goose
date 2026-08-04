# Goosebot Autonomous RC Car

## Overview

Goosebot is an autonomous RC car project built around a Radxa ROCK 5C running ROS2 Humble.

The goal of this project is to develop a low-cost autonomous robot capable of:

- Autonomous navigation
- Sensor fusion
- GPS navigation
- Indoor localization
- SLAM mapping
- Obstacle avoidance


# Hardware Platform

## Main Computer

| Component | Details |
|---|---|
| SBC | Radxa ROCK 5C |
| OS | Debian 12 KDE |
| Robotics Framework | ROS2 Humble |


# Sensors

## MPU6050 IMU

Sensor:

```
GY-521 MPU6050
```

Status:

```
WORKING
```

ROS2 Topic:

```
/imu/data
```

Provides:

- Linear acceleration
- Angular velocity
- Orientation data (future sensor fusion)


---

## SparkFun SAM-M8Q GPS

Connection:

```
SAM-M8Q TX → ROCK 5C RX
SAM-M8Q RX → ROCK 5C TX
```

UART:

```
/dev/ttyS4
```

Status:

```
WORKING OUTDOORS
```

ROS2 Topic:

```
/fix
```

Driver:

```
nmea_navsat_driver
```


---

## Wheel Encoder

Motor:

```
TT Encoder Motor
1:48 Gearbox
```

Calibration:

```
Wheel Diameter:
2.6 inches

Counts Per Revolution:
1092
```

Purpose:

- Wheel odometry
- Distance calculation
- Localization


---

# Motor System

Motor Driver:

```
L298N
```

PWM Controller:

```
PCA9685
```

Status:

```
Manual motor control working
```


---

# ROS2 Current Status

## Running Nodes

```
/mpu6050_node
/nmea_navsat_driver
```


## Current Topics

```
/imu/data
/fix
/heading
/vel
```


---

# Current Sensor Architecture

```
                GPS
                 |
                 |
                 v

              /fix


IMU
 |
 |
 v

/imu/data


Encoder
 |
 |
 v

Future wheel odometry
```


---

# Completed Features

✅ ROCK 5C setup

✅ ROS2 Humble installed

✅ Motor control

✅ Encoder testing

✅ MPU6050 ROS2 publisher

✅ SAM-M8Q UART communication

✅ GPS NMEA parsing

✅ Outdoor GPS fix


---

# Currently Developing

⬜ Wheel encoder ROS2 publisher

⬜ robot_localization EKF

⬜ GPS + IMU fusion

⬜ Encoder + IMU + GPS fusion

⬜ Nav2 autonomous navigation

⬜ SLAM


---

# Future Architecture

```
                GPS
                 |
                 |
IMU --------> EKF --------> /odometry/filtered
                 |
                 |
Encoder ---------|

                 |
                 v

                Nav2

                 |
                 v

          Autonomous Driving
```


---

# Repository Structure

```
goose/

├── README.md

├── docs/
│
│── hardware/
│
│── ros2/
│
│── sensors/
│   ├── imu/
│   ├── gps/
│   └── ultrasonic/
│
│── motors/
│
│── troubleshooting/


├── src/
│
│── motor_control/
│
│── sensors/
│
│── calibration/


├── config/

├── launch/

├── tests/

└── requirements.txt
```


---

# Development Log

## August 4, 2026

Checkpoint:

- ROS2 Humble working
- MPU6050 publishing
- SAM-M8Q GPS working
- GPS topic `/fix` confirmed
- IMU topic `/imu/data` confirmed


Next:

1. Create wheel odometry
2. Configure robot_localization
3. Fuse GPS + IMU + Encoder
4. Begin Nav2


---

# Goosebot Project

Mechanical Engineering Robotics Project
