# SparkFun SAM-M8Q GPS Setup with Radxa ROCK 5C

## Overview

This guide explains how to connect and configure the **SparkFun SAM-M8Q GNSS GPS module** with the **Radxa ROCK 5C** for the GooseBot autonomous navigation project.

The goal is to obtain:

* Latitude
* Longitude
* Altitude
* GPS fix status
* Number of satellites
* Ground speed
* Heading direction
* Timestamp

The GPS communicates with the ROCK 5C using **UART serial communication**.

---

# Hardware Required

## Components

* Radxa ROCK 5C
* SparkFun SAM-M8Q GPS Module
* Jumper wires
* 3.3V compatible power source
* GPS antenna (included with module)

---

# SAM-M8Q Interfaces

The SAM-M8Q provides multiple communication options:

## UART (Recommended)

UART is used for this project.

Advantages:

* Simple TX/RX communication
* Easy Linux integration
* Compatible with ROS2 GPS drivers
* Easy debugging through terminal

## I2C

The SAM-M8Q also supports I2C communication.

This is useful when multiple sensors share the same communication bus, but UART is recommended for initial setup.

---

# Wiring Connection

## ROCK 5C 40-Pin Header

Connect the SAM-M8Q as follows:

| SAM-M8Q | ROCK 5C | Purpose    |
| ------- | ------- | ---------- |
| VCC     | Pin 17  | 3.3V Power |
| GND     | Pin 20  | Ground     |
| TX      | Pin 10  | ROCK RX    |
| RX      | Pin 8   | ROCK TX    |

## Important UART Rule

UART communication crosses signals:

```
GPS TX  ---> ROCK RX
GPS RX  ---> ROCK TX
```

Do NOT connect:

```
GPS TX ---> TX
GPS RX ---> RX
```

---

# Initial Power Test

Before connecting UART:

1. Disconnect ROCK 5C power.
2. Connect only:

```
SAM-M8Q VCC -> ROCK Pin 17
SAM-M8Q GND -> ROCK Pin 20
```

3. Power on the ROCK 5C.

The board should boot normally.

If the ROCK 5C fails to boot:

* Disconnect the GPS power.
* Reboot the ROCK 5C.
* Check wiring before reconnecting sensors.
* Reboot the Rock 5C, then plug the power back into the sensor.

---

# Enable UART

Open terminal:

```bash
sudo rsetup
```

Navigate:

```
Overlays
    |
    └── Manage overlays
```

Enable the UART connected to the GPIO header.

Restart:

```bash
sudo reboot
```

---

# Find GPS Serial Port

Check available serial devices:

```bash
sudo dmesg | grep tty
```

Expected output:

```
feb50000.serial: ttyS2
```

The GPS should appear as:

```
/dev/ttyS2
```

Verify:

```bash
ls -l /dev/ttyS2
```

Example:

```
crw-rw---- root dialout
```

---

# Give User Serial Permission

Check groups:

```bash
groups
```

If `dialout` is missing:

```bash
sudo usermod -aG dialout $USER
```

Restart:

```bash
sudo reboot
```

Verify:

```bash
groups
```

The output should include:

```
dialout
```

---

# Testing Raw GPS Data

Set UART speed:

```bash
sudo stty -F /dev/ttyS2 9600
```

Read GPS output:

```bash
cat /dev/ttyS2
```

Expected messages:

```
$GNGGA
$GNRMC
$GPGSV
$GNVTG
```

---

# Understanding GPS Output

Example:

```
$GNGGA,,,,,,0,00,99.99
```

Means:

```
GPS Fix:
No Fix

Satellites:
0
```

The GPS is working, but it has not connected to satellites yet.

---

# Getting Satellite Lock

For first GPS fix:

* Move outdoors
* Place antenna facing the sky
* Avoid metal objects
* Avoid indoor testing

Typical first fix:

```
30 seconds - several minutes
```

