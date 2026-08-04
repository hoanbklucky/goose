# Troubleshooting Guide

This page documents common problems encountered while building Goosebot with:

- Radxa ROCK 5C
- Debian 12
- ROS2 Humble
- MPU6050 IMU
- SparkFun SAM-M8Q GPS
- Wheel Encoders
- robot_localization EKF

The goal is to record problems, causes, and solutions so future builds can be repeated.

---

# 1. ROS2 Package Not Found

## Problem

Running:

```bash
ros2 pkg list
```

does not show a package after building.

Example:

```
ros2 pkg list | grep nmea
```

Only shows:

```
nmea_msgs
```

but not:

```
nmea_navsat_driver
```

---

## Cause

The workspace was built, but the terminal was not sourced.

ROS2 only knows about packages after loading the workspace.

---

## Solution

Run:

```bash
source ~/ros2_humble/install/setup.bash
```

Then check:

```bash
ros2 pkg list | grep package_name
```

Example:

```bash
ros2 pkg list | grep nmea
```

Expected:

```
nmea_msgs
nmea_navsat_driver
```

---

# 2. nmea_navsat_driver Catkin Error

## Problem

Building:

```bash
colcon build --packages-select nmea_navsat_driver
```

returned:

```
Could not find a package configuration file provided by "catkin"
```

---

## Cause

The wrong branch was downloaded.

The default repository branch was ROS1 and used:

```
catkin
```

ROS2 uses:

```
ament
```

---

## Solution

Delete the package:

```bash
cd ~/ros2_humble/src

rm -rf nmea_navsat_driver
```

Clone the ROS2 branch:

```bash
git clone -b ros2 https://github.com/ros-drivers/nmea_navsat_driver.git
```

Build:

```bash
cd ~/ros2_humble

colcon build \
--symlink-install \
--packages-select nmea_navsat_driver \
--parallel-workers 1
```

Source:

```bash
source ~/ros2_humble/install/setup.bash
```

---

# 3. u-blox GPS Driver Baud Rate Error

## Problem

Running:

```bash
ros2 run ublox_gps ublox_gps_node
```

returned:

```
Could not configure serial baud rate
```

---

## Cause

The SparkFun SAM-M8Q was already outputting valid NMEA data.

The ublox ROS driver attempted to reconfigure the GPS UART settings.

The module firmware and driver configuration did not agree.

---

## Solution

Use the NMEA driver instead.

The SAM-M8Q already provides:

```
$GNRMC
$GNGGA
$GNGSA
$GPGSV
```

messages.

Run:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

---

# 4. GPS Shows NaN Values

## Problem

Running:

```bash
ros2 topic echo /fix --once
```

shows:

```
latitude: .nan
longitude: .nan
altitude: .nan
```

---

## Cause

The GPS has no satellite fix.

This commonly happens:

- Indoors
- Near buildings
- Without antenna visibility

---

## Solution

Move outdoors.

A working fix should show:

```
status:
  status: 0

latitude:
  27.xxxxxx

longitude:
  -81.xxxxxx
```

The GPS must see satellites before valid coordinates appear.

---

# 5. GPS Works in Minicom but Not cat

## Problem

Minicom displays:

```
$GNRMC
$GNGGA
$GPGSV
```

but:

```bash
cat /dev/ttyS4
```

shows nothing.

---

## Cause

UART settings were not configured correctly.

---

## Solution

Set UART manually:

```bash
sudo stty -F /dev/ttyS4 9600 cs8 -cstopb -parenb -ixon -ixoff
```

Then:

```bash
timeout 20 cat /dev/ttyS4
```

---

# 6. GPS UART Wiring

## SparkFun SAM-M8Q → ROCK 5C

Connection:

| GPS | ROCK 5C |
|-|-|
| TX | Pin 7 |
| RX | Pin 29 |
| GND | GND |
| VCC | 3.3V |

Important:

TX connects to RX.

RX connects to TX.

---

