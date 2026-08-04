# Goosebot ROS2 Nodes

## Overview

This folder documents the ROS2 nodes used by Goosebot.

In ROS2, a node is an individual software process that performs a specific task.

Examples:

- Reading sensors
- Controlling motors
- Processing data
- Publishing robot state
- Running localization algorithms

Each node communicates through ROS2 topics.

---

# ROS2 Node Architecture

Goosebot's software architecture:

```
                 Hardware

                    |
                    |
                    v


        +-----------------------+
        |     ROS2 Nodes        |
        +-----------------------+

                    |

                    v


              ROS2 Topics

                    |

                    v


          Data Processing Nodes

                    |

                    v


             Robot Behavior
```

---

# Current Nodes

Current working nodes:

```
/mpu6050_node

/nmea_navsat_driver
```

---

# Node 1: MPU6050 IMU Node

## Purpose

The MPU6050 node reads acceleration and gyroscope measurements from the GY-521 MPU6050 sensor.

It publishes standard ROS2 IMU messages.

---

## Hardware

Sensor:

```
GY-521 MPU6050
```

Communication:

```
I2C
```

ROCK 5C connection:

```
SDA → GPIO pins 27

SCL → GPIO pins 28

VCC → 3.3V

GND → Ground
```

---

## ROS2 Node

Node name:

```
/mpu6050_node
```

---

## Published Topic

```
/imu/data
```

Message:

```
sensor_msgs/msg/Imu
```

---

## Data Published

Orientation:

```
x
y
z
w
```

Angular velocity:

```
rad/s
```

Linear acceleration:

```
m/s²
```

Example:

```bash
ros2 topic echo /imu/data --once
```

Output:

```
angular_velocity:
  x:
  y:
  z:

linear_acceleration:
  x:
  y:
  z:
```

---

# Node 2: GPS NMEA Driver

## Purpose

The GPS node converts raw GPS serial messages into ROS2 messages.

---

## Hardware

GPS:

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

Baud:

```
9600
```

---

## ROS2 Node

Node name:

```
/nmea_navsat_driver
```

---

## Published Topics

GPS position:

```
/fix
```

Message:

```
sensor_msgs/msg/NavSatFix
```

---

Velocity:

```
/vel
```

---

Heading:

```
/heading
```

---

Time:

```
/time_reference
```

---

## GPS Testing

Check node:

```bash
ros2 node list
```

Expected:

```
/nmea_navsat_driver
```

Check GPS:

```bash
ros2 topic echo /fix --once
```

Outdoor:

```
latitude: valid value
longitude: valid value
```

Indoor:

```
latitude: .nan
longitude: .nan
```

This means no satellite fix.

---

# Future Node: Wheel Encoder Node

## Purpose

The encoder node will convert wheel rotation into robot movement.

---

## Hardware

Motor:

```
TT Encoder Motor
```

Encoder:

```
Hall effect quadrature encoder
```

---

## Responsibilities

The node will:

- Count encoder pulses
- Calculate wheel speed
- Calculate distance traveled
- Publish odometry

---

## Planned Topic

```
/wheel/odometry
```

Message:

```
nav_msgs/msg/Odometry
```

---

# Future Node: Motor Controller Node

## Purpose

Controls Goosebot movement.

---

## Hardware

Motor Driver:

```
L298N
```

PWM Controller:

```
PCA9685
```

---

## Planned Input

```
/cmd_vel
```

Message:

```
geometry_msgs/msg/Twist
```

Example:

```
linear.x = forward speed

angular.z = turning speed
```

---

# Future Node: Goosebot Main Node

## Purpose

Custom Goosebot logic.

Responsibilities:

- Robot state management
- Sensor coordination
- Autonomous behavior
- Communication with navigation

---

# Node Development Workflow

When creating a new node:

## 1. Create package

```bash
cd ~/ros2_humble/src

ros2 pkg create goosebot \
--build-type ament_python
```

---

## 2. Add node script

Example:

```
goosebot/
└── goosebot/
    └── imu_processor.py
```

---

## 3. Build

```bash
cd ~/ros2_humble

colcon build --symlink-install
```

---

## 4. Source

```bash
source install/setup.bash
```

---

## 5. Test

```bash
ros2 node list
```

---

# Current Progress

Completed:

[x] MPU6050 ROS2 node working

[x] GPS ROS2 node working

[x] Sensor topics verified


In Progress:

[ ] Encoder ROS2 node

[ ] Motor controller node

[ ] Goosebot custom package

[ ] Launch integration

[ ] EKF integration

---

# Related Documentation

Packages:

```
../packages/
```

Configuration:

```
../config/
```

Launch files:

```
../launch/
```

Scripts:

```
../scripts/
```
