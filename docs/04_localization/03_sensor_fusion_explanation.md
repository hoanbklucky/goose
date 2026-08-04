# Sensor Fusion Explanation

## Overview

Autonomous robots cannot rely on a single sensor for navigation.

Every sensor has advantages and limitations.

Goosebot uses multiple sensors together to create a more accurate understanding of its position and movement.

The process of combining sensor information is called **sensor fusion**.

---

# Why Sensor Fusion Is Needed

Each sensor provides different information.

Example:

A GPS module can tell the robot:

> "You are approximately here."

However, GPS updates slowly and may have several meters of error.

An IMU can tell the robot:

> "You rotated and accelerated this much."

However, the IMU slowly accumulates error over time.

A wheel encoder can tell the robot:

> "Your wheels moved this distance."

However, wheel slip can cause incorrect measurements.

By combining all three, the robot can estimate its position much better.

---

# Goosebot Sensor Sources

Goosebot uses three primary localization sensors:


GPS
|
|
v

Absolute Position

IMU
|
|
v

Rotation + Acceleration

Wheel Encoder
|
|
v

Distance Traveled


---

# GPS Localization

## Hardware


SparkFun SAM-M8Q


Communication:


UART


Device:


/dev/ttyS4


---

## GPS Output

The GPS receives satellite signals and produces NMEA messages.

Example:


$GNRMC
$GNGGA
$GNGSA


These contain:

- Latitude
- Longitude
- Altitude
- Velocity
- Satellite information

---

## ROS 2 GPS Topic

The GPS driver converts NMEA messages into ROS messages.

Node:


/nmea_navsat_driver


Topic:


/fix


Message type:


sensor_msgs/msg/NavSatFix


Example:


latitude: 27.xxxxxx

longitude: -81.xxxxxx

altitude: xx.x


---

# GPS Limitations

GPS is useful because it provides absolute location.

However:

## Indoor Limitations

Inside buildings:


latitude: .nan
longitude: .nan
status: -1


This means:


No GPS fix available


This is expected behavior.

---

## GPS Update Rate

GPS is relatively slow compared to IMU.

Typical:


1-10 Hz


The robot cannot rely on GPS alone for fast movement.

---

# IMU Localization

## Hardware


GY-521 MPU6050


Communication:


I2C


---

## IMU Measurements

The IMU provides:

## Accelerometer

Measures:

- Linear acceleration
- Gravity direction

Units:


m/s²


Example:


linear_acceleration:

x:
y:
z:


---

## Gyroscope

Measures:

- Rotation speed

Units:


rad/s


Example:


angular_velocity:

x:
y:
z:


---

# IMU Advantages

IMU provides fast updates.

Example:

A robot turning:


IMU detects rotation immediately


before GPS has time to update.

---

# IMU Limitations

The IMU has drift.

Small errors accumulate:


small error
|
|
v
larger error over time


Because of this, the IMU must be corrected by other sensors.

---

# Wheel Odometry

## Hardware

Goosebot uses:


TT Encoder Motors


with:


Hall-effect quadrature encoders


---

## Purpose

Wheel encoders measure:

- Wheel rotation
- Distance traveled
- Robot velocity

---

## Calibration

Current values:


Wheel Diameter:

2.6 inches

Encoder Resolution:

1092 counts/revolution


---

## Wheel Encoder Advantages

Very useful for short-term movement.

Example:

Robot moves forward:


Encoder:

0 inches
|
|
v
10 inches


The robot knows it moved.

---

## Wheel Encoder Limitations

Errors occur from:

- Wheel slip
- Uneven surfaces
- Motor differences

Example:

Robot thinks:


Moved 1 meter


Actual:


Moved 0.95 meters


The error accumulates.

---

# Extended Kalman Filter (EKF)

Goosebot uses:


robot_localization


The EKF is responsible for combining sensor information.

---

# Simple EKF Explanation

The EKF works by:

1. Predicting where the robot should be
2. Comparing predictions with sensor measurements
3. Correcting the estimate

Example:

Robot prediction:


Wheel encoder says:

Move forward 1 meter


IMU says:


Rotation = 0 degrees


GPS says:


Actual position is slightly different


The EKF combines all information and produces the best estimate.

---

# EKF Inputs

Planned inputs:


/imu/data

/fix

/odom


---

# EKF Output

The filter produces:


/odometry/filtered


This becomes the robot's best estimate of:

- Position
- Velocity
- Orientation

---

# Sensor Update Rates

Different sensors operate at different speeds.

Example:


IMU:

100 Hz

Wheel Encoder:

20-100 Hz

GPS:

1-10 Hz


The EKF handles these different rates automatically.

The robot does not need every sensor to update at the same time.

---

# Sensor Fusion Architecture

Final system:

             GPS

              |

              v

             /fix



             IMU

              |

              v

          /imu/data



      Wheel Encoder

              |

              v

             /odom



              |

              v


      robot_localization


              |

              v


      /odometry/filtered

---

# Current Status

Completed:

✅ GPS communication  
✅ GPS ROS topic  
✅ IMU ROS topic  
✅ robot_localization installed  

Remaining:

⬜ Wheel encoder ROS publisher  
⬜ EKF configuration file  
⬜ TF frame configuration  
⬜ Full localization testing  

---

# Future Goal

The final objective is to create a robot that can:

- Know its location
- Track its movement
- Navigate autonomously
- Follow planned paths
- Use SLAM and Nav2 for autonomous driving
