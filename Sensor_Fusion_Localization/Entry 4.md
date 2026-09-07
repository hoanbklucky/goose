# Step 4 — Encoder → ROS 2 → Wheel Odometry

## Goal

Convert the Goosebot wheel encoder signals into a ROS 2 wheel-odometry topic.

The data flow for this step is:

```text
Wheel Encoders
      ↓
gpiod
      ↓
Encoder ROS 2 Node
      ↓
Encoder Counts
      ↓
Wheel Distance + Differential Drive Calculations
      ↓
/wheel/odom
      ↓
nav_msgs/msg/Odometry
```

> **Important:** The IMU, GPS, `navsat_transform_node`, and EKF are **not configured in Step 4**. They will be connected later during the sensor-fusion stage.

---

# 4.1 Encoder Hardware

The Goosebot uses quadrature wheel encoders.

Current encoder wiring:

| Encoder | Signal | Physical Pin |
| ------- | ------ | -----------: |
| Left    | A      |           11 |
| Left    | B      |           13 |
| Right   | A      |           15 |
| Right   | B      |           16 |

The previously verified GPIO mappings were:

```text
Left A  → /dev/gpiochip4 line 11
Left B  → /dev/gpiochip4 line 10
Right A → /dev/gpiochip4 line 12
Right B → /dev/gpiochip1 line 5
```

> These GPIO mappings are board/configuration dependent. Verify them on the ROCK 5C before using the node.

---

# 4.2 Encoder Specifications

Current wheel and encoder values:

```text
Wheel diameter = 2.6 inches
Encoder counts/revolution = 1092
```

Wheel circumference:

```text
C = πD

C = π × 2.6
C ≈ 8.168 inches
```

Distance represented by one encoder count:

```text
8.168 / 1092
≈ 0.00748 inches/count
```

ROS 2 uses SI units, so the node converts the measurements to meters.

---

# 4.3 Verify libgpiod

The encoder node uses the **libgpiod 1.x Python API**.

Check the installed version:

```bash
gpiodetect
```

Also check the Python module:

```bash
python3 -c "import gpiod; print(gpiod.__version__ if hasattr(gpiod, '__version__') else gpiod)"
```

The implementation below uses the older API:

```python
gpiod.Chip()
chip.get_line()
line.request()
line.get_value()
```

This is intentional because the encoder implementation was developed around the libgpiod 1.x API.

---

# 4.4 Create the ROS 2 Package

Go to the ROS 2 workspace:

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_humble/src
```

Create the package:

```bash
ros2 pkg create --build-type ament_python goosebot_sensors --dependencies rclpy nav_msgs
```

The package should contain:

```text
goosebot_sensors/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/
│   └── goosebot_sensors
└── goosebot_sensors/
    ├── __init__.py
    └── encoder_odom.py
```

---

# 4.5 Create `encoder_odom.py`

Create:

```text
~/ros2_humble/src/goosebot_sensors/goosebot_sensors/encoder_odom.py
```

Use:

```python
#!/usr/bin/env python3

import math
import time
import threading

import gpiod
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


# ============================================================
# Goosebot Encoder Configuration
# ============================================================

# GPIO configuration
LEFT_A_CHIP = "/dev/gpiochip4"
LEFT_A_LINE = 11

LEFT_B_CHIP = "/dev/gpiochip4"
LEFT_B_LINE = 10

RIGHT_A_CHIP = "/dev/gpiochip4"
RIGHT_A_LINE = 12

RIGHT_B_CHIP = "/dev/gpiochip1"
RIGHT_B_LINE = 5


# Wheel/encoder configuration
WHEEL_DIAMETER_IN = 2.6
COUNTS_PER_REV = 1092

# IMPORTANT:
# Replace this with the measured distance between the
# centers of the left and right wheels.
WHEEL_BASE_IN = 6.0


# ROS 2 frame/topic names
ODOM_FRAME = "odom"
BASE_FRAME = "base_link"
ODOM_TOPIC = "/wheel/odom"


# Encoder transition table for quadrature decoding
TRANSITION_TABLE = {
    (0, 0, 0, 1): 1,
    (0, 1, 1, 1): 1,
    (1, 1, 1, 0): 1,
    (1, 0, 0, 0): 1,

    (0, 0, 1, 0): -1,
    (1, 0, 1, 1): -1,
    (1, 1, 0, 1): -1,
    (0, 1, 0, 0): -1,
}


def setup_input(chip_path, line_number):
    """
    Open a GPIO input using the libgpiod 1.x API.
    """
    chip = gpiod.Chip(chip_path)
    line = chip.get_line(line_number)

    line.request(
        consumer="goosebot_encoder",
        type=gpiod.LINE_REQ_DIR_IN
    )

    return chip, line


