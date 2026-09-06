# Step 3 — MPU-6050 ROS 2 Integration

## Objective

Connect the already-verified MPU-6050 to ROS 2 and confirm that ROS 2 can receive real accelerometer and gyroscope measurements.

The intended data path is:

```text
MPU-6050
   ↓
I²C (/dev/i2c-6)
   ↓
I²C address 0x68
   ↓
ROS 2 MPU-6050 driver
   ↓
ROS 2 IMU topic
```

> **Important:** This step does **not** involve the EKF yet. The goal is only to verify that the IMU works through ROS 2.

---

## 3.1 Source ROS 2

Open a terminal on the ROCK 5C:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

If using the Goosebot Python virtual environment:

```bash
source ~/goosebot_venv/bin/activate
```

---

## 3.2 Verify the MPU-6050

The MPU-6050 was previously identified on I²C bus 6 at address `0x68`.

Check the bus:

```bash
sudo i2cdetect -y 6
```

Confirm that `68` appears in the table.

Example:

```text
     0 1 2 3 4 5 6 7 8 9 a b c d e f
00:          -- -- -- -- -- -- -- -- --
...
60: -- -- -- -- -- -- -- 68 -- -- -- --
...
```

This confirms that the MPU-6050 is responding over I²C.

---

## 3.3 Install a ROS 2 MPU-6050 Driver

For an initial ROS 2 test, use an existing MPU-6050 ROS 2 driver rather than creating a custom ROS 2 node.

Go to the ROS 2 workspace:

```bash
cd ~/ros2_humble/src
```

Clone the driver:

```bash
git clone https://github.com/kimsniper/ros2_mpu6050.git
```

Return to the workspace:

```bash
cd ~/ros2_humble
```

Install dependencies:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

Build the driver:

```bash
colcon build --packages-select ros2_mpu6050
```

Source the updated workspace:

```bash
source ~/ros2_humble/install/setup.bash
```

---

## 3.4 Verify the ROS 2 Package

Check that ROS 2 can see the package:

```bash
ros2 pkg list | grep ros2_mpu6050
```

Expected:

```text
ros2_mpu6050
```

Check its available executables:

```bash
ros2 pkg executables ros2_mpu6050
```

---

## 3.5 Start the IMU ROS 2 Driver

Launch the driver:

```bash
ros2 launch ros2_mpu6050 ros2_mpu6050.launch.py
```

Leave this terminal running.

The driver should now provide the connection:

```text
MPU-6050
   ↓
/dev/i2c-6
   ↓
0x68
   ↓
ROS 2 MPU-6050 driver
```

---

## 3.6 Check the ROS 2 Topics

Open a **second terminal**.

Source ROS 2:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

List the active topics:

```bash
ros2 topic list
```

The driver is expected to publish an IMU topic such as:

```text
/imu/mpu6050
```

> Do not assume `/imu/data` yet. The exact topic name depends on the driver configuration.

---

## 3.7 Confirm the IMU Message Type

Check the topic type:

```bash
ros2 topic type /imu/mpu6050
```

Expected:

```text
sensor_msgs/msg/Imu
```

Check additional topic information:

```bash
ros2 topic info /imu/mpu6050
```

This confirms that ROS 2 has an active publisher for the IMU data.

---

## 3.8 Display the IMU Measurements

Run:

```bash
ros2 topic echo /imu/mpu6050
```

The output should contain fields such as:

```text
linear_acceleration:
  x: ...
  y: ...
  z: ...

angular_velocity:
  x: ...
  y: ...
  z: ...
```

Move and rotate the MPU-6050.

The acceleration and angular velocity values should change in response to the movement.

---

## 3.9 Check the IMU Publishing Rate

Run:

```bash
ros2 topic hz /imu/mpu6050
```

This verifies that the IMU is continuously publishing data and shows the approximate publishing frequency.

---

## Step 3 Checkpoint

Step 3 is complete when:

* [ ] MPU-6050 appears at I²C address `0x68`
* [ ] ROS 2 MPU-6050 driver is installed
* [ ] Driver builds successfully
* [ ] Driver launches successfully
* [ ] IMU ROS 2 topic appears
* [ ] Topic type is `sensor_msgs/msg/Imu`
* [ ] Accelerometer data is visible
* [ ] Gyroscope data is visible
* [ ] Values change when the IMU is moved
* [ ] IMU publishes continuously

### Expected Data Flow

```text
             HARDWARE
                 │
                 ▼
          ┌─────────────┐
          │  MPU-6050   │
          └──────┬──────┘
                 │
              I²C 0x68
                 │
                 ▼
          ┌─────────────┐
          │ ROS 2 IMU   │
          │   Driver    │
          └──────┬──────┘
                 │
                 ▼
          /imu/mpu6050
                 │
                 ▼
       sensor_msgs/msg/Imu
```

## What Step 3 Proves

Step 2 proved that the **physical MPU-6050 communicates with the ROCK 5C**.

Step 3 proves that **ROS 2 can receive and publish the MPU-6050 measurements**.

The EKF will be tested later:

```text
IMU ──────────────┐
                  │
Encoder → /odom ──┼──→ robot_localization EKF
                  │
GPS → navsat ─────┘
```

> **Do not proceed to EKF configuration until the IMU is successfully publishing valid ROS 2 `sensor_msgs/Imu` messages.**
