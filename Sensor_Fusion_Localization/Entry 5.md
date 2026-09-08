# Step 5 — GPS → ROS 2 → `navsat_transform_node`

## Goal

The purpose of Step 5 is to take the Goosebot GPS data and make it available to the ROS 2 `robot_localization` pipeline.

The data flow is:

```text
SparkFun u-blox SAM-M8Q
        ↓
/dev/ttyS4 @ 9600 baud
        ↓
nmea_navsat_driver
        ↓
/gps/fix
        ↓
navsat_transform_node
        ↓
GPS-based Odometry
```

> **Important:** The EKF is **not configured in Step 5**. The EKF will be configured in Step 6.

---

# 5.1 Hardware Configuration

The Goosebot GPS is the:

```text
SparkFun u-blox SAM-M8Q
```

Current serial configuration:

```text
Device: /dev/ttyS4
Baud rate: 9600
```

---

# 5.2 Verify the GPS Serial Device

Check that the GPS serial device exists:

```bash
ls -l /dev/ttyS4
```

Expected:

```text
/dev/ttyS4
```

If the device exists, continue.

---

# 5.3 Test Raw GPS Data

Before using ROS 2, verify that the GPS is actually transmitting NMEA data.

Set the serial speed:

```bash
sudo stty -F /dev/ttyS4 9600
```

Read the GPS:

```bash
sudo cat /dev/ttyS4
```

You should see NMEA sentences similar to:

```text
$GPGGA,...
$GPRMC,...
```

or other `$GP...`, `$GN...` NMEA messages.

Stop the test with:

```text
Ctrl+C
```

### Checkpoint

The GPS should continuously output NMEA data.

---

# 5.4 Source ROS 2

Open a terminal and run:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

---

# 5.5 Verify `nmea_navsat_driver`

Check whether the GPS driver is available:

```bash
ros2 pkg list | grep nmea_navsat_driver
```

Expected:

```text
nmea_navsat_driver
```

If it is installed, continue.

---

# 5.6 Start the GPS ROS 2 Driver

Run:

```bash
ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600 \
-r /fix:=/gps/fix
```

This node reads the GPS's NMEA data and converts it into a ROS 2 `NavSatFix` message.

The topic is remapped from:

```text
/fix
```

to:

```text
/gps/fix
```

Leave this terminal running.

---

# 5.7 Verify `/gps/fix`

Open a second terminal.

Source ROS 2:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

Check the available topics:

```bash
ros2 topic list
```

You should see:

```text
/gps/fix
```

---

# 5.8 Verify the GPS Message Type

Run:

```bash
ros2 topic type /gps/fix
```

Expected:

```text
sensor_msgs/msg/NavSatFix
```

This confirms that ROS 2 is receiving the GPS data as the correct message type.

---

# 5.9 View the GPS Data

Run:

```bash
ros2 topic echo /gps/fix
```

You should see information similar to:

```text
header:
  stamp:
  frame_id:

status:
  status:
  service:

latitude: ...
longitude: ...
altitude: ...

position_covariance:
  ...
```

The important fields are:

```text
latitude
longitude
altitude
```

The latitude and longitude should correspond to the robot's physical location.

Stop with:

```text
Ctrl+C
```

---

# 5.10 Check GPS Publishing

Run:

```bash
ros2 topic hz /gps/fix
```

The GPS should continuously publish messages.

The exact frequency depends on the GPS configuration, so there is no need to require a specific frequency at this stage.

---

# 5.11 Verify `robot_localization`

`robot_localization` provides the tools we will use for GPS transformation and sensor fusion.

Check that it is installed:

```bash
ros2 pkg list | grep robot_localization
```

Expected:

```text
robot_localization
```

Then check its executables:

```bash
ros2 pkg executables robot_localization
```

You should see executables including:

```text
robot_localization ekf_node
robot_localization navsat_transform_node
robot_localization ukf_node
```

For Step 5, we are primarily interested in:

```text
navsat_transform_node
```

---

# 5.12 What `navsat_transform_node` Does

The GPS provides geographic coordinates:

```text
latitude
longitude
altitude
```

However, the robot's odometry system operates in a local Cartesian coordinate system.

`navsat_transform_node` converts the GPS information into a form that can be used by the robot's localization system.

Conceptually:

```text
GPS
 ↓
/gps/fix
 ↓
navsat_transform_node
 ↓
GPS-based Odometry
```

---

# 5.13 Inputs Required by `navsat_transform_node`

For the final Goosebot configuration, `navsat_transform_node` will work with information from:

```text
GPS
 ↓
/gps/fix

IMU
 ↓
/imu/data

Robot Odometry
 ↓
/odometry/filtered
```

The overall relationship is:

```text
                  /imu/data
                      │
                      ↓
                ┌──────────────┐
                │    navsat    │
/gps/fix ──────→│   transform  │
                └──────────────┘
                      ↑
                      │
              /odometry/filtered
```

> **Do not configure the final EKF connections in Step 5.** That is Step 6.

---

# 5.14 Create the Configuration Directory

Create a configuration directory inside the Goosebot package:

```bash
mkdir -p ~/ros2_humble/src/goosebot_sensors/config
```

---

# 5.15 Create `navsat.yaml`

Create:

```text
~/ros2_humble/src/goosebot_sensors/config/navsat.yaml
```

Use Nano to edit .yaml file

Use:

```yaml
navsat_transform:
  ros__parameters:

    frequency: 30.0

    delay: 0.0

    magnetic_declination_radians: 0.0

    yaw_offset: 0.0

    zero_altitude: true

    broadcast_utm_transform: false

    publish_filtered_gps: true

    use_odometry_yaw: false

    wait_for_datum: false
```

