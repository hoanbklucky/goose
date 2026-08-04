# ROS2 Troubleshooting Guide

This document contains problems encountered while building Goosebot and their solutions.

The purpose is to help someone reproduce the project and avoid common mistakes.

---

# 1. ROS2 Package Not Found

## Problem

Running:

```bash
ros2 run package_name node_name
```

returns:

```
package not found
```

---

## Cause

The workspace has not been sourced.

---

## Solution

Run:

```bash
source ~/ros2_humble/install/setup.bash
```

Verify:

```bash
ros2 pkg list
```

---

# 2. colcon Command Missing

## Problem

Running:

```bash
colcon build
```

returns:

```
command not found
```

---

## Cause

Colcon extensions are not installed.

---

## Solution

Install:

```bash
pip install colcon-common-extensions
```

or:

```bash
sudo apt install python3-colcon-common-extensions
```

Check:

```bash
colcon --version
```

---

# 3. Wrong ROS Package Version

## Problem

Building a package gives:

```
Could not find catkin
```

Example:

```
find_package(catkin REQUIRED)
```

---

## Cause

The package is ROS1, not ROS2.

ROS1 uses:

```
catkin
```

ROS2 uses:

```
ament
```

---

## Solution

Remove the ROS1 package:

```bash
rm -rf package_name
```

Clone the ROS2 branch:

Example:

```bash
git clone -b ros2 \
https://github.com/ros-drivers/nmea_navsat_driver.git
```

Check:

```bash
grep build_type package.xml
```

Correct ROS2 output:

```
ament_python
```

---

# 4. GPS Driver Baud Rate Error

## Problem

Running:

```bash
ros2 run ublox_gps ublox_gps_node
```

returns:

```
Could not configure serial baud rate
```

---

## Cause

The SparkFun SAM-M8Q was already outputting NMEA correctly, but the u-blox driver attempted to configure unsupported settings.

---

## Solution

Use the NMEA driver instead:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

---

# 5. GPS Works But Latitude Is NaN

## Problem

Topic:

```bash
ros2 topic echo /fix
```

shows:

```
latitude: .nan
longitude: .nan
```

---

## Cause

GPS has no satellite fix.

Common indoors.

---

## Solution

Move outdoors.

A valid fix should show:

```
latitude:
longitude:
altitude:
```

---

# 6. GPS Serial Output Missing

## Problem

Running:

```bash
cat /dev/ttyS4
```

shows nothing.

---

## Check

Verify UART exists:

```bash
ls -l /dev/ttyS4
```

---

Set baud:

```bash
sudo stty -F /dev/ttyS4 9600 cs8 -cstopb -parenb
```

---

Check wiring:

```
GPS TX → ROCK RX

GPS RX → ROCK TX
```

UART communication requires crossing TX/RX.

---

# 7. GPS Produces Garbage Characters

## Problem

Output:

```
invalid utf-8 byte
```

Example:

```
codec can't decode byte
```

---

## Cause

Serial settings mismatch.

---

## Fix

Set:

```bash
sudo stty -F /dev/ttyS4 9600 cs8 -cstopb -parenb -ixon -ixoff
```

---

# 8. MPU6050 Not Detected

## Problem

I2C scan does not show:

```
68
```

---

## Check wiring

Correct:

| MPU6050 | ROCK 5C |
|-|-|
| SDA | Pin 27 |
| SCL | Pin 28 |
| GND | GND |
| VCC | 3.3V |

---

Scan:

```bash
sudo i2cdetect -y -r BUS_NUMBER
```

---

Expected:

```
68
```

---

# 9. I2C Address Conflict

## Problem

Multiple devices appear on I2C.

---

## Example

PCA9685:

```
0x40
```

MPU6050:

```
0x68
```

---

## Solution

Use different addresses or different buses.

Check:

```bash
i2cdetect -l
```

---

# 10. gpiod Version/API Conflict

## Problem

Python error:

```
Chip.get_line does not exist
```

or:

```
Device or resource busy
```

---

## Cause

Different libgpiod versions.

Example:

System:

```
gpiod 1.6.3
```

Python environment:

```
gpiod 2.x
```

The APIs are different.

---

## Solution

Check version:

```bash
python -m pip show gpiod
```

Use matching API.

---

# 11. Keyboard Library Requires Root

## Problem

Motor test:

```
keyboard requires root
```

---

## Solution

Run:

```bash
sudo python motor_test.py
```

or replace keyboard library with terminal input.

---

# 12. Encoder Does Not Count

## Problem

Motor moves but encoder stays:

```
0 counts
```

---

## Check GPIO pins

Current wiring:

| Encoder | Pin |
|-|-|
| Left A | 11 |
| Left B | 13 |
| Right A | 15 |
| Right B | 16 |

---

Check GPIO:

```bash
gpioinfo
```

---

Test encoder before ROS2 integration.

---

# 13. Motor Driver Beeping

## Problem

Motor driver makes continuous beep.

---

## Cause

Possible:

- Incorrect PWM signal
- Floating input pins
- Power connection issue

---

## Test

Disconnect PWM.

If sound stops:

PWM control is the issue.

---

# 14. robot_localization Has No Output

## Problem

Installed:

```bash
ros2 pkg list | grep robot_localization
```

but no:

```
/odometry/filtered
```

---

## Cause

EKF node has not been launched.

Installing the package does not start it.

---

## Required

Need:

```
ekf.yaml

launch file

sensor topics
```

Example:

```
/imu/data

/odom

/gps
```

---

# 15. Sensor Data Has Zero Covariance

## Problem

IMU output:

```
covariance:
0.0
```

---

## Meaning

The driver is not providing uncertainty values.

---

## Future Fix

Update IMU node to publish:

```
orientation covariance

gyro covariance

acceleration covariance
```

This improves EKF performance.

---

# 16. Current Goosebot Debug Checklist

Before testing:

## ROS2

```bash
source ~/ros2_humble/install/setup.bash
```

---

## Check nodes:

```bash
ros2 node list
```

Expected:

```
/mpu6050_node
/nmea_navsat_driver
```

---

## Check topics:

```bash
ros2 topic list
```

Expected:

```
/imu/data
/fix
```

---

## Check IMU:

```bash
ros2 topic echo /imu/data --once
```

---

## Check GPS:

Outdoor:

```bash
ros2 topic echo /fix --once
```

---

# Final Debug Flow

```
Hardware

   |

   v

Linux Device

   |

   v

ROS2 Driver

   |

   v

ROS2 Topic

   |

   v

robot_localization

   |

   v

Navigation
```

Always verify each layer before moving forward.
