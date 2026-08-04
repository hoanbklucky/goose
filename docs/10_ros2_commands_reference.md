# ROS2 Commands Reference

This document contains the main ROS2 commands used while developing Goosebot.

It is designed as a quick reference for:

- Building ROS2 packages
- Checking nodes
- Checking topics
- Debugging sensors
- Running hardware drivers

---

# 1. ROS2 Workspace Commands

## Enter Workspace

```bash
cd ~/ros2_humble
```

---

## Build Workspace

Build everything:

```bash
colcon build
```

Recommended:

```bash
colcon build --symlink-install
```

---

## Build One Package

Example:

```bash
colcon build \
--symlink-install \
--packages-select package_name
```

Example:

```bash
colcon build \
--symlink-install \
--packages-select nmea_navsat_driver
```

---

## Source Workspace

After building:

```bash
source ~/ros2_humble/install/setup.bash
```

Without sourcing:

- ROS2 cannot find new packages
- Nodes will not appear

---

# 2. Package Commands

## List Installed Packages

```bash
ros2 pkg list
```

---

Search packages:

```bash
ros2 pkg list | grep package_name
```

Examples:

```bash
ros2 pkg list | grep imu
```

```bash
ros2 pkg list | grep robot_localization
```

---

## Package Information

```bash
ros2 pkg info package_name
```

Example:

```bash
ros2 pkg info robot_localization
```

---

# 3. Node Commands

## List Running Nodes

```bash
ros2 node list
```

Example:

```
/mpu6050_node
/nmea_navsat_driver
```

---

## Node Information

```bash
ros2 node info node_name
```

Example:

```bash
ros2 node info /mpu6050_node
```

Shows:

- Published topics
- Subscribed topics
- Services

---

# 4. Topic Commands

## List Topics

```bash
ros2 topic list
```

---

Example Goosebot topics:

```
/imu/data
/fix
```

Future:

```
/odom
/odometry/filtered
```

---

## Topic Information

```bash
ros2 topic info /topic_name
```

Example:

```bash
ros2 topic info /imu/data
```

Shows:

- Message type
- Publisher count
- Subscriber count

---

## Read Topic Data

```bash
ros2 topic echo /topic_name
```

Example:

```bash
ros2 topic echo /imu/data
```

---

Read one message:

```bash
ros2 topic echo /imu/data --once
```

---

# 5. Message Types

Find topic type:

```bash
ros2 topic type /topic_name
```

Example:

```bash
ros2 topic type /imu/data
```

Result:

```
sensor_msgs/msg/Imu
```

---

Show message structure:

```bash
ros2 interface show sensor_msgs/msg/Imu
```

---

# 6. Sensor Testing Commands

---

# IMU Test

Check:

```bash
ros2 topic echo /imu/data --once
```

Expected:

```
angular_velocity

linear_acceleration
```

---

# GPS Test

Check:

```bash
ros2 topic echo /fix --once
```

Expected outdoors:

```
latitude

longitude

altitude
```

---

# UART Testing

List serial devices:

```bash
ls /dev/ttyS*
```

---

Read GPS directly:

```bash
cat /dev/ttyS4
```

Expected:

```
$GNRMC
$GNGGA
```

---

Set UART baud:

```bash
sudo stty -F /dev/ttyS4 9600 cs8 -cstopb -parenb
```

---

# 7. Launch Commands

Run launch file:

```bash
ros2 launch package_name launch_file.py
```

Example:

```bash
ros2 launch goosebot_bringup robot.launch.py
```

---

# 8. Parameter Commands

Show parameters:

```bash
ros2 param list
```

---

Node parameters:

```bash
ros2 param list node_name
```

---

Get parameter:

```bash
ros2 param get node_name parameter
```

---

Set parameter:

```bash
ros2 param set node_name parameter value
```

---

# 9. Recording Data

ROS2 bag records sensor data.

Record everything:

```bash
ros2 bag record -a
```

---

Record specific topics:

Example:

```bash
ros2 bag record \
/imu/data \
/fix
```

---

Play recording:

```bash
ros2 bag play bag_name
```

Useful for:

- Testing EKF
- Debugging sensors
- Replaying drives

---

# 10. ROS2 Graph Visualization

Generate graph:

```bash
ros2 run rqt_graph rqt_graph
```

Shows:

```
Sensor Nodes

      |

      v

robot_localization

      |

      v

Navigation
```

---

# 11. Debugging Commands

## Check Environment

```bash
echo $ROS_DISTRO
```

Expected:

```
humble
```

---

## Check ROS2 Installation

```bash
ros2 doctor
```

---

## Check Running Processes

```bash
ps aux | grep ros
```

---

## Check Serial Usage

```bash
sudo lsof /dev/ttyS4
```

---

# 12. Common Build Problems

## Package Not Found

Example:

```
package not found
```

Fix:

```bash
source ~/ros2_humble/install/setup.bash
```

---

## Build Does Not Detect Package

Run:

```bash
colcon list
```

Confirm package appears.

---

## Clean Build

If corrupted:

```bash
rm -rf build install log
```

Then:

```bash
colcon build
```

---

# 13. Goosebot Current Commands

## Start IMU

```bash
ros2 run mpu6050_driver mpu6050_node
```

---

## Start GPS

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

---

## Check Nodes

```bash
ros2 node list
```

Current:

```
/mpu6050_node
/nmea_navsat_driver
```

---

## Check Topics

```bash
ros2 topic list
```

Current:

```
/imu/data
/fix
```

---

# 14. Development Workflow

Every coding session:

## 1. Enter workspace

```bash
cd ~/ros2_humble
```

---

## 2. Build changes

```bash
colcon build --symlink-install
```

---

## 3. Source

```bash
source install/setup.bash
```

---

## 4. Test nodes

```bash
ros2 node list
```

---

## 5. Test topics

```bash
ros2 topic list
```

---

# Goal

These commands provide everything needed to:

- Build ROS2 packages
- Test sensors
- Debug problems
- Prepare Goosebot for autonomous navigation
