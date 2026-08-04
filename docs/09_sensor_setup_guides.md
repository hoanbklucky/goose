# Sensor Setup Guides

This document explains how to install, configure, and test each sensor used by Goosebot in ROS2 Humble.

Sensors covered:

- MPU6050 IMU
- SparkFun SAM-M8Q GPS
- Wheel Encoder
- PCA9685 PWM Controller

The goal is to make the setup reproducible for someone starting from a fresh ROCK 5C.

---

# 1. ROS2 Environment Setup

Before running any ROS2 node:

```bash
source ~/ros2_humble/install/setup.bash
```

Check ROS2:

```bash
ros2 --version
```

Check available topics:

```bash
ros2 topic list
```

---

# 2. MPU6050 IMU Setup

## Hardware

Sensor:

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

# Check I2C Connection

Find I2C buses:

```bash
i2cdetect -l
```

Scan the correct bus:

```bash
sudo i2cdetect -y -r BUS_NUMBER
```

Expected:

```
68
```

---

# Running IMU Node

Start the IMU node:

```bash
ros2 run mpu6050_driver mpu6050_node
```

---

# Verify Data

Check topic:

```bash
ros2 topic echo /imu/data --once
```

Expected:

```
sensor_msgs/msg/Imu
```

Example:

```
angular_velocity:
linear_acceleration:
```

A stationary sensor should show:

```
z acceleration ≈ 9.8 m/s²
```

because gravity is detected.

---

# 3. GPS Setup

## Hardware

GPS:

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

UART must cross:

```
GPS TX → ROCK RX

GPS RX → ROCK TX
```

---

# Check Serial Device

```bash
ls -l /dev/ttyS4
```

Expected:

```
/dev/ttyS4
```

---

# Test Raw GPS Output

Set baud rate:

```bash
sudo stty -F /dev/ttyS4 9600 cs8 -cstopb -parenb
```

Read data:

```bash
cat /dev/ttyS4
```

Expected:

```
$GNRMC
$GNGGA
$GNGSA
$GPGSV
```

---

# Install NMEA Driver

Go to ROS2 source folder:

```bash
cd ~/ros2_humble/src
```

Clone ROS2 version:

```bash
git clone -b ros2 https://github.com/ros-drivers/nmea_navsat_driver.git
```

Build:

```bash
cd ~/ros2_humble

colcon build \
--symlink-install \
--packages-select nmea_navsat_driver
```

Source:

```bash
source ~/ros2_humble/install/setup.bash
```

---

# Run GPS Node

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

---

# Verify GPS Topic

Check:

```bash
ros2 topic list
```

Expected:

```
/fix
```

---

Test:

```bash
ros2 topic echo /fix --once
```

Outdoor result:

```
latitude:
longitude:
altitude:
```

Indoor:

```
nan
```

is expected because GPS cannot receive satellites.

---

# 4. Wheel Encoder Setup

## Hardware

Motor:

```
TT Encoder Motor
1:48 Gearbox
```

Encoder:

```
Hall effect quadrature encoder
```

---

# Wiring

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

Counts per revolution:

```
1092
```

Wheel circumference:

```
diameter × π
```

Distance:

```
(distance per count)
×
(number of counts)
```

---

# Encoder Testing

Before ROS2 integration:

Run encoder test script:

```bash
python encoder_test.py
```

Expected:

```
Left encoder: changing
Right encoder: changing
```

---

# Future ROS2 Encoder Node

The encoder must publish:

Message:

```
nav_msgs/Odometry
```

Topic:

```
/odom
```

Required:

```
x position

y position

heading

linear velocity

angular velocity
```

---

# 5. PCA9685 PWM Setup

## Purpose

Controls:

- Motor PWM
- Servo signals

Communication:

```
I2C
```

Address:

```
0x40
```

---

# Check Device

Scan:

```bash
sudo i2cdetect -y -r BUS_NUMBER
```

Expected:

```
40
```

---

# Python Test

Install:

```bash
pip install adafruit-circuitpython-pca9685
```

Test:

```python
from adafruit_pca9685 import PCA9685
```

---

# 6. Sensor Startup Order

Recommended startup:

## 1. Start ROS2

```bash
source ~/ros2_humble/install/setup.bash
```

---

## 2. Start IMU

```bash
ros2 run mpu6050_driver mpu6050_node
```

Verify:

```bash
ros2 topic echo /imu/data --once
```

---

## 3. Start GPS

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

Verify:

```bash
ros2 topic echo /fix --once
```

---

## 4. Start Encoder

Future:

```bash
ros2 run goosebot_sensors encoder_node
```

---

# 7. Current Sensor Status

Completed:

✅ MPU6050 publishing `/imu/data`  
✅ SAM-M8Q publishing `/fix` outdoors  
✅ robot_localization installed  

Remaining:

⬜ Encoder ROS2 odometry  
⬜ EKF configuration  
⬜ Nav2 integration  

---

# Final Sensor Flow

```
MPU6050

   |
   v

/imu/data


GPS

   |
   v

/fix


Encoder

   |
   v

/odom



       |
       v


robot_localization EKF


       |
       v


/odometry/filtered
```

This is the foundation for autonomous navigation.
