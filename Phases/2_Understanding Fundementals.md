# Phase 2 – Understanding ROS2 Fundamentals

## Objective

Learn the core concepts of ROS2 that are required before creating the Goosebot software. By the end of this phase, you should understand how ROS2 organizes programs, how different parts of the robot communicate, and how data flows between sensors and algorithms.

---

## Commands

```bash
# List all running ROS2 nodes
ros2 node list

# List all active topics
ros2 topic list

# Display information about a topic
ros2 topic info /parameter_events

# Echo messages from a topic
ros2 topic echo /parameter_events

# List all installed ROS2 packages
ros2 pkg list
```

---

## Summary

During this phase, the focus is on understanding the ROS2 communication system rather than writing code. A ROS2 application is composed of nodes that exchange messages through topics. Publishers send data to topics, subscribers receive data from topics, and packages organize related code into reusable components. These concepts form the foundation for integrating the Goosebot sensors into ROS2.

### Concepts Learned

### Node

A node is a single executable program responsible for one task.

Examples:

- IMU Node
- GPS Node
- Encoder Node
- Motor Controller Node

---

### Topic

A topic is a communication channel between nodes.

Example:

```text
IMU Node
     │
Publishes
     │
     ▼
 /imu/data
     ▲
Subscribes
     │
robot_localization
```

---

### Publisher

A publisher sends messages to a topic.

Example:

```text
GPS Node
     │
Publishes
     ▼
 /fix
```

---

### Subscriber

A subscriber receives messages from a topic.

Example:

```text
robot_localization
        │
Subscribes to
        ▼
     /imu/data
     /fix
     /wheel/odometry
```

---

### Package

A package contains all of the files needed for a ROS2 application.

Future Goosebot package:

```text
goosebot/
├── package.xml
├── setup.py
├── setup.cfg
└── goosebot/
```

---

### Message

A message is structured data transmitted between nodes.

Examples:

- sensor_msgs/Imu
- sensor_msgs/NavSatFix
- nav_msgs/Odometry
- geometry_msgs/Twist

---

## Troubleshooting

### `ros2 node list` returns nothing

If no custom nodes have been created yet, this is expected.

---

### Only `/parameter_events` and `/rosout` appear

This is normal before any Goosebot nodes have been launched.

---

### `ros2 topic echo` produces no output

The selected topic may not currently have an active publisher.

Verify that the node publishing the topic is running.

---

## Phase Completion Checklist

- [ ] Understand what a node is.
- [ ] Understand what a topic is.
- [ ] Understand publishers and subscribers.
- [ ] Understand ROS2 messages.
- [ ] Understand ROS2 packages.
- [ ] Successfully use `ros2 node list`.
- [ ] Successfully use `ros2 topic list`.

Phase 2 is complete.
