# Goosebot ROS2 Configuration

## Overview

This folder contains ROS2 configuration files used to define how Goosebot's software components operate.

Configuration files allow ROS2 nodes to be adjusted without changing the source code.

Examples:

- Sensor settings
- Coordinate frames
- Robot dimensions
- EKF parameters
- Navigation parameters

---

# Planned Configuration Structure

Future structure:

```
config/

├── robot_localization/
│   └── ekf.yaml
│
├── sensors/
│   ├── imu.yaml
│   └── gps.yaml
│
├── robot/
│   └── robot_description.yaml
│
└── nav2/
    └── nav2_params.yaml
```

---

# Current Configuration Status

Current completed:

[x] GPS UART communication verified

[x] GPS ROS2 driver working

[x] MPU6050 IMU publishing

[x] robot_localization installed


Current work:

[ ] Create EKF configuration

[ ] Configure sensor fusion parameters

[ ] Add robot frame definitions

[ ] Add Nav2 configuration

---

# robot_localization EKF Configuration

## Purpose

The EKF configuration tells `robot_localization`:

- Which sensors to use
- Which measurements are trusted
- How often sensors update
- How coordinate frames connect

---

# Planned EKF File

Location:

```
config/robot_localization/ekf.yaml
```

---

# Sensor Fusion Inputs

Goosebot will combine:

## IMU

Topic:

```
/imu/data
```

Provides:

- Angular velocity
- Linear acceleration
- Orientation (future calibration)
- Rotation information

---

## GPS

Topic:

```
/fix
```

Provides:

- Latitude
- Longitude
- Altitude

GPS will later be converted into a local coordinate system for localization.

---

## Wheel Encoder

Future topic:

```
/wheel/odometry
```

Provides:

- Distance traveled
- Robot velocity
- Wheel movement

---

# EKF Data Flow

```
              MPU6050
                 |
                 |
                 v

             /imu/data


GPS
 |
 |
 v

/fix


Encoder
 |
 |
 v

/wheel/odometry


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

# Coordinate Frames

ROS2 uses coordinate frames to describe robot movement.

Planned Goosebot frames:

```
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
```

---

## map

Global reference frame.

Sources:

- GPS
- SLAM

---

## odom

Short-term continuous movement estimate.

Sources:

- Wheel encoder
- IMU

---

## base_link

The center of the robot.

All sensors are positioned relative to this frame.

---

## Sensor Frames

Current:

```
imu_link
```

Future:

```
gps_link
wheel_left
wheel_right
camera_link
```

---

# Example EKF Parameters (Future)

Example file:

```
ekf.yaml
```

will contain:

```yaml
frequency: 30

two_d_mode: true

publish_tf: true

map_frame: map

odom_frame: odom

base_link_frame: base_link

imu0: /imu/data

gps0: /gps/fix
```

This will be customized after encoder integration.

---

# Sensor Update Rates

Different sensors operate at different speeds.

Example:

```
IMU
 |
50-100 Hz


Encoder
 |
10-50 Hz


GPS
 |
1-10 Hz
```

The EKF handles these different update rates automatically.

---

# Configuration Workflow

When adding a new sensor:

1. Confirm ROS2 topic exists

Example:

```bash
ros2 topic list
```

---

2. Check message format

Example:

```bash
ros2 topic echo /imu/data --once
```

---

3. Add sensor to EKF configuration

Edit:

```
config/robot_localization/ekf.yaml
```

---

4. Rebuild workspace:

```bash
cd ~/ros2_humble

colcon build --symlink-install
```

---

5. Source workspace:

```bash
source install/setup.bash
```

---

6. Test output:

```bash
ros2 topic echo /odometry/filtered
```

---

# Future Configuration Goals

[ ] Complete EKF YAML

[ ] Add GPS localization parameters

[ ] Add encoder odometry parameters

[ ] Add TF frame configuration

[ ] Add Nav2 parameters

[ ] Tune localization accuracy

---

# Related Documentation

ROS2 architecture:

```
../../docs/02_ros2/
```

Sensor fusion:

```
../../docs/04_localization/
```

Hardware:

```
../../docs/03_sensors/
```
