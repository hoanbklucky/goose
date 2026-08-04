# ROS2 Package Structure

This document explains the planned ROS2 organization for Goosebot.

The goal is to organize the robot software like a professional ROS2 project.

The structure separates:

- Hardware drivers
- Sensor nodes
- Robot description
- Localization
- Navigation
- Launch files
- Configuration

---

# 1. Complete Goosebot ROS2 Workspace

Main workspace:

```
~/ros2_humble/
```

Structure:

```
ros2_humble/

├── src/

│
├── build/

├── install/

└── log/
```

---

# 2. Source Folder

All custom ROS2 packages belong inside:

```
~/ros2_humble/src/
```

Example:

```
src/

├── goosebot_description

├── goosebot_bringup

├── goosebot_sensors

├── goosebot_control

├── goosebot_localization

└── goosebot_navigation
```

---

# 3. Goosebot Package Overview

## goosebot_description

Purpose:

Robot model.

Contains:

- URDF
- Xacro files
- Robot dimensions
- Links
- Joints
- Sensors positions

Structure:

```
goosebot_description/

├── urdf/

│   └── goosebot.urdf.xacro

├── meshes/

├── launch/

│   └── display.launch.py

└── package.xml
```

---

# 4. goosebot_bringup

Purpose:

Starts the entire robot.

Responsible for:

- Starting sensors
- Starting controllers
- Starting localization

Structure:

```
goosebot_bringup/

├── launch/

│   └── robot.launch.py

├── config/

└── package.xml
```

Example launch:

```
robot.launch.py

starts:

IMU

GPS

Encoder

EKF

Navigation
```

---

# 5. goosebot_sensors

Purpose:

All hardware sensor drivers.

Contains:

- IMU
- GPS
- Encoder
- Ultrasonic
- Other sensors

Structure:

```
goosebot_sensors/

├── goosebot_sensors/

│
├── imu_node.py

├── gps_node.py

├── encoder_node.py

└── ultrasonic_node.py


├── launch/

├── config/

└── package.xml
```

---

# 6. goosebot_control

Purpose:

Robot movement.

Contains:

- Motor control
- PWM control
- Servo control

Structure:

```
goosebot_control/

├── goosebot_control/

│
├── motor_controller.py

├── pwm_driver.py

└── servo_controller.py


├── config/

└── package.xml
```

---

# 7. goosebot_localization

Purpose:

Sensor fusion.

Contains:

- EKF configuration
- GPS transformation

Structure:

```
goosebot_localization/

├── config/

│
└── ekf.yaml


├── launch/

│
└── localization.launch.py


└── package.xml
```

---

# 8. goosebot_navigation

Purpose:

Autonomous navigation.

Contains:

- Nav2 configuration
- Maps
- Planner settings

Structure:

```
goosebot_navigation/

├── config/

│
├── nav2.yaml

│
└── costmap.yaml


├── maps/

│
└── map.yaml


├── launch/

│
└── navigation.launch.py


└── package.xml
```

---

# 9. Final ROS2 Graph

The final system:

```
                 Camera

                   |

                   v


IMU ---------

             |

GPS -------->|

             |

Encoder -----|


             v


     robot_localization

             |

             v


    /odometry/filtered


             |

             v


            Nav2


             |

             v


      Motor Controller


             |

             v


          Motors
```

---

# 10. Current Progress

Completed:

```
/imu/data

/fix

robot_localization installed
```

---

In Progress:

```
/odom encoder node

EKF launch

Nav2 setup
```

---

Future:

```
Camera node

SLAM

Obstacle avoidance

Autonomous driving
```

---

# 11. Recommended Development Order

## Step 1

Hardware drivers:

```
IMU

GPS

Encoder
```

---

## Step 2

ROS2 topics:

```
/imu/data

/fix

/odom
```

---

## Step 3

Robot description:

```
URDF

TF frames
```

---

## Step 4

Localization:

```
robot_localization EKF
```

---

## Step 5

Navigation:

```
Nav2

SLAM
```

---

# Goal

By following this structure, Goosebot becomes a modular ROS2 robot.

Each part can be tested independently and replaced without rewriting the entire system.
