# Goosebot ROS2 Setup (Sensor Publisher Preparation)

This section prepares Goosebot to publish sensor data into ROS2.

Current hardware:

- Rock 5C
- ROS2 Humble (source build)
- MPU6050 IMU
- GPS module
- Wheel encoders

The goal is to convert:

```
Raw Sensor Python Code
          |
          v
      ROS2 Publisher
          |
          v
 ROS2 Topics (/imu/data, /gps/fix, /odom)
          |
          v
 robot_localization EKF
          |
          v
        Nav2
```

---

# 1. Activate ROS2 Environment

Because ROS2 was built from source, activate it manually:

```bash
source ~/ros2_humble/install/setup.bash
```

Verify ROS2:

```bash
echo $ROS_DISTRO
```

Expected:

```
humble
```

Check ROS2:

```bash
ros2 topic list
```

Expected:

```
/parameter_events
/rosout
```

---

# 2. Fix User PATH

ROS tools installed through pip may be located in:

```
~/.local/bin
```

Add this permanently:

```bash
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
```

Reload:

```bash
source ~/.bashrc
```

---

# 3. Install rosdep

Debian 12 does not provide ROS packages through apt.

Install using pip:

```bash
pip3 install rosdep --break-system-packages
```

Check:

```bash
rosdep --version
```

Expected:

```
0.26.0
```

Initialize:

```bash
sudo /home/radxa/.local/bin/rosdep init
```

Update:

```bash
rosdep update
```

---

# 4. Install Colcon Build Tools

Check if colcon exists:

```bash
colcon
```

If missing:

```bash
pip3 install colcon-common-extensions --break-system-packages
```

Test:

```bash
colcon version-check
```

---

# 5. Create Goosebot Sensor Package

Go to ROS2 source folder:

```bash
cd ~/ros2_humble/src
```

Create package:

```bash
ros2 pkg create goosebot_sensors \
--build-type ament_python \
--dependencies rclpy sensor_msgs std_msgs
```

Package structure:

```
ros2_humble
|
└── src
    |
    └── goosebot_sensors
        |
        ├── package.xml
        ├── setup.py
        |
        └── goosebot_sensors
            |
            └── __init__.py
```

---

# 6. Build ROS2 Workspace

Go to workspace:

```bash
cd ~/ros2_humble
```

Source ROS2:

```bash
source ~/ros2_humble/install/setup.bash
```

Build:

```bash
colcon build --symlink-install --parallel-workers 2
```

The `--parallel-workers 2` option is recommended for the Rock 5C to reduce RAM usage.

---

# 7. Source New Workspace

After building:

```bash
source ~/ros2_humble/install/setup.bash
```

Check package:

```bash
ros2 pkg list | grep goosebot
```

Expected:

```
goosebot_sensors
```

---

# 8. Planned Sensor Topics

After adding publishers, Goosebot will publish:

## IMU

Message:

```
sensor_msgs/msg/Imu
```

Topic:

```
/imu/data
```

Data:

```
orientation
angular velocity
linear acceleration
```

---

## GPS

Message:

```
sensor_msgs/msg/NavSatFix
```

Topic:

```
/gps/fix
```

Data:

```
latitude
longitude
altitude
```

---

## Wheel Encoder

Message:

```
nav_msgs/msg/Odometry
```

Topic:

```
/wheel/odom
```

Data:

```
distance traveled
velocity
robot rotation
```

---

# 9. Final Sensor Fusion Architecture

```
             GPS
              |
              v
          /gps/fix


             IMU
              |
              v
          /imu/data


          Encoders
              |
              v
        /wheel/odom


              |
              v

     robot_localization EKF

              |
              v

       /odometry/filtered

              |
              v

             Nav2
```

---

# Next Step

Create:

```
goosebot_sensors/imu_publisher.py
```

and convert the existing MPU6050 Python script into a ROS2 publisher.