class EncoderOdomNode(Node):

    def __init__(self):
        super().__init__("encoder_odom")

        # ----------------------------------------------------
        # GPIO setup
        # ----------------------------------------------------

        self.left_a_chip, self.left_a = setup_input(
            LEFT_A_CHIP,
            LEFT_A_LINE
        )

        self.left_b_chip, self.left_b = setup_input(
            LEFT_B_CHIP,
            LEFT_B_LINE
        )

        self.right_a_chip, self.right_a = setup_input(
            RIGHT_A_CHIP,
            RIGHT_A_LINE
        )

        self.right_b_chip, self.right_b = setup_input(
            RIGHT_B_CHIP,
            RIGHT_B_LINE
        )

        # ----------------------------------------------------
        # Encoder state
        # ----------------------------------------------------

        self.left_count = 0
        self.right_count = 0

        self.last_left_a = self.left_a.get_value()
        self.last_left_b = self.left_b.get_value()

        self.last_right_a = self.right_a.get_value()
        self.last_right_b = self.right_b.get_value()

        self.last_left_state = (
            self.last_left_a,
            self.last_left_b
        )

        self.last_right_state = (
            self.last_right_a,
            self.last_right_b
        )

        self.count_lock = threading.Lock()

        # ----------------------------------------------------
        # Odometry state
        # ----------------------------------------------------

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.previous_left_count = 0
        self.previous_right_count = 0

        self.previous_time = time.monotonic()

        # ----------------------------------------------------
        # Unit conversions
        # ----------------------------------------------------

        self.wheel_diameter_m = (
            WHEEL_DIAMETER_IN * 0.0254
        )

        self.wheel_circumference_m = (
            math.pi * self.wheel_diameter_m
        )

        self.wheel_base_m = (
            WHEEL_BASE_IN * 0.0254
        )

        self.distance_per_count = (
            self.wheel_circumference_m /
            COUNTS_PER_REV
        )

        # ----------------------------------------------------
        # ROS 2 publisher
        # ----------------------------------------------------

        self.odom_pub = self.create_publisher(
            Odometry,
            ODOM_TOPIC,
            10
        )

        # Update encoder and odometry at 100 Hz
        self.timer = self.create_timer(
            0.01,
            self.update
        )

        self.get_logger().info(
            "Goosebot encoder odometry node started."
        )

        self.get_logger().info(
            f"Wheel diameter: {WHEEL_DIAMETER_IN} in"
        )

        self.get_logger().info(
            f"Counts/revolution: {COUNTS_PER_REV}"
        )

        self.get_logger().info(
            f"Publishing: {ODOM_TOPIC}"
        )

    # ========================================================
    # Encoder reading
    # ========================================================

    def read_encoder_states(self):

        left_a = self.left_a.get_value()
        left_b = self.left_b.get_value()

        right_a = self.right_a.get_value()
        right_b = self.right_b.get_value()

        return (
            (left_a, left_b),
            (right_a, right_b)
        )

    # ========================================================
    # Quadrature decoder
    # ========================================================

    def decode(self, previous_state, current_state):

        previous = (
            previous_state[0],
            previous_state[1]
        )

        current = (
            current_state[0],
            current_state[1]
        )

        transition = (
            previous[0],
            previous[1],
            current[0],
            current[1]
        )

        return TRANSITION_TABLE.get(
            transition,
            0
        )

    # ========================================================
    # Main update
    # ========================================================

    def update(self):

        left_state, right_state = (
            self.read_encoder_states()
        )

        # Decode left encoder
        left_delta = self.decode(
            self.last_left_state,
            left_state
        )

        # Decode right encoder
        right_delta = self.decode(
            self.last_right_state,
            right_state
        )

        with self.count_lock:
            self.left_count += left_delta
            self.right_count += right_delta

        self.last_left_state = left_state
        self.last_right_state = right_state

        # ----------------------------------------------------
        # Calculate distance traveled
        # ----------------------------------------------------

        with self.count_lock:
            current_left = self.left_count
            current_right = self.right_count

        delta_left_count = (
            current_left -
            self.previous_left_count
        )

        delta_right_count = (
            current_right -
            self.previous_right_count
        )

        self.previous_left_count = current_left
        self.previous_right_count = current_right

        delta_left = (
            delta_left_count *
            self.distance_per_count
        )

        delta_right = (
            delta_right_count *
            self.distance_per_count
        )

        # ----------------------------------------------------
        # Differential-drive odometry
        # ----------------------------------------------------

        delta_center = (
            delta_left + delta_right
        ) / 2.0

        delta_theta = (
            delta_right - delta_left
        ) / self.wheel_base_m

        # Use the midpoint heading during the update
        theta_mid = (
            self.theta +
            delta_theta / 2.0
        )

        self.x += (
            delta_center *
            math.cos(theta_mid)
        )

        self.y += (
            delta_center *
            math.sin(theta_mid)
        )

        self.theta += delta_theta

        # Keep theta within -π to +π
        self.theta = math.atan2(
            math.sin(self.theta),
            math.cos(self.theta)
        )

        # ----------------------------------------------------
        # Velocity calculation
        # ----------------------------------------------------

        current_time = time.monotonic()

        dt = (
            current_time -
            self.previous_time
        )

        self.previous_time = current_time

        if dt <= 0.0:
            return

        linear_velocity = (
            delta_center / dt
        )

        angular_velocity = (
            delta_theta / dt
        )

        # ----------------------------------------------------
        # Publish Odometry
        # ----------------------------------------------------

        msg = Odometry()

        msg.header.stamp = (
            self.get_clock().now().to_msg()
        )

        msg.header.frame_id = ODOM_FRAME
        msg.child_frame_id = BASE_FRAME

        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.position.z = 0.0

        # Convert yaw to quaternion
        msg.pose.pose.orientation.z = (
            math.sin(self.theta / 2.0)
        )

        msg.pose.pose.orientation.w = (
            math.cos(self.theta / 2.0)
        )

        msg.twist.twist.linear.x = (
            linear_velocity
        )

        msg.twist.twist.linear.y = 0.0
        msg.twist.twist.linear.z = 0.0

        msg.twist.twist.angular.z = (
            angular_velocity
        )

        self.odom_pub.publish(msg)

    # ========================================================
    # Shutdown
    # ========================================================

    def destroy_node(self):

        try:
            self.left_a.release()
            self.left_b.release()
            self.right_a.release()
            self.right_b.release()
        except Exception:
            pass

        try:
            self.left_a_chip.close()
            self.left_b_chip.close()
            self.right_a_chip.close()
            self.right_b_chip.close()
        except Exception:
            pass

        super().destroy_node()


