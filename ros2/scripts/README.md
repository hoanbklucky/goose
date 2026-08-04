# Goosebot ROS2 Scripts

## Overview

This folder contains supporting Python scripts used during Goosebot development.

These scripts are used for:

- Hardware testing
- Sensor verification
- Calibration
- Debugging
- Data collection
- Early development before converting functionality into ROS2 nodes

The development process started with standalone Python programs before integrating everything into ROS2.

---

# Development Workflow

Goosebot development follows this progression:

```
Standalone Python Script

        |
        |
        v

Hardware Testing

        |
        |
        v

ROS2 Node Conversion

        |
        |
        v

Robot Integration
```

---

# Current Script Organization

Future structure:

```
scripts/

├── sensors/
│   ├── imu_test.py
│   └── gps_test.py
│
├── motors/
│   ├── motor_test.py
│   └── encoder_test.py
│
├── calibration/
│   └── imu_calibration.py
│
└── utilities/
    └── diagnostics.py
```

---

# Sensor Testing Scripts

## IMU Testing

Purpose:

Verify MPU6050 communication before ROS2 integration.

Checks:

- I2C communication
- Accelerometer readings
- Gyroscope readings
- Temperature

Example output:

```
Acceleration:
X:
Y:
Z:

Gyroscope:
X:
Y:
Z:
```

---

## GPS Testing

Purpose:

Verify UART communication with GPS module.

Hardware:

```
SparkFun u-blox SAM-M8Q
```

UART:

```
/dev/ttyS4
```

Baud:

```
9600
```

Raw test:

```bash
sudo stty -F /dev/ttyS4 9600 cs8 -cstopb -parenb

cat /dev/ttyS4
```

Expected:

```
$GNRMC
$GNGGA
$GNGSA
```

---

# Motor Testing Scripts

## Motor Controller Test

Purpose:

Verify:

- PWM output
- Motor direction
- Motor driver wiring

Hardware:

```
PCA9685
L298N
DC motors
```

---

## Encoder Test

Purpose:

Verify wheel encoder signals.

Checks:

- Encoder A channel
- Encoder B channel
- Pulse counting
- Direction detection

Example:

```
Left Encoder:
count = 100

Right Encoder:
count = 100
```

---

# Encoder Calibration

The encoder system requires calibration values.

Current values:

Wheel diameter:

```
2.6 inches
```

Encoder counts per revolution:

```
1092 counts/revolution
```

The encoder converts:

```
Encoder pulses

        |

        v

Wheel rotation

        |

        v

Distance traveled
```

---

# ROS2 Conversion Process

Scripts are converted into ROS2 nodes when stable.

Example:

Before:

```
imu_test.py
```

After:

```
mpu6050_node
```

---

Before:

```
gps_test.py
```

After:

```
nmea_navsat_driver
```

---

Before:

```
encoder_test.py
```

After:

```
encoder_node
```

---

# Debugging Workflow

When hardware fails:

## Step 1: Test hardware directly

Example:

```
Python script
```

---

## Step 2: Confirm readings

Example:

```
Sensor values change correctly
```

---

## Step 3: Convert to ROS2

Create:

```
ROS2 node
```

---

## Step 4: Verify topics

Example:

```bash
ros2 topic list
```

---

## Step 5: Integrate

Connect:

```
Sensor

↓

ROS2 Topic

↓

Localization

↓

Navigation
```

---

# Useful Commands

List ROS2 nodes:

```bash
ros2 node list
```

List topics:

```bash
ros2 topic list
```

Check topic data:

```bash
ros2 topic echo <topic_name>
```

Check packages:

```bash
ros2 pkg list
```

---

# Current Status

Completed:

[x] IMU testing completed

[x] GPS UART testing completed

[x] Motor encoder testing completed


Working ROS2 replacements:

[x] MPU6050 node

[x] GPS driver


Future:

[ ] Encoder ROS2 node

[ ] Motor ROS2 node

[ ] Autonomous control scripts

[ ] Nav2 integration

---

# Related Documentation

Nodes:

```
../nodes/
```

Packages:

```
../packages/
```

Configuration:

```
../config/
```

Launch:

```
../launch/
```
