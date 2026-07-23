# GooseBot ROCK 5C Motor + Encoder Setup Guide

Complete beginner-friendly guide for installing and configuring:

- ROCK 5C SBC
- PCA9685 PWM motor controller
- Encoder DC motors
- Dual wheel encoder feedback
- Keyboard motor control
- Distance calculation

This setup is designed as the foundation for future:

- ROS2 Differential Drive
- Odometry
- Nav2 Navigation
- Autonomous Driving

---
NOTICE: Make sure to follow the instruction in 04_motor_test. You need to be able to enter goose, activate venv, the pythin virtual enviorment, and the proper libraries.
# 1. Hardware Overview

## Components

| Component | Purpose |
|---|---|
| ROCK 5C | Main computer |
| PCA9685 | PWM motor controller |
| Motor Driver | Controls motor power |
| TT Encoder Motors | Drive wheels + feedback |
| Battery | Motor power |
| Jumper wires | Connections |

---

# 2. System Architecture