def main(args=None):

    rclpy.init(args=args)

    node = None

    try:
        node = EncoderOdomNode()
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"Encoder node error: {e}")

    finally:

        if node is not None:
            node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()
```

---

# 4.6 Create `setup.py`

File:

```text
~/ros2_humble/src/goosebot_sensors/setup.py
```

Use:

```python
from setuptools import setup

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

---

# 4.7 Create `setup.cfg`

File:

```text
~/ros2_humble/src/goosebot_sensors/setup.cfg
```

Use:

```ini
[develop]
script_dir=$base/lib/goosebot_sensors

[install]
install_scripts=$base/lib/goosebot_sensors
```

---

# 4.8 Create `package.xml`

File:

```text
~/ros2_humble/src/goosebot_sensors/package.xml
```

Use:

```xml
<?xml version="1.0"?>
<package format="3">

  <name>goosebot_sensors</name>
  <version>0.0.0</version>

  <description>
    Goosebot encoder and wheel odometry ROS 2 package.
  </description>

  <maintainer email="user@example.com">
    Goosebot
  </maintainer>

  <license>Apache-2.0</license>

  <buildtool_depend>ament_python</buildtool_depend>

  <depend>rclpy</depend>
  <depend>nav_msgs</depend>

  <export>
    <build_type>ament_python</build_type>
  </export>

</package>
```

The email above is only package metadata and does not affect the encoder node.

---

# 4.9 Create the Resource File

Create:

```text
~/ros2_humble/src/goosebot_sensors/resource/goosebot_sensors
```

The file can be empty.

---

# 4.10 Make Sure `__init__.py` Exists

Create:

```text
~/ros2_humble/src/goosebot_sensors/goosebot_sensors/__init__.py
```

The file can be empty.

---

# 4.11 Build the Package

Go to the workspace:

```bash
cd ~/ros2_humble
```

Source ROS 2:

```bash
source /opt/ros/humble/setup.bash
```

Build only the encoder package:

```bash
colcon build --packages-select goosebot_sensors
```

If the build succeeds:

```bash
source ~/ros2_humble/install/setup.bash
```

---

# 4.12 Verify the ROS 2 Package

Check that ROS 2 can see the package:

```bash
ros2 pkg list | grep goosebot_sensors
```

Expected:

```text
goosebot_sensors
```

Check the executable:

```bash
ros2 pkg executables goosebot_sensors
```

Expected:

```text
goosebot_sensors encoder_odom
```

---

# 4.13 Run the Encoder Node

Source the workspace:

```bash
source ~/ros2_humble/install/setup.bash
```

Run:

```bash
ros2 run goosebot_sensors encoder_odom
```

Expected startup messages should look similar to:

```text
[INFO] [encoder_odom]: Goosebot encoder odometry node started.
[INFO] [encoder_odom]: Wheel diameter: 2.6 in
[INFO] [encoder_odom]: Counts/revolution: 1092
[INFO] [encoder_odom]: Publishing: /wheel/odom
```

