# Goosebot ROS2 Package

## Overview

The `goosebot` package is the custom ROS2 package created specifically for the Goosebot autonomous RC car.

This package contains Goosebot-specific code that connects:

- Sensors
- Motors
- Encoders
- Localization
- Autonomous behaviors

into one ROS2 system.

---

# Package Role

ROS2 packages are separated by responsibility.

Goosebot uses:

```
External ROS2 Packages

        |
        |

Custom Goosebot Package

        |
        |

Robot Hardware
```

---

# External Packages

These packages provide existing functionality.

## nmea_navsat_driver

Purpose:

GPS communication.

Input:

```
UART GPS data
```

Output:

```
/fix
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

# Goosebot Package Responsibilities

The Goosebot package handles:

```
Motor Control

Encoder Processing

Robot State

Hardware Communication

Autonomous Logic
```

---

# Planned Package Structure

Final package:

```
goosebot/

├── package.xml
├── setup.py
├── setup.cfg
│
├── goosebot/
│   |
│   ├── __init__.py
│   |
│   ├── encoder_node.py
│   |
│   ├── motor_node.py
│   |
│   ├── robot_state_node.py
│   |
│   └── navigation_node.py
│
├── launch/
│   |
│   └── robot.launch.py
│
├── config/
│   |
│   └── parameters.yaml
│
└── resource/
```

---

# Node Overview

## Encoder Node

File:

```
encoder_node.py
```

Purpose:

Convert wheel encoder signals into ROS2 odometry.

Hardware:

```
TT Encoder Motors
```

Input:

```
GPIO Encoder Signals
```

Output:

```
/wheel/odometry
```

Message:

```
nav_msgs/msg/Odometry
```

---

# Motor Controller Node

File:

```
motor_node.py
```

Purpose:

Control Goosebot motors.

Hardware:

```
L298N Motor Driver

PCA9685 PWM Controller
```

Input:

```
/cmd_vel
```

Message:

```
geometry_msgs/msg/Twist
```

Output:

```
PWM motor commands
```

---

# Robot State Node

File:

```
robot_state_node.py
```

Purpose:

Monitor robot information.

Future:

- Battery state
- Sensor health
- Motor status
- Errors

---

# Navigation Node

File:

```
navigation_node.py
```

Purpose:

Custom autonomous behavior.

Future:

- Waypoint handling
- Decision making
- Autonomous driving logic

---

# Creating The Package

Navigate:

```bash
cd ~/ros2_humble/src
```

Create:

```bash
ros2 pkg create goosebot \
--build-type ament_python
```

---

# Building

Go to workspace:

```bash
cd ~/ros2_humble
```

Build:

```bash
colcon build --symlink-install
```

Source:

```bash
source install/setup.bash
```

Verify:

```bash
ros2 pkg list | grep goosebot
```

---

# Node Development Workflow

Every new node follows:

```
Create Python File

        |

Add ROS2 Publisher/Subscriber

        |

Register Node

        |

Update setup.py

        |

Build Package

        |

Test Node
```

---

# Example Node Test

After creating:

```
encoder_node.py
```

Build:

```bash
colcon build --packages-select goosebot
```

Source:

```bash
source install/setup.bash
```

Run:

```bash
ros2 run goosebot encoder_node
```

Check:

```bash
ros2 node list
```

---

# Current Development Status

Completed:

[x] ROS2 workspace created

[x] GPS ROS2 integration

[x] IMU ROS2 integration

[x] robot_localization installed


In Progress:

[ ] Create goosebot package

[ ] Create encoder node

[ ] Create motor node

[ ] Add EKF configuration

[ ] Create launch system


Future:

[ ] Nav2

[ ] SLAM

[ ] Autonomous navigation

---

# Related Documentation

ROS2 structure:

```
../../
```

Nodes:

```
../../nodes/
```

Config:

```
../../config/
```

Launch:

```
../../launch/
```