Successful fix example:

```
Fix Quality: 1
Satellites: 8
```

---

# Install Python GPS Libraries

Install:

```bash
pip3 install pyserial pynmea2 --break-system-packages
```

---

# GooseBot GPS Reader

Create:

```bash
nano goosebot_gps.py
```

Add your GPS reading script.

The program should output:

```
Latitude
Longitude
Altitude
Satellites
Speed
Heading
Fix Status
```

Run:

```bash
python3 goosebot_gps.py
```

---

# GooseBot Navigation Data

The SAM-M8Q provides:

## Position

```
Latitude
Longitude
Altitude
```

Used for:

* GPS location
* Waypoints
* Mapping

## Movement

```
Speed
Heading
```

Used for:

* Direction of travel
* Velocity estimation

## Reliability

```
Satellite count
Fix status
```

Used for:

* Determining GPS accuracy

---

# Sensor Fusion Plan

The GPS is only one part of GooseBot navigation.

```
                 SAM-M8Q GPS
                      |
                      |
              Global Position
                      |
                      |
ROCK 5C ---- Sensor Fusion ---- Nav2
                      |
          ---------------------
          |                   |
       MPU-6050          Wheel Encoder
       Orientation        Distance
```

GPS answers:

> Where am I?

IMU answers:

> Which direction am I facing?

Encoder answers:

> How far have I moved?

---

# Troubleshooting

## Problem: ROCK 5C does not turn on

### Symptoms

* ROCK 5C does not boot
* No display output
* Board appears stuck

### Solution

1. Disconnect power from all external sensors.

Example:

```
Disconnect:
- SAM-M8Q VCC
- IMU power
- Other GPIO sensors
```

2. Reboot the ROCK 5C.

3. Verify the board boots normally.

4. Reconnect sensors one at a time.

Possible causes:

* Sensor short circuit
* Incorrect power connection
* Incorrect GPIO wiring
* Power rail overload

---

# Problem: Blue LED is solid and ROCK does not boot

### Symptoms

* Blue LED remains solid
* ROCK 5C stuck during startup
* System does not load

### Solution

1. Remove power from connected sensors.

Example:

```
Disconnect sensor VCC lines:
- GPS power
- IMU power
- Other modules
```

2. Restart the ROCK 5C.

3. Confirm the ROCK boots.

4. Reconnect sensors after startup.

Possible causes:

* Sensor pulling down the 3.3V rail
* Incorrect power wiring
* Sensor connected while board is powered
* Short circuit

---

# Problem: GPS Outputs Data but No Location

Example:

```
$GNGGA,,,,,,0,00
```

Meaning:

* UART works
* GPS is powered
* No satellite lock

Solution:

* Move outdoors
* Wait for GPS fix
* Check antenna placement

---

# Problem: Permission Denied on /dev/ttyS2

Example:

```
Permission denied: /dev/ttyS2
```

Solution:

Add user to dialout:

```bash
sudo usermod -aG dialout $USER
```

Reboot.

---

# Problem: No GPS Data

Check:

## 1. Wiring

Correct:

```
GPS TX -> ROCK RX
GPS RX -> ROCK TX
```

## 2. UART device

Check:

```bash
sudo dmesg | grep tty
```

## 3. Baud rate

SAM-M8Q default:

```
9600 baud
```

---

# Recommended GooseBot Sensor Stack

Current:

✅ ROCK 5C
✅ SAM-M8Q GPS
✅ MPU-6050 IMU

Future:

⬜ Wheel encoders
⬜ ToF obstacle sensors
⬜ Camera/LiDAR
⬜ ROS2 Nav2

---

# Final Goal

The completed navigation system will combine:

```
GPS
 |
Global Position

+
 
IMU
 |
Orientation

+

Wheel Encoder
 |
Distance Traveled

=

Robot Position Estimate
```

This allows GooseBot to navigate autonomously using ROS2 and Nav2.