Leave this terminal running.

---

# 4.14 Check the Odometry Topic

Open a second terminal.

Source ROS 2:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

Check the topic list:

```bash
ros2 topic list
```

You should see:

```text
/wheel/odom
```

Check the message type:

```bash
ros2 topic type /wheel/odom
```

Expected:

```text
nav_msgs/msg/Odometry
```

---

# 4.15 View the Encoder Odometry

Run:

```bash
ros2 topic echo /wheel/odom
```

You should see messages containing:

```text
pose:
  pose:
    position:
      x:
      y:
      z:
```

and:

```text
twist:
  twist:
    linear:
      x:
    angular:
      z:
```

The position and velocity values should change when the robot moves.

---

# 4.16 Check Publishing Frequency

Run:

```bash
ros2 topic hz /wheel/odom
```

The node is configured for a 100 Hz update timer, so the measured frequency should be approximately:

```text
100 Hz
```

The exact measured frequency may vary depending on CPU load and system timing.

---

# 4.17 Test Forward Motion

With the robot safely supported or on the ground:

1. Start the encoder node.
2. Reset the node by restarting it if necessary.
3. Move the robot forward.
4. Watch:

```bash
ros2 topic echo /wheel/odom
```

Expected behavior:

```text
x → changes
y → approximately constant
yaw → approximately constant
```

The exact sign depends on the encoder wiring and motor orientation.

---

# 4.18 Test Turning

Rotate the robot.

Watch:

```bash
ros2 topic echo /wheel/odom
```

Expected behavior:

```text
yaw → changes
```

For differential-drive odometry:

```text
Δθ = (Δright - Δleft) / wheel_base
```

Therefore, the difference between the left and right wheel movements determines the estimated turn.

---

# 4.19 Important: Wheelbase

The code currently contains:

```python
WHEEL_BASE_IN = 6.0
```

This is a **placeholder**.

The wheelbase should be measured from the center of the left wheel to the center of the right wheel.

For example:

```text
Left wheel center
       ●
       |<------ wheel base ------>|
       ●
Right wheel center
```

Replace:

```python
WHEEL_BASE_IN = 6.0
```

with the actual measured value before relying on the odometry for accurate navigation or EKF fusion.

---

# 4.20 Troubleshooting

### Package not found

Run:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

Then:

```bash
ros2 pkg list | grep goosebot_sensors
```

---

### Executable not found

Check:

```bash
ros2 pkg executables goosebot_sensors
```

If `encoder_odom` is missing, rebuild:

```bash
cd ~/ros2_humble
colcon build --packages-select goosebot_sensors
source ~/ros2_humble/install/setup.bash
```

---

### GPIO permission error

Check the GPIO devices:

```bash
ls -l /dev/gpiochip*
```

If the node cannot access the GPIO lines, test the GPIO configuration and permissions before modifying the encoder code.

---

### GPIO line is busy

Another program may already be using the GPIO line.

Check which processes are running and stop other encoder/GPIO programs before launching the ROS 2 node.

---

### Encoder counts move backward

If forward movement produces negative counts, the encoder A/B phase may be reversed.

The affected encoder's A/B inputs can be swapped, or the decoding direction can be inverted in software.

Do not change the GPIO mapping until the physical wiring has been verified.

---

# 4.21 Step 4 Completion Checkpoint

Step 4 is complete when all of the following work:

* [ ] Encoder hardware is connected.
* [ ] GPIO lines are accessible.
* [ ] libgpiod 1.x API works.
* [ ] `goosebot_sensors` builds successfully.
* [ ] `encoder_odom` executable exists.
* [ ] Encoder node starts successfully.
* [ ] `/wheel/odom` exists.
* [ ] `/wheel/odom` has type `nav_msgs/msg/Odometry`.
* [ ] Encoder movement changes odometry.
* [ ] Forward movement changes position.
* [ ] Turning changes yaw.
* [ ] Linear velocity is published.
* [ ] Angular velocity is published.
* [ ] Actual wheelbase has been measured before using the odometry for serious navigation.

---

# Step 4 Data Path

At the end of this step, Goosebot should have:

```text
LEFT ENCODER ──┐
               │
               ├──> encoder_odom.py
               │          │
RIGHT ENCODER ─┘          ↓
                     Wheel Odometry
                          │
                          ↓
                     /wheel/odom
                          │
                          ↓
                 nav_msgs/msg/Odometry
```

The next fusion stage will take this already-working wheel odometry and combine it with the **IMU** and **GPS**.

```text
                    /imu/data
                        │
                        │
                        ↓
/wheel/odom ────────> EKF ───────> /odometry/filtered
                        ↑
                        │
                 GPS / navsat
```

**Do not add the IMU or GPS to the Step 4 encoder node.** Their purpose is to be independently verified first and then connected during the EKF/fusion stage.
