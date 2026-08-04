# ROS 2 Architecture

## Overview

ROS 2 (Robot Operating System 2) is the communication framework used by Goosebot.

Instead of having one large program controlling the entire robot, ROS 2 separates the system into smaller independent programs called **nodes**.

Each node performs a specific task and communicates with other nodes through topics, services, and messages.

This modular design makes it easier to test, replace, and expand robot systems.

---

# Goosebot ROS 2 Architecture

Current architecture:

             Sensors

    +----------------------+
    |                      |
    |                      |
    v                      v


 MPU6050               SAM-M8Q GPS
    |                      |
    |                      |
    v                      v

/mpu6050_node /nmea_navsat_driver
| |
| |
v v

/imu/data /fix
|
|
v

                     GPS Data


          Wheel Encoder (Future)
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


                Nav2

---

# ROS 2 Components

## Nodes

A node is an executable program that performs a specific function.

Goosebot currently uses:

---

## MPU6050 Node

Node:


/mpu6050_node


Purpose:

- Communicate with MPU6050 over I2C
- Read accelerometer data
- Read gyroscope data
- Publish IMU messages

Publishes:


/imu/data


Message type:


sensor_msgs/msg/Imu


---

## GPS Node

Node:


/nmea_navsat_driver


Purpose:

- Read NMEA GPS data from UART
- Parse latitude and longitude
- Convert GPS information into ROS messages

Hardware:


SparkFun SAM-M8Q


Connection:


UART


Device:


/dev/ttyS4


Publishes:


/fix
/heading
/vel
/time_reference


---

# ROS 2 Topics

Topics are continuous data streams.

A publisher sends messages to a topic.

A subscriber receives messages from a topic.

Example:

         Publisher

      MPU6050 Node

            |
            |
            v

        /imu/data

            |
            |
            v

      robot_localization

         Subscriber

---

# Current Topic List

Current working topics:


/imu/data

/fix

/heading

/vel

/time_reference

/parameter_events

/rosout


---

# Message Types

## IMU Message

Topic:


/imu/data


Type:


sensor_msgs/msg/Imu


Contains:

### Orientation

Robot rotation estimate.

Example:


x:
y:
z:
w:


Currently:


orientation_covariance[0] = -1


because the current MPU6050 setup does not provide fused orientation.

---

### Angular Velocity

Gyroscope output.

Example:


angular_velocity:
x:
y:
z:


Units:


rad/s


---

### Linear Acceleration

Accelerometer output.

Example:


linear_acceleration:
x:
y:
z:


Units:


m/s²


---

# GPS Message

Topic:


/fix


Type:


sensor_msgs/msg/NavSatFix


Contains:


latitude
longitude
altitude


Example:


latitude: 27.xxxxxx

longitude: -81.xxxxxx


---

# Coordinate Systems

ROS 2 uses coordinate frames to describe robot movement.

The main frames planned for Goosebot are:


map
|
|
odom
|
|
base_link
|
|
sensors


---

# Frame Explanation

## map

Global fixed coordinate system.

Used for:

- GPS
- SLAM
- Navigation

---

## odom

Local movement estimate.

Generated from:

- Wheel encoders
- IMU

Can drift over time.

---

## base_link

The robot body reference point.

All sensors are positioned relative to this frame.

---

## Sensor Frames

Examples:


imu_link

gps_link

base_link


These describe where each sensor is mounted.

---

# Sensor Fusion Flow

Each sensor has different characteristics.

## GPS

Advantages:

- Absolute position

Disadvantages:

- Slow updates
- Requires outdoor signal
- Less accurate temporarily

---

## IMU

Advantages:

- Fast updates
- Detects rotation and acceleration

Disadvantages:

- Drift over time

---

## Wheel Encoder

Advantages:

- Accurate short-term movement

Disadvantages:

- Wheel slip causes error

---

# Extended Kalman Filter (EKF)

Goosebot will use:


robot_localization


The EKF combines sensor information.

Input:


/imu/data

/fix

/odom


Output:


/odometry/filtered


The filter estimates the most likely robot state.

---

# Current Progress

Completed:

✅ ROS 2 Humble installed  
✅ Workspace created  
✅ IMU publishing  
✅ GPS publishing  
✅ nmea_navsat_driver working  
✅ robot_localization installed  

In progress:

⬜ Wheel encoder ROS node  
⬜ EKF configuration  
⬜ TF frame setup  
⬜ Nav2 integration  

---

# Future ROS 2 Expansion

Planned nodes:


camera_node

wheel_encoder_node

ultrasonic_node

ekf_filter_node

nav2_controller

slam_toolbox


Final goal:

A complete autonomous ROS 2 navigation stack.
