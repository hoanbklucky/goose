# Step 6 — Create and Configure the EKF

## Goal

The goal of Step 6 is to take the sensor data that was already verified in the previous steps and combine it using the ROS 2 `robot_localization` Extended Kalman Filter (EKF).

At the beginning of this step, the following sensor topics should already exist:

```text
IMU      → /imu/data
Encoder  → /wheel/odom
GPS      → /gps/fix
```

The `robot_localization` package should also already be installed and available.

The overall goal is:

```text
IMU
 │
 ├──────────────┐
 │              │
 ▼              │
/imu/data       │
                │
Encoder         │
 │              │
 ▼              │
/wheel/odom ───► EKF ───► /odometry/filtered
                │
                │
GPS             │
 │              │
 ▼              │
/gps/fix → navsat_transform_node
                │
                ▼
          GPS odometry
```

---

# 6.1 — Verify the Existing Sensor Topics

Before creating the EKF, verify that the sensor nodes are still publishing.

### Check the IMU

```bash
ros2 topic type /imu/data
```

Expected:

```text
sensor_msgs/msg/Imu
```

Check the data:

```bash
ros2 topic echo /imu/data
```

---

### Check the wheel odometry

```bash
ros2 topic type /wheel/odom
```

Expected:

```text
nav_msgs/msg/Odometry
```

Check the data:

```bash
ros2 topic echo /wheel/odom
```

---

### Check the GPS

```bash
ros2 topic type /gps/fix
```

Expected:

```text
sensor_msgs/msg/NavSatFix
```

Check the data:

```bash
ros2 topic echo /gps/fix
```

---

# 6.2 — Verify robot_localization

Confirm that `robot_localization` is already installed:

```bash
ros2 pkg list | grep robot_localization
```

Then:

```bash
ros2 pkg executables robot_localization
```

The available executables should include:

```text
ekf_node
navsat_transform_node
ukf_node
```

Do **not** reinstall `robot_localization` if these are already available.

---

# 6.3 — Create the Configuration Directory

The EKF configuration will be stored with the Goosebot sensor package.

```bash
mkdir -p ~/ros2_humble/src/goosebot_sensors/config
```

---

# 6.4 — Create `ekf.yaml`

Create:

```text
~/ros2_humble/src/goosebot_sensors/config/ekf.yaml
```

Initial configuration:

```yaml
ekf_filter_node:
  ros__parameters:

    # EKF update frequency
    frequency: 30.0

    # Maximum time between sensor measurements
    sensor_timeout: 0.2

    # Goosebot is a ground robot
    two_d_mode: true

    # Publish the odom -> base_link transform
    publish_tf: true

    # Coordinate frames
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom


    # =========================================================
    # WHEEL ENCODER ODOMETRY
    # =========================================================

    odom0: /wheel/odom

    odom0_config: [
      true,  true,  false,
      false, false, true,
      true,  false, false,
      false, false, true,
      false, false, false
    ]

    odom0_differential: false
    odom0_relative: false


    # =========================================================
    # IMU
    # =========================================================

    imu0: /imu/data

    imu0_config: [
      false, false, false,
      false, false, true,
      false, false, false,
      false, false, true,
      false, false, false
    ]

    imu0_differential: false
    imu0_relative: false

    imu0_remove_gravitational_acceleration: true
```

---

# 6.5 — Understand the EKF Configuration

The `*_config` arrays contain 15 values.

Their order is:

```text
[x, y, z,
 roll, pitch, yaw,
 vx, vy, vz,
 vroll, vpitch, vyaw,
 ax, ay, az]
```

This is the standard `robot_localization` ordering.

For example:

```yaml
odom0_config: [
  true,  true,  false,
  false, false, true,
  true,  false, false,
  false, false, true,
  false, false, false
]
```

means the encoder odometry is initially being used for:

```text
X position       ✓
Y position       ✓
Z position       ✗

Roll             ✗
Pitch            ✗
Yaw              ✓

X velocity       ✓
Y velocity       ✗
Z velocity       ✗

Roll velocity    ✗
Pitch velocity   ✗
Yaw velocity     ✓

X acceleration   ✗
Y acceleration   ✗
Z acceleration   ✗
```

For the IMU:

```yaml
imu0_config: [
  false, false, false,
  false, false, true,
  false, false, false,
  false, false, true,
  false, false, false
]
```

we initially use:

```text
Yaw
Yaw rate
```

The exact IMU configuration should be verified against the actual `/imu/data` message before treating this as the final configuration.

---

# 6.6 — Build the Goosebot Package

After creating the YAML file:

```bash
cd ~/ros2_humble

source /opt/ros/humble/setup.bash

colcon build --packages-select goosebot_sensors
```

Then source the workspace:

```bash
source ~/ros2_humble/install/setup.bash
```

This is a relatively small package build. It is **not** the large ROS 2/`robot_localization` compilation that previously caused memory pressure on the ROCK 5C.

---

# 6.7 — Start the EKF

Run:

```bash
ros2 run robot_localization ekf_node \
--ros-args \
--params-file ~/ros2_humble/src/goosebot_sensors/config/ekf.yaml
```

If the configuration is accepted, the EKF node should start.

---

# 6.8 — Verify the EKF Node

Open another terminal and source ROS:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

Check the nodes:

```bash
ros2 node list
```

Check the topics:

```bash
ros2 topic list
```

We should see:

```text
/odometry/filtered
```

---

# 6.9 — Verify the EKF Output

Check the message type:

```bash
ros2 topic type /odometry/filtered
```

Expected:

```text
nav_msgs/msg/Odometry
```

Then:

```bash
ros2 topic echo /odometry/filtered
```

The EKF should now be publishing a fused state estimate.

The output contains information such as:

```text
position
orientation
linear velocity
angular velocity
```

---

# 6.10 — Check the EKF Update Rate

Run:

```bash
ros2 topic hz /odometry/filtered
```

The target configuration is:

```text
30 Hz
```

The actual measured rate may vary slightly depending on sensor timing and system load.

---

# 6.11 — Test the Encoder + IMU Fusion

At this point, initially test the EKF with:

```text
/wheel/odom
        +
/imu/data
        ↓
       EKF
        ↓
/odometry/filtered
```

### Test 1 — Robot stationary

Leave Goosebot still.

The output should remain relatively stable.

---

### Test 2 — Drive forward

Move Goosebot forward.

The filtered odometry should show movement in the forward direction.

---

### Test 3 — Turn

Rotate the robot.

The yaw/orientation estimate should change.

---

### Test 4 — Stop

Stop the robot.

The velocity estimate should decrease toward zero.

---

# 6.12 — Connect GPS Through navsat_transform_node

GPS is not directly connected to the EKF as:

```text
/gps/fix → EKF
```

because `/gps/fix` is a `sensor_msgs/msg/NavSatFix` message.

Instead, `navsat_transform_node` is used to transform the GPS measurement into an odometry representation that can participate in localization. `robot_localization` provides `navsat_transform_node` specifically for GPS integration.

The intended flow is:

```text
GPS
 │
 ▼
/gps/fix
 │
 ▼
navsat_transform_node
 │
 ▼
GPS-based odometry
 │
 ▼
EKF
```

The exact final GPS/EKF architecture will be configured carefully in the next part of Step 6 because `navsat_transform_node` also requires appropriate odometry and heading information.

---

# 6.13 — Final Sensor-Fusion Architecture

Once GPS integration is completed, the intended system is:

```text
                  IMU
                   │
                   ▼
               /imu/data
                   │
                   │
Encoder            │
   │               │
   ▼               │
/wheel/odom ───────┼────► EKF
                   │       │
                   │       ▼
                   │  /odometry/filtered
                   │
GPS                │
 │                 │
 ▼                 │
/gps/fix           │
 │                 │
 ▼                 │
navsat_transform ──┘
```

The final implementation may use separate localization stages/EKFs depending on the required `map`/`odom` architecture. `robot_localization` recommends using an `odom`-world filter for continuous local data and a `map`-world filter when fusing global GPS data.

---

# 6.14 — Step 6 Checkpoint

Step 6 is complete when:

* [ ] `/imu/data` is publishing
* [ ] `/wheel/odom` is publishing
* [ ] `/gps/fix` is publishing
* [ ] `robot_localization` is installed
* [ ] `ekf_node` is available
* [ ] `ekf.yaml` has been created
* [ ] EKF starts without errors
* [ ] `/odometry/filtered` exists
* [ ] `/odometry/filtered` has type `nav_msgs/msg/Odometry`
* [ ] EKF responds to encoder movement
* [ ] EKF responds to IMU rotation
* [ ] GPS is connected through `navsat_transform_node`
* [ ] Final fused localization is verified

---

## Step 6 Result

Before Step 6:

```text
IMU     → working independently
Encoder → working independently
GPS     → working independently
```

After Step 6:

```text
IMU ────────┐
            │
Encoder ────┼──► Localization / EKF ──► fused odometry
            │
GPS ────────┘
```

The important achievement is that Goosebot is no longer treating the IMU, encoder, and GPS as three unrelated sensors.

They are being combined into a **single estimated robot state** that can later be used by the navigation stack.
