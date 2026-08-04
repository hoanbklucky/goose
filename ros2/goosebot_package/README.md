# Goosebot ROS2 Package

## Overview

This folder documents the custom ROS2 package for Goosebot.

The purpose of this package is to combine Goosebot's custom robot software into one ROS2 package.

External packages such as:

```
nmea_navsat_driver
robot_localization
```

provide existing functionality.

The `goosebot` package will contain the custom logic that connects everything together.

---

# Purpose

The Goosebot package will eventually handle:

- Motor control
- Wheel encoder processing
- Sensor management
- Robot state
- Autonomous behaviors
- Communication between hardware and ROS2

---

# Planned Package Structure

Final structure:

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

# Package Creation

Navigate:

```bash
cd ~/ros2_humble/src
```

Create package:

```bash
ros2 pkg create goosebot \
--build-type ament_python
```

Expected:

```
goosebot/
├── package.xml
├── setup.py
└── goosebot/
```

---

# Building Package

From workspace:

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

Check package:

```bash
ros2 pkg list | grep goosebot
```

---

# Planned Nodes

## Encoder Node

File:

```
encoder_node.py
```

Purpose:

Convert wheel encoder signals into ROS2 odometry.

Input:

```
GPIO encoder signals
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

## Motor Node

File:

```
motor_node.py
```

Purpose:

Control motors from ROS2 commands.

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

## Robot State Node

File:

```
robot_state_node.py
```

Purpose:

Track Goosebot status.

Future responsibilities:

- Battery monitoring
- Sensor status
- Error reporting

---

# Integration Flow

```
             Sensors

                |
                |

        External ROS2 Drivers

                |
                |

          goosebot package

                |
                |

        robot_localization EKF

                |
                |

              Nav2

                |
                |

          Autonomous Robot
```

---

# Development Roadmap

## Phase 1: Package Creation

[ ] Create goosebot package

[ ] Verify ROS2 build

[ ] Create first node


---

## Phase 2: Hardware Integration

[ ] Convert encoder script into ROS2 node

[ ] Convert motor control into ROS2 node

[ ] Add robot parameters


---

## Phase 3: Localization

[ ] Connect encoder odometry

[ ] Configure EKF

[ ] Publish filtered odometry


---

## Phase 4: Navigation

[ ] Integrate Nav2

[ ] Add SLAM

[ ] Autonomous driving


---

# Related Documentation

ROS2 packages:

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

Configuration:

```
../config/
```

Scripts:

```
../scripts/
```
