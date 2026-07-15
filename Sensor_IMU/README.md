# ROCK 5C MPU6050 IMU Setup Guide

A step-by-step guide for connecting and reading a **GY-521 MPU6050 6-Axis IMU** with a **Radxa ROCK 5C running Debian 12**.

The MPU6050 provides:

- 3-axis accelerometer
- 3-axis gyroscope
- Temperature sensor
- I2C communication

---

# 1. Hardware Required

## Components

- Radxa ROCK 5C
- GY-521 MPU6050 Module
- Jumper wires
- Computer/SSH access to ROCK 5C

---

# 2. MPU6050 Pin Connections

The ROCK 5C uses a 40-pin GPIO header.

We will use the second I2C bus to avoid interfering with an existing PCA9685 PWM servo controller.

## Wiring

| MPU6050 | ROCK 5C Pin | Function |
|---|---|---|
| VCC | Pin 1 | 3.3V Power |
| GND | Pin 9 | Ground |
| SDA | Pin 27 | I2C Data |
| SCL | Pin 28 | I2C Clock |

Connection:

```
MPU6050        ROCK 5C

VCC  --------> Pin 1 (3.3V)

GND  --------> Pin 9 (GND)

SDA  --------> Pin 27 (I2C SDA)

SCL  --------> Pin 28 (I2C SCL)
```

---

# 3. Enable I2C on ROCK 5C

Check available I2C devices:

```bash
ls /dev/i2c*
```

Expected:

```
/dev/i2c-0
/dev/i2c-2
/dev/i2c-6
/dev/i2c-7
/dev/i2c-8
```

---

# 4. Check I2C Configuration

View enabled overlays:

```bash
cat /boot/extlinux/extlinux.conf
```

Example:

```
fdtoverlays /boot/dtbo/rk3588-i2c6-m0.dtbo
```

The MPU6050 is connected to:

```
i2c-6
```

---

# 5. Install I2C Tools

Install required packages:

```bash
sudo apt update

sudo apt install i2c-tools python3-smbus2 -y
```

---

# 6. Detect MPU6050

Scan the I2C bus:

```bash
sudo i2cdetect -y 6
```

A working MPU6050 should appear:

```
60: -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
68: UU
```

The address:

```
0x68
```

is the MPU6050 default address.

---

# 7. Create Python IMU Program

Create file:

```bash
nano imu_angle.py
```

Paste the Python program.

The program provides:

- Accelerometer magnitude
- Roll angle
- Pitch angle
- Yaw rotation
- Gyroscope turn rate
- Tare function

Save:

```
CTRL + O
ENTER
CTRL + X
```

---

# 8. Run the IMU

Start the program:

```bash
python3 imu_angle.py
```

Example output:

```
----------------------------

Acceleration Total: 0.998 g

Roll : 0.25 deg

Pitch: -1.10 deg

Yaw : 15.40 deg

Turn Rate: 20.5 deg/s
```

---

# 9. Tare / Zero the Angle

Place the robot/car in the starting position.

Press:

```
t
ENTER
```

The IMU will reset:

```
Roll  = 0°
Pitch = 0°
Yaw   = 0°
```

Future movement is measured relative to this position.

---

# 10. Understanding Sensor Units

## Accelerometer

Output:

```
g-force
```

Example:

```
Z = 1.0g
```

means gravity is pointing through the Z-axis.

Normally:

```
Total Gravity ≈ 1g
```

---

## Gyroscope

Output:

```
degrees per second (deg/s)
```

Example:

```
Z = 90 deg/s
```

means the sensor is rotating 90 degrees every second around Z.

---

## Angle Output

Output:

```
degrees
```

Example:

```
Yaw = 45°
```

means the robot rotated 45 degrees from the tare position.

---

# 11. Important MPU6050 Limitations

## Roll and Pitch

Good accuracy because gravity provides a reference.

Example:

```
Robot tilted 20°
```

The accelerometer can detect it.

---

## Yaw

Yaw will drift over time.

Reason:

The MPU6050 has:

✅ Accelerometer  
✅ Gyroscope  

but:

❌ No magnetometer (compass)

The gyro measures rotation but has no absolute heading reference.

---

# 12. For Autonomous RC Car Use

Recommended sensor setup:

```
                 ROCK 5C

                    |
        -------------------------
        |           |           |
       GPS       MPU6050    Wheel Encoder
        |           |           |
     Position     Turning    Distance
```

Sensor roles:

| Sensor | Purpose |
|-|-|
| GPS | Global position |
| MPU6050 | Short-term turning |
| Wheel encoder | Distance traveled |
| Camera | Lane detection |

---

# 13. Future Improvements

For better heading accuracy replace MPU6050 with:

- BNO055
- BNO085
- MPU9250
- ICM-20948

These include a magnetometer or onboard sensor fusion.

---

# Troubleshooting

## Error:

```
No such device or address
```

Check:

- SDA/SCL wiring
- Correct I2C bus number
- Power connection
- MPU6050 address

---

## Error:

```
No module named smbus
```

Install:

```bash
sudo apt install python3-smbus2 -y
```

---

## Error:

```
No module named mpu6050
```

The setup does not require the mpu6050 Python package.

It communicates directly through I2C using:

```
smbus2
```

---

# Completed Setup

At this point:

✅ MPU6050 connected  
✅ I2C communication working  
✅ Accelerometer reading  
✅ Gyroscope reading  
✅ Angle tracking  
✅ Ready for robotics integration
