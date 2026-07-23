# SparkFun SAM-M8Q GPS Setup with Radxa ROCK 5C

## GooseBot Autonomous Navigation Sensor Guide

This guide explains how to connect and configure the **SparkFun SAM-M8Q GNSS GPS module** with the **Radxa ROCK 5C** for the GooseBot autonomous navigation project.

The goal is to obtain:

- Latitude
- Longitude
- Altitude
- GPS fix status
- Number of satellites
- Ground speed
- Heading direction
- Timestamp

The SAM-M8Q communicates with the ROCK 5C using **UART serial communication**.

---

# Hardware Required

## Components

- Radxa ROCK 5C
- SparkFun SAM-M8Q GNSS GPS Module
- Jumper wires
- GPS antenna
- 3.3V power connection (5V works as well but recommended 3.3V)

---

# SAM-M8Q Communication Interfaces

The SAM-M8Q provides multiple communication methods.

## UART (Recommended)

UART is used for this project.

Advantages:

- Simple TX/RX communication
- Easy Linux integration
- Compatible with ROS2 GPS drivers
- Easy debugging using terminal commands

## I2C

The SAM-M8Q also supports I2C communication.

I2C is useful when multiple sensors share the same communication bus, but UART is recommended for initial GPS setup.

---

# UART4-M2 Connection

For GooseBot, UART4-M2 is used.

## ROCK 5C 40-Pin Header Wiring

| SAM-M8Q | ROCK 5C Pin | Function |
|---|---|---|
| VCC | Pin 17 | 3.3V Power |
| GND | Pin 20 | Ground |
| TX | Pin 29 | UART4 RX |
| RX | Pin 7 | UART4 TX |

## UART Rule

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
SAM-M8Q VCC -> ROCK 5C Pin 17
SAM-M8Q GND -> ROCK 5C Pin 20
```

3. Power on the ROCK 5C.

The board should boot normally.

## If ROCK 5C does not boot:

1. Disconnect GPS power.

Disconnect:

```
GPS VCC
Other sensor VCC lines
```

2. Restart the ROCK 5C.

3. Confirm the board boots.

4. Reconnect sensors one at a time.

Possible causes:

- Sensor short circuit
- Incorrect wiring
- 3.3V rail overload
- Power connection issue

---

# Blue LED Solid / Boot Failure

## Symptoms

- ROCK 5C does not display
- Blue LED remains solid
- Board is stuck during startup

## Solution

1. Remove power from sensors.

Example:

```
Disconnect:
- SAM-M8Q VCC
- IMU power
- Other GPIO sensors
```

2. Restart the ROCK 5C.

3. Wait until the system boots.

4. Reconnect sensor power.

Possible causes:

- Sensor pulling down the 3.3V rail
- Sensor connected during startup
- Incorrect power wiring
- Short circuit

---

# Enable UART4-M2

Open:

```bash
sudo rsetup
```

Navigate:

```
Overlays
 |
 └── Manage overlays
```

Enable:

```
UART4-M2
```

Disable any conflicting UART overlays.

Restart:

```bash
sudo reboot
```

---

# Verify UART4

Check available serial devices:

```bash
ls /dev/ttyS*
```

Expected:

```
/dev/ttyS4
```

Check kernel:

```bash
sudo dmesg | grep tty
```

Expected:

```
ttyS4
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

# Test Raw GPS Data

The SAM-M8Q default baud rate is:

```
9600 baud
```

Configure UART:

```bash
sudo stty -F /dev/ttyS4 9600
```

Read GPS output:

```bash
cat /dev/ttyS4
```

Expected NMEA messages:

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

The GPS is communicating, but it has not connected to satellites.

---

# Getting Satellite Lock

For first GPS fix:

- Move outdoors
- Place antenna facing the sky
- Avoid metal objects
- Avoid indoor testing

Typical first fix:

```
30 seconds - several minutes
```

Successful fix:

```
Fix Quality: 1
Satellites: 5+
```

---

# Install Python GPS Libraries

Debian 12 uses PEP 668 protection.

Install:

```bash
pip3 install pyserial pynmea2 --break-system-packages
```

---

# Create GPS Reader

Create file:

```bash
nano goosebot_gps.py
```

The script should read:

- Latitude
- Longitude
- Altitude
- Satellites
- Speed
- Heading
- Fix Status

Run:

```bash
python3 goosebot_gps.py
```

---

# SAM-M8Q Data Information

| Data | NMEA Sentence |
|-|-|
| Latitude | GGA/RMC |
| Longitude | GGA/RMC |
| Altitude | GGA |
| Satellite Count | GGA |
| Speed | RMC |
| Heading | RMC |
| Time | GGA/RMC |

---

# Important GPS Heading Limitation

The SAM-M8Q heading is:

```
Course over Ground
```

This means:

- It calculates direction while moving.
- It does not know the robot's physical orientation while stationary.

Example:

Robot stopped:

```
Heading = unreliable
```

Robot moving:

```
Heading = useful
```

For robot orientation:

```
MPU-6050 IMU = Robot rotation

SAM-M8Q GPS = Global position

Wheel Encoder = Distance traveled
```

---

# GooseBot Sensor Fusion

The complete navigation system:

```
                 SAM-M8Q GPS
                       |
                       |
              Latitude / Longitude
                       |
                       |
               robot_localization
                       |
                       |
                 EKF Fusion
                       |
                       |
                     Nav2


MPU-6050 IMU
      |
      |
Orientation
      |
      |
robot_localization


Wheel Encoder
      |
      |
Distance / Odometry
      |
      |
robot_localization
```

GPS answers:

```
Where am I?
```

IMU answers:

```
Which direction am I facing?
```

Encoder answers:

```
How far did I move?
```

---

# Troubleshooting

## GPS Outputs Data But No Location

Example:

```
$GNGGA,,,,,,0,00
```

Meaning:

- UART works
- GPS has power
- No satellite lock

Solution:

- Move outdoors
- Check antenna
- Wait for GPS fix

---

## Permission Denied

Example:

```
Permission denied: /dev/ttyS4
```

Solution:

```bash
sudo usermod -aG dialout $USER
```

Restart:

```bash
sudo reboot
```

---

## No GPS Data

Check:

### Wiring

Correct:

```
GPS TX -> ROCK RX
GPS RX -> ROCK TX
```

### UART

Check:

```bash
sudo dmesg | grep tty
```

### Baud Rate

SAM-M8Q:

```
9600 baud
```

---

# Recommended GooseBot Sensor Stack

Current:

✅ ROCK 5C  
✅ SparkFun SAM-M8Q GPS  
✅ MPU-6050 IMU  

Future:

⬜ Wheel Encoders  
⬜ ToF Collision Sensors  
⬜ Camera/LiDAR  
⬜ ROS2 Nav2  

---

# Final Goal

The completed GooseBot navigation system:

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
Distance

=

Robot Position Estimate
```

This allows GooseBot to navigate autonomously using:

- ROS2
- robot_localization
- Nav2
- Sensor Fusion
