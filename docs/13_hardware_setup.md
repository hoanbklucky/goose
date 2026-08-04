# Hardware Setup Documentation

This document contains the hardware configuration for Goosebot.

It includes:

- Main computer
- Power system
- Sensors
- Motor system
- Wiring information

The purpose is to allow another person to rebuild the same hardware setup.

---

# 1. Main Computer

## Single Board Computer

```
Radxa ROCK 5C
```

Operating System:

```
Debian 12 KDE
```

ROS2:

```
ROS2 Humble
```

---

# ROCK 5C Responsibilities

The ROCK 5C handles:

- ROS2 nodes
- Sensor processing
- Motor control
- Localization
- Future AI vision processing

---

# 2. Power System

## Important Voltage Notes

The ROCK 5C requires:

```
5V power
```

Do not connect unknown voltage sources directly.

---

## Sensor Power

Most sensors:

```
3.3V logic
```

Check voltage before connecting.

---

# 3. MPU6050 IMU

## Sensor

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

# Purpose

Provides:

- Angular velocity
- Linear acceleration
- Motion data

ROS2 topic:

```
/imu/data
```

---

# 4. GPS Module

## Sensor

```
SparkFun SAM-M8Q
```

Communication:

```
UART
```

Device:

```
/dev/ttyS4
```

---

# Wiring

| GPS | ROCK 5C |
|-|-|
| TX | Pin 7 |
| RX | Pin 29 |
| GND | GND |
| VCC | 3.3V |

---

# UART Rule

UART crosses:

```
TX → RX

RX → TX
```

---

# GPS Output

Raw:

```
NMEA sentences
```

Example:

```
$GNRMC

$GNGGA
```

ROS2 topic:

```
/fix
```

---

# 5. Motor System

## Motors

```
TT Encoder Motors

6V-9V

1:48 gearbox

150 RPM
```

---

# Motor Driver

```
L298N
```

Responsibilities:

- Direction control
- Motor power switching

---

# Motor Connections

Motor driver receives:

```
PWM signal

Direction signals

Motor power
```

---

# 6. Wheel Encoder

## Encoder Type

```
Hall Effect Quadrature Encoder
```

---

# Encoder Pins

| Encoder | ROCK 5C |
|-|-|
| Left A | Pin 11 |
| Left B | Pin 13 |
| Right A | Pin 15 |
| Right B | Pin 16 |

---

# Calibration

Current values:

Wheel diameter:

```
2.6 inches
```

Counts per revolution:

```
1092
```

---

# Distance Calculation

Wheel circumference:

```
C = πD
```

Distance:

```
distance = counts × distance_per_count
```

---

# Future ROS2 Output

Topic:

```
/odom
```

Message:

```
nav_msgs/Odometry
```

---

# 7. PCA9685 PWM Controller

## Board

```
PCA9685 16 Channel PWM Driver
```

Communication:

```
I2C
```

Address:

```
0x40
```

---

# Purpose

Controls:

- Motor PWM
- Servo signals

---

# I2C Check

Run:

```bash
sudo i2cdetect -y -r BUS_NUMBER
```

Expected:

```
40
```

---

# 8. Ultrasonic Sensor

## Purpose

Obstacle detection.

Future use:

- Collision avoidance
- Emergency stop

---

# Planned ROS2 Topic

```
/ultrasonic_distance
```

---

# 9. Camera System

Planned:

Purpose:

- Lane detection
- Vision navigation
- Object detection

---

# 10. Hardware Layout

Current architecture:

```
                 ROCK 5C

                    |

        ------------------------

        |          |           |

       IMU       GPS       PCA9685

       I2C       UART        I2C


                    |

                    v


                 L298N


                    |

                    v


                 Motors


                    |

                    v


               Wheel Encoders

```

---

# 11. Current Hardware Status

## Working

✅ ROCK 5C  
✅ MPU6050 IMU  
✅ SAM-M8Q GPS  
✅ PCA9685 PWM board  
✅ Encoder hardware  

---

## Software Remaining

⬜ Encoder ROS2 node

⬜ EKF configuration

⬜ Nav2

⬜ SLAM

---

# 12. Important Notes

## GPS

GPS only works properly outdoors.

Indoor:

```
latitude: nan

longitude: nan
```

is expected.

---

## IMU

Current output provides:

```
angular velocity

linear acceleration
```

Orientation estimation will be improved later.

---

## Power

Always verify:

- Voltage
- Ground connection
- Logic levels

before connecting new hardware.
