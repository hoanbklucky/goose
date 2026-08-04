# Goosebot ROS2 Source Workspace

## Overview

This folder contains the source code for Goosebot's ROS2 packages.

In ROS2, the `src` folder is where all packages are created, edited, and stored.

After development, ROS2 uses these packages to build the robot software system.

---

# ROS2 Workspace Structure

The complete workspace:

```
ros2_humble/

├── src/
│
│   ├── goosebot/
│   │
│   ├── robot_localization/
│   │
│   └── nmea_navsat_driver/
│
├── build/
│
├── install/
│
└── log/
```

---

# Purpose of Each Folder

## src/

Contains:

- ROS2 packages
- Python nodes
- Launch files
- Configuration files
- Robot software

This is the main development area.

---

## build/

Generated automatically by ROS2.

Contains:

- Build files
- Compilation information

Do not manually edit.

---

## install/

Generated automatically.

Contains:

- Installed ROS2 packages
- Environment setup files

Used with:

```bash
source install/setup.bash
```

---

## log/

Contains:

- Build logs
- Debug information

Useful when troubleshooting build errors.

---

# Current Source Packages

## nmea_navsat_driver

Purpose:

GPS communication driver.

Hardware:

```
SparkFun u-blox SAM-M8Q
```

Provides:

```
/fix
/vel
/heading
/time_reference
```

---

## robot_localization

Purpose:

Sensor fusion using EKF.

Inputs:

```
/imu/data

/fix

/wheel/odometry
```

Output:

```
/odometry/filtered
```

---

## goosebot

Purpose:

Custom Goosebot ROS2 package.

Will contain:

```
Motor Control

Encoder Processing

Robot State

Autonomous Behavior
```

---

# Creating a New Package

Navigate:

```bash
cd ~/ros2_humble/src
```

Create Python package:

```bash
ros2 pkg create goosebot \
--build-type ament_python
```

Result:

```
goosebot/

├── package.xml
├── setup.py
├── setup.cfg
│
└── goosebot/
    └── __init__.py
```

---

# Building After Changes

After adding or editing files:

Go to workspace:

```bash
cd ~/ros2_humble
```

Build:

```bash
colcon build --symlink-install
```

Load changes:

```bash
source install/setup.bash
```

Verify:

```bash
ros2 pkg list
```

---

# Package Development Workflow

The normal ROS2 workflow:

```
Create Package

        |

Write Nodes

        |

Add Launch Files

        |

Add Configuration

        |

Build Package

        |

Source Workspace

        |

Test Nodes
```

---

# Goosebot Development Progress

Completed:

[x] ROS2 Humble workspace created

[x] External packages installed

[x] GPS driver working

[x] IMU node working


Current:

[ ] Create goosebot package

[ ] Add encoder node

[ ] Add motor controller node

[ ] Connect EKF

[ ] Create launch system


Future:

[ ] Nav2 integration

[ ] SLAM

[ ] Autonomous navigation

---

# Useful Commands

List packages:

```bash
ros2 pkg list
```

Check package:

```bash
ros2 pkg prefix goosebot
```

Build only Goosebot:

```bash
colcon build --packages-select goosebot
```

Run a node:

```bash
ros2 run goosebot <node_name>
```

---

# Related Documentation

ROS2 architecture:

```
../
```

Packages:

```
../packages/
```

Nodes:

```
../nodes/
```

Launch:

```
../launch/
```

Config:

```
../config/
```
