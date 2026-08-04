# robot_localization + EKF Setup

This document explains how Goosebot will combine sensor data using ROS2 `robot_localization`.

The goal is to fuse:

- MPU6050 IMU
- Wheel Encoder Odometry
- GPS Position

into a single reliable position estimate.

Output:

```
/odometry/filtered
```

---

# 1. What is robot_localization?

`robot_localization` is a ROS2 package that performs sensor fusion.

It uses an:

```
Extended Kalman Filter (EKF)
```

to combine multiple imperfect sensors.

---

# 2. Why Sensor Fusion?

Each sensor has weaknesses.

## IMU

Good:

- Fast updates
- Rotation
- Acceleration

Bad:

- Drift over time

---

## GPS

Good:

- Absolute position

Bad:

- Slow updates
- Indoor failure
- Noise

---

## Wheel Encoder

Good:

- Distance traveled
- Velocity

Bad:

- Wheel slip
- Accumulated error

---

# 3. EKF Concept

The EKF constantly predicts and corrects.

Example:

Robot moves forward.

## Prediction

Using:

```
IMU + encoder
```

The filter predicts:

```
"I think the robot is here"
```

---

## Correction

GPS says:

```
"Actually you are slightly over here"
```

The EKF adjusts.

---

Final result:

```
best estimate
```

---

# 4. Sensor Flow

Final architecture:

```
                 GPS

                  |

                  v

                /fix



IMU

 |

 v

/imu/data



Encoder

 |

 v

/odom



        |

        v


robot_localization EKF


        |

        v


/odometry/filtered

```

---

# 5. Current Sensor Status

Completed:

```
/imu/data
```

from MPU6050.

---

Completed:

```
/fix
```

from SAM-M8Q GPS.

---

Not completed:

```
/odom
```

from wheel encoder.

---

# 6. Install robot_localization

Check:

```bash
ros2 pkg list | grep robot_localization
```

Expected:

```
robot_localization
```

---

# 7. Create EKF Configuration Folder

Create:

```bash
mkdir -p ~/ros2_humble/src/goosebot_localization/config
```

---

Create:

```
ekf.yaml
```

inside:

```
goosebot_localization/config/
```

---

# 8. EKF Configuration

Example:

```yaml
ekf_filter_node:
  ros__parameters:

    frequency: 30.0

    two_d_mode: true

    publish_tf: true

    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom


    imu0: /imu/data

    imu0_config:
      [
        false, false, false,

        false, false, true,

        false, false, false,

        false, false, true,

        false, false, false
      ]


    odom0: /odom

    odom0_config:
      [
        true, true, false,

        false, false, true,

        false, false, false,

        false, false, false,

        false, false, false
      ]

```

---

# 9. Understanding *_config

Each sensor has a list of 15 values.

Order:

```
x
y
z

roll
pitch
yaw

velocity x
velocity y
velocity z

angular velocity roll
angular velocity pitch
angular velocity yaw

acceleration x
acceleration y
acceleration z
```

Example:

```
true
```

means:

"Use this measurement."

```
false
```

means:

"Ignore this measurement."

---

# 10. Launch EKF

Example:

```bash
ros2 run robot_localization ekf_node \
--ros-args \
--params-file ekf.yaml
```

---

# 11. Check Output

Topics:

```bash
ros2 topic list
```

Expected:

```
/odometry/filtered
```

---

Check:

```bash
ros2 topic echo /odometry/filtered --once
```

---

# 12. GPS Integration

GPS should eventually publish:

```
sensor_msgs/NavSatFix
```

Topic:

```
/fix
```

---

A second node:

```
navsat_transform_node
```

converts:

```
latitude longitude altitude
```

into:

```
map coordinates
```

---

Flow:

```
GPS

 |

 v

/fix


navsat_transform_node


 |

 v


/odometry/gps


 |

 v


EKF

```

---

# 13. Encoder Integration

Encoder must publish:

```
nav_msgs/Odometry
```

Topic:

```
/odom
```

Required:

```
position

orientation

velocity
```

---

Example:

```
wheel rotation

      |

      v

distance traveled

      |

      v

robot x/y position

      |

      v

/odom
```

---

# 14. Current Limitations

The current IMU publishes:

```
orientation:
x:0
y:0
z:0
w:1
```

This means:

```
no orientation estimate
```

Only:

```
angular velocity

linear acceleration
```

are currently useful.

---

Future improvements:

- Add gyro integration
- Add covariance values
- Calibrate IMU
- Publish proper orientation

---

# 15. Testing Order

When EKF is ready:

Start IMU:

```bash
ros2 run mpu6050_driver mpu6050_node
```

---

Start GPS:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

---

Start encoder:

```
encoder_node
```

---

Start EKF:

```bash
ros2 run robot_localization ekf_node \
--ros-args \
--params-file ekf.yaml
```

---

Check:

```bash
ros2 topic echo /odometry/filtered
```

---

# Final Goal

The finished Goosebot localization system:

```
GPS
 |
 |
IMU -----> robot_localization EKF -----> Nav2
 |
 |
Encoder
```

The EKF provides the robot's best estimate of:

- Position
- Heading
- Velocity

which becomes the foundation for autonomous navigation.
