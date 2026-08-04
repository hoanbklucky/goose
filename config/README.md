# GooseBot Configuration Files

This folder contains all configuration files used by GooseBot.

Configuration files define how ROS2 nodes, sensors, and localization algorithms operate.

The goal is to keep hardware-independent settings separate from the actual code.

---

# Folder Structure

```
config/
│
├── gps/
│   └── neo_m8u_rover.yaml
│
├── localization/
│   └── ekf.yaml
│
└── robot/
    └── robot_params.yaml
```

---

# GPS Configuration

Location:

```
config/gps/neo_m8u_rover.yaml
```

This file configures the SparkFun SAM-M8Q GPS module.

Current hardware:

- GPS Module: SparkFun SAM-M8Q
- Connection: UART
- ROCK 5C UART:
  - TX → Pin 7
  - RX → Pin 29
- Device:

```
/dev/ttyS4
```

Baud rate:

```
9600
```

The GPS outputs standard NMEA messages:

Examples:

```
$GNRMC
$GNGGA
$GNGSA
$GPGSV
```

---

# GPS ROS2 Node

The GPS driver used:

```
nmea_navsat_driver
```

Launch command:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600
```

Successful operation produces:

```
/fix
/heading
/vel
/time_reference
```

---

# GPS Notes

The GPS requires outdoor satellite visibility.

Indoor testing may produce:

```
latitude: .nan
longitude: .nan
altitude: .nan
```

This means:

- GPS communication works
- No satellite fix is available

A valid outdoor fix should show:

```
status:
  status: 0
```

or better.

---

# Localization Configuration

Location:

```
config/localization/ekf.yaml
```

This file will contain parameters for:

```
robot_localization
```

The Extended Kalman Filter (EKF) combines:

- IMU
- GPS
- Wheel Encoder

into one estimated robot position.

Sensor flow:

```
IMU
 |
 |
 v
robot_localization EKF
 ^
 |
GPS


Wheel Encoder
```

---

# Robot Parameters

Location:

```
config/robot/robot_params.yaml
```

Contains robot-specific measurements.

Current GooseBot values:

## Wheels

Wheel diameter:

```
2.6 inches
```

Encoder:

```
1092 counts/revolution
```

Used for distance calculations:

```
distance = encoder counts / counts_per_rev * wheel circumference
```

---

# Why Configuration Is Separate

Keeping configuration separate allows:

- Changing hardware without rewriting code
- Easy ROS2 parameter loading
- Reproducible setup
- Easier debugging
- Easier collaboration

---

# Current Status

Completed:

[x] GPS communication  
[x] GPS ROS2 publishing  
[x] IMU ROS2 publishing  
[x] robot_localization package installed  

In Progress:

[ ] EKF configuration  
[ ] Wheel encoder ROS2 publishing  
[ ] Full sensor fusion  

---

# Next Steps

Continue building:

```
config/
    localization/
        ekf.yaml
```

Then connect:

```
GPS + IMU + Encoder
          |
          v
 robot_localization EKF
          |
          v
      /odometry
```