# 7. IMU Topic Exists But Orientation Is Zero

## Problem

Running:

```bash
ros2 topic echo /imu/data --once
```

shows:

```
orientation:
 x:0
 y:0
 z:0
 w:1
```

---

## Cause

The MPU6050 only provides:

- Accelerometer
- Gyroscope

It does not calculate orientation by itself.

---

## Current Output

Working:

```
angular_velocity
linear_acceleration
```

Example:

```
linear_acceleration:
 z: ~9.8
```

This means gravity is detected correctly.

---

## Future Solution

Add sensor fusion:

- Madgwick filter
- Complementary filter
- robot_localization EKF

---

# 8. robot_localization Has No Output

## Problem

Package exists:

```bash
ros2 pkg list | grep robot_localization
```

but no EKF output appears.

---

## Cause

robot_localization does not automatically read sensors.

It requires:

- IMU topic
- GPS topic
- Wheel odometry topic

---

## Required Inputs

Example:

```
/imu/data

/fix

/odom
```

Then EKF combines them.

---

# 9. Wheel Encoder Distance Incorrect

## Problem

Distance calculation is wrong.

---

## Cause

Wheel diameter calibration was incorrect.

---

## Current Calibration

Wheel diameter:

```
2.6 inches
```

Encoder counts:

```
1092 counts/revolution
```

Formula:

```
distance =
(revolutions)
×
wheel circumference
```

where:

```
circumference = π × wheel diameter
```

---

# 10. Python Package Missing

## Problem

Example:

```
ModuleNotFoundError
```

---

## Cause

Python package installed outside the virtual environment.

---

## Solution

Activate environment:

```bash
source venv/bin/activate
```

Install package:

```bash
pip install package_name
```

---

# 11. gpiod Version Conflict

## Problem

Errors:

```
Chip.get_line does not exist
```

or:

```
Device or resource busy
```

---

## Cause

Different gpiod versions:

System:

```
libgpiod 1.6.3
```

Python:

```
gpiod 2.x
```

The APIs are different.

---

## Solution

Check:

```bash
python3 -m pip show gpiod
```

and:

```bash
gpioinfo --version
```

Make sure code matches installed version.

---

# 12. I2C Device Not Found

## Problem

PCA9685 or sensors cannot be detected.

---

## Check buses:

```bash
i2cdetect -l
```

Scan:

```bash
sudo i2cdetect -y -r BUS_NUMBER
```

Example:

```bash
sudo i2cdetect -y -r 6
```

---

Expected devices:

Example:

```
40
68
```

Where:

```
0x40 = PCA9685
0x68 = MPU6050
```

---

# 13. ROS2 Build Errors

## General Fix

Always:

```bash
cd ~/ros2_humble

colcon build --symlink-install
```

Then:

```bash
source install/setup.bash
```

---

# 14. Checking Running ROS2 System

Nodes:

```bash
ros2 node list
```

Topics:

```bash
ros2 topic list
```

Sensor testing:

GPS:

```bash
ros2 topic echo /fix --once
```

IMU:

```bash
ros2 topic echo /imu/data --once
```

---

# Current Working Checkpoint

Current working system:

## GPS

Status:

✅ SparkFun SAM-M8Q working  
✅ UART4 (/dev/ttyS4) working  
✅ NMEA messages received  
✅ ROS2 GPS topic publishing  

Topic:

```
/fix
```

---

## IMU

Status:

✅ MPU6050 working  
✅ ROS2 node publishing  

Topic:

```
/imu/data
```

---

## ROS2

Status:

✅ ROS2 Humble workspace  
✅ nmea_navsat_driver installed  
✅ robot_localization installed  

---

## Next Development Step

The next stage is:

```
Wheel Encoder
        |
        v
       /odom

GPS
 |
 v
/navsat_transform_node

IMU
 |
 v
/imu/data

        |
        v

robot_localization EKF

        |
        v

/odometry/filtered
```

This will create a fused robot position estimate for navigation.