---

# 5.16 Important Configuration Values

Two parameters will eventually need to be properly calibrated:

```yaml
magnetic_declination_radians: 0.0
yaw_offset: 0.0
```

These should not automatically be considered final values.

They depend on:

* Robot IMU orientation
* IMU coordinate convention
* Robot heading convention
* Magnetic declination at the operating location

These will be finalized when we connect the IMU and GPS to the localization system.

---

# 5.17 Build the Configuration into the ROS 2 Package

After creating the configuration file, the package needs to install it.

The `setup.py` should eventually include the configuration directory in its `data_files`.

For example:

```python
from setuptools import setup
from glob import glob
import os

package_name = "goosebot_sensors"

setup(
    name=package_name,
    version="0.0.0",
    packages=[package_name],

    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name]
        ),

        (
            "share/" + package_name,
            ["package.xml"]
        ),

        (
            os.path.join("share", package_name, "config"),
            glob("config/*.yaml")
        ),
    ],

    install_requires=[
        "setuptools",
    ],

    zip_safe=True,

    entry_points={
        "console_scripts": [
            "encoder_odom = goosebot_sensors.encoder_odom:main",
        ],
    },
)
```

Then rebuild:

```bash
cd ~/ros2_humble
source /opt/ros/humble/setup.bash

colcon build --packages-select goosebot_sensors

source ~/ros2_humble/install/setup.bash
```

---

# 5.18 Verify the Configuration Was Installed

Run:

```bash
ls ~/ros2_humble/install/goosebot_sensors/share/goosebot_sensors/config/
```

Expected:

```text
navsat.yaml
```

---

# 5.19 `navsat_transform_node` — Final Architecture

At this point, do **not** treat the following as a final launch command yet.

The final architecture we are building toward is:

```text
                       ┌───────────────┐
                       │    IMU        │
                       │  /imu/data   │
                       └───────┬───────┘
                               │
                               ↓
                        ┌────────────┐
                        │    EKF     │
                        └─────┬──────┘
                              │
                              ↓
                     /odometry/filtered
                              │
                              ↓
                    ┌──────────────────┐
                    │ navsat_transform │
                    └────────┬─────────┘
                             ↑
                             │
                         /gps/fix
                             ↑
                             │
                            GPS
```

The encoder will also eventually feed the EKF:

```text
Encoder
   ↓
/wheel/odom
   ↓
  EKF
```

Therefore, the complete system will eventually become:

```text
                  ┌──────────────┐
                  │     IMU      │
                  │  /imu/data  │
                  └──────┬───────┘
                         │
                         ↓
Encoder ──→ /wheel/odom ──→ EKF ──→ /odometry/filtered
                                  │
                                  ↓
                         navsat_transform
                                  ↑
                                  │
                            /gps/fix
                                  ↑
                                  │
                                 GPS
```

> The exact `navsat_transform_node` topic remappings and EKF configuration will be established in **Step 6** rather than hard-coded prematurely in Step 5.

---

# 5.20 Step 5 Troubleshooting

## `/dev/ttyS4` does not exist

Run:

```bash
ls /dev/ttyS*
```

Verify that the GPS is connected to the expected UART.

---

## No NMEA data

Run:

```bash
sudo stty -F /dev/ttyS4 9600
sudo cat /dev/ttyS4
```

Check:

* GPS power
* TX/RX wiring
* Ground connection
* UART selection
* Baud rate

---

## `/gps/fix` does not appear

Check that the driver is running:

```bash
ros2 node list
```

You should see the NMEA driver node.

Then check:

```bash
ros2 topic list
```

---

## `/gps/fix` exists but has no useful position

Run:

```bash
ros2 topic echo /gps/fix
```

Check:

```text
latitude
longitude
status
```

The GPS may need time and a suitable outdoor view of the sky to obtain a good fix.

---

# 5.21 Step 5 Completion Checkpoint

Step 5 is complete when:

* [ ] GPS is connected.
* [ ] `/dev/ttyS4` exists.
* [ ] GPS outputs NMEA data.
* [ ] GPS operates at 9600 baud.
* [ ] `nmea_navsat_driver` is installed.
* [ ] `nmea_serial_driver` starts successfully.
* [ ] `/gps/fix` exists.
* [ ] `/gps/fix` is `sensor_msgs/msg/NavSatFix`.
* [ ] Latitude is being published.
* [ ] Longitude is being published.
* [ ] GPS data continuously publishes.
* [ ] `robot_localization` is installed.
* [ ] `navsat_transform_node` is available.
* [ ] `navsat.yaml` exists.

---

# Step 5 Final Result

At the end of Step 5, Goosebot has three independently verified sensor paths:

```text
Step 3
IMU
 ↓
/imu/data
```

```text
Step 4
Encoder
 ↓
/wheel/odom
```

```text
Step 5
GPS
 ↓
/gps/fix
 ↓
navsat_transform_node
```

The next step is **Step 6 — EKF Sensor Fusion**.

That is where the three sensor sources are finally brought together using `robot_localization`:

```text
                  /imu/data
                      │
                      ↓
/wheel/odom ────────→ EKF ─────→ /odometry/filtered
                      ↑
                      │
                GPS odometry
                      ↑
                      │
              navsat_transform
                      ↑
                      │
                  /gps/fix
```

**Step 5 = prepare and verify GPS.**

**Step 6 = actually fuse GPS + IMU + encoder.**
