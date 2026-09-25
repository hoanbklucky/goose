# Goosebot ROS2 MPU6050 IMU Publisher Setup

This guide documents the setup of the MPU6050 GY-521 IMU on the Rock 5C and exporting it into ROS2.

The final ROS2 topic created:

```
/imu/data
```

Message type:

```
sensor_msgs/msg/Imu
```

This IMU will later be fused with:

- Wheel encoder odometry (`/odom`)
- GPS (`/gps/fix`)
- `robot_localization` EKF
- Nav2 autonomous navigation


---

# 1. Start ROS2 Environment

Every ROS2 terminal must start with:

```bash
source ~/ros2_humble/install/setup.bash
```

Check ROS2:

```bash
echo $ROS_DISTRO
```

Expected:

```
humble
```


---

# 2. Verify Workspace

ROS2 workspace:

```bash
cd ~/ros2_humble
```

Expected structure:

```
ros2_humble
├── src
│   └── goosebot_sensors
├── build
├── install
└── log
```


---

# 3. MPU6050 Wiring

GY-521 MPU6050:

| MPU6050 | Rock 5C |
|---|---|
| VCC | 3.3V |
| GND | GND |
| SDA | Pin 27 |
| SCL | Pin 28 |


Current configuration:

```
I2C Bus: 6
Address: 0x68
```


Verify connection:

```bash
sudo i2cdetect -y 6
```

Expected:

```
68
```


---

# 4. Install Dependencies

Install I2C:

```bash
sudo apt update

sudo apt install python3-smbus2
```


Install quaternion conversion:

```bash
pip3 install transforms3d --break-system-packages
```


---

# 5. Create IMU ROS2 Publisher

Navigate:

```bash
cd ~/ros2_humble/src/goosebot_sensors/goosebot_sensors
```


Create:

```bash
nano imu_publisher.py
```


The publisher must:

- Connect to MPU6050
- Calibrate gyro drift
- Read acceleration
- Read angular velocity
- Calculate quaternion orientation
- Publish ROS2 IMU messages


ROS2 frame:

```python
frame_id = "imu_link"
```


Published data:

```
orientation
angular_velocity
linear_acceleration
```


---

# 6. IMU Covariance Configuration

Covariance values are required for EKF sensor fusion.

Do not leave:

```yaml
- 0.0
```

because the filter interprets it as perfect confidence.


Use:

```python
msg.orientation_covariance = [
    0.05, 0.0, 0.0,
    0.0, 0.05, 0.0,
    0.0, 0.0, 0.10
]


msg.angular_velocity_covariance = [
    0.02, 0.0, 0.0,
    0.0, 0.02, 0.0,
    0.0, 0.0, 0.02
]


msg.linear_acceleration_covariance = [
    0.1, 0.0, 0.0,
    0.0, 0.1, 0.0,
    0.0, 0.0, 0.1
]
```


---

# 7. Create, Build, and Run IMU ROS2 Publisher (One Paste Setup)

Run the following from your Rock 5C terminal:

```bash
cd ~/ros2_humble/src/goosebot_sensors/goosebot_sensors

cat > imu_publisher.py << 'EOF'
# Paste your complete MPU6050 ROS2 publisher code here
EOF


cd ~/ros2_humble

colcon build \
--symlink-install \
--packages-select goosebot_sensors


source ~/ros2_humble/install/setup.bash


ros2 run goosebot_sensors imu_publisher
```

This will:

1. Create the IMU publisher file
2. Build the ROS2 package
3. Load the new ROS2 environment
4. Start publishing IMU data


---

# Code Explanation

## 1. Create the Publisher

The command:

```bash
cat > imu_publisher.py
```

creates a Python file inside:

```
goosebot_sensors/goosebot_sensors/
```

This file contains the ROS2 node that communicates with the MPU6050.


---

## 2. MPU6050 Communication

The publisher connects through:

```
I2C Bus: 6
Address: 0x68
```

using:

```python
SMBus(6)
```

The node wakes the MPU6050:

```python
bus.write_byte_data(
    0x68,
    0x6B,
    0
)
```

