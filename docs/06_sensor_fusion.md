# Sensor Fusion: IMU + GPS + Wheel Encoder

This document explains how Goosebot combines multiple sensors into one estimated robot position.

The goal is to create a reliable localization system using:

- MPU6050 IMU
- SparkFun SAM-M8Q GPS
- Wheel Encoders
- ROS2 robot_localization EKF

---

# 1. Why Sensor Fusion Is Needed

Each sensor has limitations.

## GPS

Provides:

- Absolute global position
- Latitude
- Longitude
- Altitude

Advantages:

✅ Does not drift over time

Disadvantages:

❌ Slow update rate  
❌ Indoor signal loss  
❌ Several meter accuracy error

Example:

```
Latitude:
27.xxxxxx

Longitude:
-81.xxxxxx
```

ROS2 topic:

```
/fix
```

---

# IMU

The MPU6050 provides:

- Linear acceleration
- Angular velocity

Advantages:

✅ Very fast updates  
✅ Detects movement and rotation

Disadvantages:

❌ Gyroscope drifts over time  
❌ Accelerometer accumulates error

ROS2 topic:

```
/imu/data
```

Current output:

```
angular_velocity

linear_acceleration
```

---

# Wheel Encoder

Wheel encoders provide:

- Wheel rotation
- Distance traveled
- Velocity

Advantages:

✅ Very accurate short-term movement

Disadvantages:

❌ Wheel slip causes error  
❌ Error increases over distance

ROS2 topic:

```
/odom
```

---

# 2. Why Combine Sensors?

Each sensor fixes another sensor's weakness.

Example:

Robot drives forward:

```
Encoder:
"I moved 5 meters"

IMU:
"I rotated 2 degrees"

GPS:
"You are actually here"
```

The EKF combines these measurements.

---

# 3. Extended Kalman Filter (EKF)

robot_localization uses an Extended Kalman Filter.

The EKF estimates:

- Position
- Velocity
- Orientation

by comparing:

```
Prediction
+
Sensor Measurements
=
Best Estimate
```

---

# 4. Data Flow

Current planned architecture:

```
                 GPS
                  |
                  |
                  v
              /fix topic


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

```

---

# 5. ROS2 Topics

Current working topics:

Check:

```bash
ros2 topic list
```

Expected:

```
/fix
/imu/data
```

Future:

```
/odom
/odometry/filtered
```

---

# 6. GPS Processing

The GPS sends NMEA strings:

Example:

```
$GNRMC
$GNGGA
$GNGSA
```

The ROS2 driver converts them into:

```
sensor_msgs/NavSatFix
```

Topic:

```
/fix
```

Example:

```bash
ros2 topic echo /fix --once
```

Output:

```
latitude:
longitude:
altitude:
```

---

# 7. IMU Processing

The MPU6050 publishes:

```
sensor_msgs/Imu
```

Topic:

```
/imu/data
```

Current status:

Working:

```
linear_acceleration
angular_velocity
```

Example:

```
linear_acceleration:
 z: 9.8
```

This confirms gravity detection.

---

# 8. Wheel Encoder Processing

Wheel encoder data must become ROS2 odometry.

Required information:

```
position x
position y
rotation theta

velocity x
velocity theta
```

ROS2 message:

```
nav_msgs/Odometry
```

Topic:

```
/odom
```

---

# 9. robot_localization Inputs

The EKF configuration tells robot_localization which values to trust.

Example:

```
imu0:
/imu/data

odom0:
/odom

gps:
 /fix
```

The EKF does NOT automatically detect sensors.

Every sensor must be configured.

---

# 10. Coordinate Systems

ROS2 uses coordinate frames.

Important frames:

```
map

 |

odom

 |

base_link

 |

imu_link
```

Meaning:

## map

Global position.

GPS reference.

---

## odom

Local movement estimate.

Wheel encoder + IMU.

---

## base_link

Robot center.

---

## imu_link

Physical IMU location.

---

# 11. Current Goosebot Status

## Completed

✅ ROS2 Humble workspace  
✅ MPU6050 ROS2 node  
✅ GPS ROS2 node  
✅ /fix topic working outdoors  
✅ /imu/data publishing  
✅ robot_localization installed  

---

# 12. Remaining Work

## Step 1

Create wheel encoder ROS2 publisher.

Convert:

```
encoder counts
```

into:

```
/odom
```

---

## Step 2

Create robot_localization EKF configuration.

Example:

```
ekf.yaml
```

---

## Step 3

Connect:

```
GPS

IMU

Wheel Encoder

        |

        v

robot_localization

        |

        v

filtered position
```

---

# 13. Testing Commands

Check nodes:

```bash
ros2 node list
```

Expected:

```
/mpu6050_node
/nmea_navsat_driver
```

---

Check GPS:

```bash
ros2 topic echo /fix --once
```

---

Check IMU:

```bash
ros2 topic echo /imu/data --once
```

---

Check topics:

```bash
ros2 topic list
```

---

# Final Goal

After completing sensor fusion:

Goosebot will know:

- Where it is
- Which direction it faces
- How far it traveled
- How fast it moves

This becomes the foundation for:

- ROS2 Nav2
- Autonomous navigation
- SLAM
- Path planning
