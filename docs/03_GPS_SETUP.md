# SparkFun SAM-M8Q GPS Setup

## Overview

The Goosebot uses the SparkFun SAM-M8Q GPS module for outdoor positioning.

The GPS module communicates with the Radxa ROCK 5C through UART and publishes GPS information into ROS2.

---

# Hardware

## GPS Module

```
SparkFun SAM-M8Q
u-blox M8 GNSS receiver
```

Capabilities:

- GPS
- GLONASS
- Galileo
- BeiDou
- QZSS
- NMEA output
- UBX protocol

---

# Wiring

## UART Connection

Connection:

```
SAM-M8Q TX  →  ROCK 5C RX
SAM-M8Q RX  →  ROCK 5C TX
```

Current pins:

```
GPS TX → ROCK 5C Pin 7
GPS RX → ROCK 5C Pin 29
```

Power:

```
VCC → 3.3V
GND → GND
```

---

# UART Configuration

The GPS is connected through:

```
/dev/ttyS4
```

Verify:

```bash
ls -l /dev/ttyS4
```

Expected:

```
crw-rw---- root dialout
```

---

# Testing GPS Communication

Before ROS2, verify raw NMEA messages:

```bash
cat /dev/ttyS4
```

Expected output:

```
$GNRMC
$GNVTG
$GNGGA
$GNGSA
$GPGSV
$GLGSV
```

Example:

```
$GNGGA,,,,,,0,00,99.99,,,,,,*56
```

Indoor readings may show no fix.

This is normal.

---

# GPS Fix Behavior

## Indoors

Expected:

```
latitude: .nan
longitude: .nan
altitude: .nan
```

Reason:

The GPS does not have enough satellite visibility.

---

## Outdoors

Expected:

```
latitude: XX.XXXXXX
longitude: XX.XXXXXX
altitude: XX.X
```

The SAM-M8Q successfully obtains satellite lock outdoors.

---

# ROS2 Setup

## Install NMEA Driver

The ROS2 NMEA driver is used because the GPS outputs standard NMEA sentences.

Repository:

```
nmea_navsat_driver
```

Build:

```bash
cd ~/ros2_humble/src

git clone -b ros2 https://github.com/ros-drivers/nmea_navsat_driver.git

cd ~/ros2_humble

colcon build \
--symlink-install \
--packages-select nmea_navsat_driver
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

# Running GPS Node

Start GPS ROS2 publisher:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

Successful output:

```
Successfully connected to /dev/ttyS4 at 9600
```

---

# ROS2 GPS Topics

Check:

```bash
ros2 topic list
```

GPS topics:

```
/fix
/vel
/heading
/time_reference
```

---

# Checking GPS Data

Run:

```bash
ros2 topic echo /fix --once
```

Example successful output:

```
latitude: XX.XXXX
longitude: XX.XXXX
altitude: XX.X
```

---

# Troubleshooting

## Problem: /dev/ttyACM0 does not exist

Cause:

The SAM-M8Q is connected through UART, not USB.

Wrong:

```
/dev/ttyACM0
```

Correct:

```
/dev/ttyS4
```

---

## Problem: No NMEA output

Check:

```bash
sudo lsof /dev/ttyS4
```

Make sure another program is not using the UART.

---

## Problem: GPS works indoors but shows NaN

Cause:

No satellite fix.

Solution:

Move outdoors with clear sky visibility.

---

# Current Status

Completed:

✅ UART communication  
✅ NMEA output  
✅ ROS2 GPS driver  
✅ /fix topic  
✅ Outdoor GPS position fix  


Future:

⬜ Convert GPS latitude/longitude to local coordinates

⬜ Fuse GPS with IMU using robot_localization EKF

⬜ Combine GPS + IMU + wheel encoder odometry
