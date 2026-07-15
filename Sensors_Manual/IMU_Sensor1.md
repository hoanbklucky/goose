# ROCK 5C + MPU6050 IMU Setup Guide (Debian)

This guide explains how to connect and test an **MPU6050 6-axis IMU (3-axis accelerometer + 3-axis gyroscope)** with a **Radxa ROCK 5C running Debian Linux** using I2C.

The MPU6050 provides:

* Acceleration (X, Y, Z)
* Angular velocity (gyro X, Y, Z)
* Temperature
* Orientation estimation (using sensor fusion)

---

# 1. Hardware Required

## Components

* Radxa ROCK 5C
* MPU6050 module
* Jumper wires
* Computer with SSH or terminal access

---

# 2. MPU6050 Pin Connections

The MPU6050 communicates through **I2C**.

Connect:

| MPU6050 | ROCK 5C GPIO Header |
| ------- | ------------------- |
| VCC     | 3.3V  (Either 1 or 17, you can use a breadboard to share)              |
| GND     | GND (Any Black tiles for the pins)                |
| SDA     | GPIO 27 (Pin 27 on Rock)            |
| SCL     | GPIO 28 (Pin 28 on Rock)            |

### Important

The MPU6050 module should be powered with **3.3V** when connected directly to the ROCK 5C.

---

# 3. Enable I2C on ROCK 5C

Check available I2C buses:

```bash
ls /dev/i2c*
```

Example output:

```
/dev/i2c-0
/dev/i2c-2
/dev/i2c-6
/dev/i2c-7
/dev/i2c-8
```

Check I2C adapters:

```bash
sudo i2cdetect -l
```

For GPIO 27/28, the commonly used bus is:

```
i2c-6
```

Test the MPU6050:

```bash
sudo i2cdetect -y 6
```

Expected result:

```
60: -- -- -- -- -- -- 68 -- -- -- --
```

The address:

```
0x68
```

means the MPU6050 is detected.

---

# 4. Install Required Packages

Update packages:

```bash
sudo apt update
```

Install Python I2C support:

```bash
sudo apt install python3-smbus2 -y
```

---

# 5. Create IMU Test Program

Create a Python file:

```bash
nano imu_test.py
```

Paste:

```python
import time
from smbus2 import SMBus

BUS = 6
ADDRESS = 0x68

bus = SMBus(BUS)

# Wake MPU6050
bus.write_byte_data(ADDRESS, 0x6B, 0)

def read_word(reg):
    high = bus.read_byte_data(ADDRESS, reg)
    low = bus.read_byte_data(ADDRESS, reg + 1)

    value = (high << 8) | low

    if value >= 32768:
        value -= 65536

    return value


while True:

    accel_x = read_word(0x3B)
    accel_y = read_word(0x3D)
    accel_z = read_word(0x3F)

    gyro_x = read_word(0x43)
    gyro_y = read_word(0x45)
    gyro_z = read_word(0x47)

    temp = read_word(0x41)/340 + 36.53


    print("--------------------")

    print("Acceleration:")
    print("X:", accel_x/16384, "g")
    print("Y:", accel_y/16384, "g")
    print("Z:", accel_z/16384, "g")

    print("\nGyroscope:")
    print("X:", gyro_x/131, "deg/s")
    print("Y:", gyro_y/131, "deg/s")
    print("Z:", gyro_z/131, "deg/s")

    print("\nTemperature:", round(temp,2),"C")

    time.sleep(1)
```

Save:

```
CTRL + O
ENTER
CTRL + X
```

Run:

```bash
python3 imu_test.py
```

---

# 6. Understanding the Output

Example:

```
Acceleration:
X: -0.04 g
Y: -0.02 g
Z: 0.84 g

Gyroscope:
X: 1.1 deg/s
Y: 0.3 deg/s
Z: 0.8 deg/s
```

## Accelerometer

Unit:

```
g
```

where:

```
1g = Earth's gravity
```

A stationary sensor normally shows approximately:

```
X = 0g
Y = 0g
Z = 1g
```

depending on orientation.

---

## Gyroscope

Unit:

```
degrees/second
```

Example:

```
90 deg/s
```

means the sensor is rotating 90 degrees every second.

A stationary MPU6050 may show small values due to sensor bias.

---

## Temperature

Unit:

```
°C
```

This is the internal temperature of the MPU6050.

---

# 7. Measuring Vehicle Turning (Yaw)

The MPU6050 gyro can measure turning rate.

For a vehicle:

Looking from above:

```
        Front

          ↑

     YAW ROTATION

          ↺
```

The Z-axis gyro measures turning.

Example:

```
Gyro Z = 45 deg/s
```

means the vehicle is rotating 45 degrees per second.

---

# 8. Important: Gyro Drift

The MPU6050 cannot directly know absolute heading.

If you integrate gyro data:

```
angle = angle + gyro_rate * time
```

the error accumulates.

Example:

```
Start:
Yaw = 0°

After several minutes:
Yaw = 20°
```

even though the vehicle did not move.

This is called:

```
gyro drift
```

For accurate heading, combine:

* Gyroscope
* Accelerometer
* Magnetometer (compass)

using sensor fusion.

Examples:

* MPU6050 + complementary filter
* MPU6050 + Kalman filter
* MPU9250 (includes magnetometer)

---

# 9. Troubleshooting

## Problem: No /dev/i2c devices

Check:

```bash
ls /dev/i2c*
```

If nothing appears:

* I2C overlay is not enabled
* Check `/boot/extlinux/extlinux.conf`
* Confirm I2C overlay is loaded

---

## Problem: i2cdetect shows nothing

Example:

```
-- -- -- --
```

Check:

### Wiring

Verify:

```
VCC -> 3.3V
GND -> GND
SDA -> GPIO27
SCL -> GPIO28
```

### Bad sensor

A defective MPU6050 can appear as:

* Device detected sometimes
* Read errors
* Incorrect values

Replacing the module fixed this issue.

---

## Problem:

```
OSError: [Errno 6] No such device or address
```

Cause:

* Wrong I2C bus
* Wrong address
* Sensor not responding

Check:

```bash
sudo i2cdetect -y 6
```

Look for:

```
68
```

---

## Problem:

```
ModuleNotFoundError: No module named smbus
```

Install:

```bash
sudo apt install python3-smbus2 -y
```

---

## Problem:

```
externally-managed-environment
```

When using pip on Debian:

Avoid:

```bash
sudo pip3 install
```

Use:

```bash
sudo apt install python3-smbus2
```

or create a virtual environment.

---

## Problem:

```
python3: SyntaxError
```

Cause:

Arduino C++ code was pasted into Python.

Python files use:

```
.py
```

Arduino files use:

```
.ino
```

They are not interchangeable.

---

# 10. Future Improvements for Robotics

For an autonomous RC car, the MPU6050 can provide:

✅ Vehicle rotation rate
✅ Tilt angle
✅ Acceleration changes
✅ Motion detection

For navigation, combine with:

* GPS module
* Wheel encoders
* Camera
* Magnetometer
* SLAM algorithms

The IMU should be treated as a motion sensor, not a standalone GPS replacement.

---

# Summary

Successful setup:

```
ROCK 5C
 |
 |-- I2C
 |
MPU6050
 |
 |-- Accelerometer
 |-- Gyroscope
 |-- Temperature
```

Test command:

```bash
python3 imu_test.py
```

Expected stationary readings:

```
Acceleration:
X ≈ 0g
Y ≈ 0g
Z ≈ 1g

Gyroscope:
X/Y/Z ≈ 0 deg/s
```

The MPU6050 is now ready for robotics applications.

```
```




