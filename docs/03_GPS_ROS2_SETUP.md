# 03 - GPS Setup (SparkFun SAM-M8Q → ROCK 5C → ROS2)

## Overview

This section documents the setup of the SparkFun SAM-M8Q GPS module connected to the Radxa ROCK 5C through UART.

Hardware used:

- GPS Module: SparkFun SAM-M8Q
- Computer: Radxa ROCK 5C
- Communication: UART
- ROS2: Humble
- GPS Driver: nmea_navsat_driver

Final data flow:

```
SparkFun SAM-M8Q
        |
        | UART
        |
ROCK 5C UART4
        |
        | /dev/ttyS4
        |
nmea_navsat_driver
        |
        |
ROS2 Topics:
    /fix
    /vel
    /heading
    /time_reference
```

---

# Wiring

## SparkFun SAM-M8Q → ROCK 5C

| SAM-M8Q | ROCK 5C |
|---|---|
| VCC | 3.3V |
| GND | GND |
| TX | UART RX |
| RX | UART TX |

Current working connection:

```
SAM-M8Q TX → ROCK 5C RX
SAM-M8Q RX → ROCK 5C TX
```

UART device:

```
/dev/ttyS4
```

---

# Verify UART Device

Check UART exists:

```bash
ls -l /dev/ttyS4
```

Expected:

```
crw-rw---- 1 root dialout ... /dev/ttyS4
```

---

# Test Raw GPS Data

Install minicom:

```bash
sudo apt install minicom
```

Run:

```bash
sudo minicom -D /dev/ttyS4 -b 9600
```

Working output:

```
$GNRMC,,V,,,,,,,,,,N*4D
$GNVTG,,,,,,,,,N*2E
$GNGGA,,,,,,0,00,99.99,,,,,,*56
$GNGSA,A,1,,,,,,,,,,,,,99.99,99.99,99.99*2E
```

When outdoors with GPS lock:

Example:

```
$GNRMC,xxxxxx,A,latitude,N,longitude,E,...
$GNGGA,...,1,...
```

---

# Install ROS2 NMEA Driver

Go to ROS2 workspace:

```bash
cd ~/ros2_humble/src
```

Clone ROS2 branch:

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

Verify:

```bash
ros2 pkg list | grep nmea
```

Expected:

```
nmea_msgs
nmea_navsat_driver
```

---

# Start GPS ROS2 Node

Run:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

Expected:

```
Successfully connected to /dev/ttyS4 at 9600.
```

---

# ROS2 GPS Topics

Check available topics:

```bash
ros2 topic list
```

Expected:

```
/fix
/heading
/time_reference
/vel
```

---

# Check GPS Position

Run:

```bash
ros2 topic echo /fix --once
```

Working outdoor GPS:

Example:

```
latitude: 27.xxxxxx
longitude: -81.xxxxxx
altitude: xx.x
```

---

# Indoor GPS Behavior

Inside buildings GPS may show:

```
latitude: .nan
longitude: .nan
altitude: .nan
status:
  status: -1
```

This is normal.

Meaning:

```
No GPS fix available
```

Move outdoors with clear sky view.

---

# Troubleshooting

## Problem: /dev/ttyACM0 not found

Cause:

Wrong configuration.

SAM-M8Q is UART, not USB.

Incorrect:

```
/dev/ttyACM0
```

Correct:

```
/dev/ttyS4
```

---

## Problem: U-Blox driver baud error

The ublox_gps package attempted to configure the GPS directly.

Issue:

The SparkFun SAM-M8Q already outputs NMEA correctly.

Solution:

Use:

```
nmea_navsat_driver
```

instead of:

```
ublox_gps
```

---

## Problem: No data from cat

Example:

```bash
cat /dev/ttyS4
```

shows nothing.

Check:

1. GPS power
2. TX/RX swapped
3. Correct UART enabled
4. Correct baud rate

Test:

```bash
sudo stty -F /dev/ttyS4 9600 cs8 -cstopb -parenb
```

---

# Current Working Status

Completed:

✅ UART communication  
✅ /dev/ttyS4 detected  
✅ SAM-M8Q NMEA output verified  
✅ ROS2 nmea_navsat_driver installed  
✅ /fix topic publishing  
✅ Outdoor latitude/longitude working  

Current ROS2 nodes:

```
/nmea_navsat_driver
/mpu6050_node
```

Current topics:

```
/fix
/heading
/imu/data
/time_reference
/vel
```

---

# Next Step

Integrate:

```
GPS
 +
IMU
 +
Wheel Encoder
        |
        v
robot_localization EKF
        |
        v
Robot Pose Estimate
```