because the MPU6050 starts in sleep mode.


---

## 3. Gyroscope Calibration

The IMU gyro has a small bias even when stationary.

The code collects samples:

```python
samples = 500
```

and calculates:

```
gyro offset
```

This reduces yaw drift.


---

## 4. Sensor Data Conversion

The MPU6050 outputs raw values.

The publisher converts:

Accelerometer:

```
raw data
    |
    v
m/s²
```

Gyroscope:

```
raw data
    |
    v
degrees/sec
```

---

## 5. Quaternion Orientation

The IMU calculates:

```
Roll
Pitch
Yaw
```

and converts them into a quaternion:

```python
x
y
z
w
```

ROS2 uses quaternions because they avoid gimbal lock.


---

## 6. ROS2 IMU Message

The node publishes:

```
/imu/data
```

using:

```
sensor_msgs/msg/Imu
```


The message contains:

### Orientation

```yaml
orientation:
 x:
 y:
 z:
 w:
```


### Angular Velocity

```yaml
angular_velocity:
 z:
```


### Linear Acceleration

```yaml
linear_acceleration:
 x:
 y:
 z:
```


---

## 7. Covariance Values

The covariance tells the EKF how much to trust the sensor.

Example:

```python
orientation_covariance = 0.05
```

means:

```
small uncertainty
```

while larger values mean:

```
less trust
```


Without covariance:

```
0.0
```

robot_localization may treat the sensor incorrectly.


---

## 8. Build Process

This command:

```bash
colcon build --symlink-install
```

compiles the ROS2 package.


The package:

```
goosebot_sensors
```

becomes available to ROS2.


---

## 9. Source Environment

After building:

```bash
source ~/ros2_humble/install/setup.bash
```

loads the new package into ROS2.


Without sourcing:

```
ros2 run goosebot_sensors imu_publisher
```

will not find the node.


---

## 10. Verify Output

Open another terminal:

```bash
source ~/ros2_humble/install/setup.bash

ros2 topic list
```

Expected:

```
/imu/data
/parameter_events
/rosout
```


View IMU:

```bash
ros2 topic echo /imu/data
```


Successful output:

```yaml
header:
 frame_id: imu_link

orientation:
 x:
 y:
 z:
 w:

angular_velocity:
 z:

linear_acceleration:
 x:
 y:
 z:
```


---

# Current Status

✅ MPU6050 connected  
✅ ROS2 publisher created  
✅ `/imu/data` active  
✅ Covariance configured  
✅ Ready for sensor fusion  


Next step:

```
Wheel Encoder → /odom Publisher
```

Then:

```
/imu/data + /odom
          |
          v
robot_localization EKF
```
# 11. Verify ROS2 Topic

Open another terminal:

```bash
source ~/ros2_humble/install/setup.bash
```


List topics:

```bash
ros2 topic list
```


Expected:

```
/imu/data
/parameter_events
/rosout
```


---

# 12. View IMU Data

Run:

```bash
ros2 topic echo /imu/data
```


Expected:

```yaml
header:
  frame_id: imu_link

orientation:
  x:
  y:
  z:
  w:

angular_velocity:
  z:

linear_acceleration:
  x:
  y:
  z:
```


Stationary IMU:

```
Acceleration:

x ≈ 0
y ≈ 0
z ≈ 9.81 m/s²
```


---

# Current Status

✅ MPU6050 detected  
✅ I2C working  
✅ ROS2 publisher working  
✅ `/imu/data` created  
✅ Covariance configured  
✅ Ready for EKF fusion  


---

# Navigation Sensor Fusion Pipeline

```
                 MPU6050
                    |
                    |
                /imu/data
                    |
                    |
Wheel Encoder ---> /odom
                    |
                    |
                    v
          robot_localization EKF
                    |
                    |
            /odometry/filtered
                    |
                    |
                  GPS
                    |
                    |
                   Nav2
```


---

# Next Step

Create:

```
Wheel Encoder ROS2 Publisher
```

Publishing:

```
/odom
```

Then fuse:

```
/imu/data + /odom
```

using:

```
robot_localization
```
