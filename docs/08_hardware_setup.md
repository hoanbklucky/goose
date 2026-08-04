# Hardware Setup Documentation

This document covers the physical hardware setup for Goosebot.

The robot uses:

- Radxa ROCK 5C as the main computer
- SparkFun SAM-M8Q GPS
- MPU6050 GY-521 IMU
- PCA9685 PWM controller
- L298N motor driver
- TT encoder motors
- Wheel encoders

---

# 1. Main Computer

## Radxa ROCK 5C

The ROCK 5C runs:

```
Debian 12
ROS2 Humble
Python
```

Responsibilities:

- Runs ROS2
- Processes sensor data
- Runs motor control
- Performs localization

---

# 2. Power System

## Power Requirements

The ROCK 5C requires:

- 5V power input
- Stable current supply

Sensors should use appropriate voltage levels.

---

# 3. GPIO Pin Reference

Important pins used during development:

| Function | ROCK 5C Pin |
|-|-|
| UART TX | Pin 7 |
| UART RX | Pin 29 |
| I2C SDA | Pin 27 |
| I2C SCL | Pin 28 |

---

# 4. GPS Setup

## SparkFun SAM-M8Q

Communication:

```
UART
```

Device:

```
/dev/ttyS4
```

---

## Wiring

| SAM-M8Q | ROCK 5C |
|-|-|
| TX | Pin 7 |
| RX | Pin 29 |
| GND | GND |
| VCC | 3.3V |

Important:

UART uses crossed communication:

```
GPS TX → ROCK RX

GPS RX → ROCK TX
```

---

# 5. GPS Testing

Check UART:

```bash
ls /dev/ttyS*
```

Expected:

```
/dev/ttyS4
```

---

Test raw GPS output:

```bash
cat /dev/ttyS4
```

Expected:

```
$GNRMC
$GNGGA
$GPGSV
```

---

Test ROS2:

```bash
ros2 topic echo /fix --once
```

Working outdoors:

```
latitude:
longitude:
altitude:
```

---

# 6. MPU6050 IMU

## Sensor

Model:

```
GY-521 MPU6050
```

Communication:

```
I2C
```

Address:

```
0x68
```

---

# Wiring

| MPU6050 | ROCK 5C |
|-|-|
| VCC | 3.3V |
| GND | GND |
| SDA | Pin 27 |
| SCL | Pin 28 |

---

# Testing I2C

Check buses:

```bash
i2cdetect -l
```

Scan:

```bash
sudo i2cdetect -y -r BUS_NUMBER
```

Expected:

```
68
```

---

# ROS2 IMU Test

Run:

```bash
ros2 topic echo /imu/data --once
```

Expected:

```
angular_velocity

linear_acceleration
```

Example:

```
linear_acceleration:
 z: ~9.8
```

Gravity confirms the accelerometer is working.

---

# 7. PCA9685 PWM Controller

## Purpose

The PCA9685 controls:

- Motor PWM
- Servo PWM

Communication:

```
I2C
```

Address:

```
0x40
```

---

# I2C Check

Scan:

```bash
sudo i2cdetect -y -r 6
```

Expected:

```
40
```

---

# 8. Motor Driver

## L298N

Purpose:

Controls:

- Motor direction
- Motor power

Connections:

```
ROCK 5C

     |

     v

PCA9685

     |

     v

L298N

     |

     v

DC Motors
```

---

# 9. Encoder Motors

Motor type:

```
TT Encoder Motor
1:48 Gear Ratio
150 RPM
```

Encoder provides:

- Rotation count
- Wheel speed
- Distance traveled

---

# Encoder Pins

Current wiring:

| Encoder | ROCK 5C |
|-|-|
| Left A | Pin 11 |
| Left B | Pin 13 |
| Right A | Pin 15 |
| Right B | Pin 16 |

---

# Encoder Calibration

Current values:

Wheel diameter:

```
2.6 inches
```

Encoder counts:

```
1092 counts/revolution
```

Distance calculation:

```
distance =
wheel revolutions
×
wheel circumference
```

---

# 10. Ultrasonic Sensor

Purpose:

Obstacle detection.

Communication:

```
GPIO Trigger/Echo
```

Used for:

- Collision avoidance
- Short distance measurement

---

# 11. Hardware Testing Order

When rebuilding Goosebot:

Follow this order:

---

## Step 1

Power ROCK 5C only.

Verify:

```bash
hostname
```

---

## Step 2

Connect IMU.

Verify:

```bash
i2cdetect
```

Expected:

```
68
```

---

## Step 3

Connect GPS.

Verify:

```bash
ls /dev/ttyS*
```

Then:

```bash
cat /dev/ttyS4
```

---

## Step 4

Connect PWM controller.

Verify:

```
40
```

appears on I2C.

---

## Step 5

Connect motors and encoders.

Test encoder counts before running autonomous code.

---

# 12. Current Hardware Status

## Working

✅ ROCK 5C  
✅ MPU6050 IMU  
✅ SAM-M8Q GPS  
✅ ROS2 communication  
✅ Encoder reading  
✅ PCA9685 detected  

---

# 13. Final Hardware Architecture

```
                 GPS
                  |
                  |
               UART4
                  |
                  v


               ROCK 5C


                  ^
                  |
              I2C Bus


        +---------+---------+

        |                   |

      MPU6050          PCA9685

        |                   |

        |                L298N

        |                   |

        |                Motors

        |

     IMU Data


        |

        v

 ROS2 robot_localization

        |

        v

 Navigation
```

---

# Goal

The hardware layer provides reliable sensor data to ROS2.

The next steps are:

1. Create ROS2 sensor packages
2. Publish encoder odometry
3. Configure EKF
4. Connect Nav2
