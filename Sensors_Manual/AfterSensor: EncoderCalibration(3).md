# ROCK 5C — ROS 2 Sensor Setup

This guide documents the setup from the ROS 2 workspace through wheel encoder and IMU publishing, with troubleshooting notes from the development process.

The goal is to reach:

```
Sensors
   ↓
ROS 2 Python Nodes
   ↓
ROS 2 Topics
   ↓
robot_localization
   ↓
Navigation
```

---

# 1. ROS 2 Workspace

The ROS 2 workspace used for this project is:

```
~/ros2_humble
```

The source folder is:

```
~/ros2_humble/src
```

If the workspace does not exist:

```
mkdir -p ~/ros2_humble/src
cd ~/ros2_humble
```

---

# 2. ROS 2 Environment

Before using ROS 2 commands, source the ROS 2 environment.

If using the workspace:

```
source ~/ros2_humble/install/setup.bash
```

This may need to be done again when opening a new terminal.

If `ros2` is not found, source the workspace again.

Check:

```
ros2 --version
```

---

# 3. ROS 2 Tools

This project uses:

* ROS 2
* Python
* `colcon`
* `rosdep`
* `gpiod`
* GPIO encoder inputs
* MPU6050 IMU
* `robot_localization`

Check `rosdep`:

```
rosdep --version
```

If `rosdep` was installed locally and the command cannot be found, make sure the local Python bin directory is in PATH:

```
export PATH=$HOME/.local/bin:$PATH
```

To make this permanent:

```
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
```

Then reload:

```
source ~/.bashrc
```

---

# 4. Create the Sensor Package

Go into the ROS 2 source directory:

```
cd ~/ros2_humble/src
```

Create the Python package:

```
ros2 pkg create --build-type ament_python goosebot_sensors
```

The package is used for the robot's sensor nodes.

The important package structure is:

```
~/ros2_humble/
└── src/
    └── goosebot_sensors/
        ├── package.xml
        ├── setup.py
        └── goosebot_sensors/
            ├── __init__.py
            ├── encoder_odom.py
            ├── imu_publisher.py
            └── tf_broadcaster.py
```

---

# 5. Python Sensor Nodes

The project uses separate Python ROS 2 nodes for different sensors.

## encoder_odom.py

Location:

```
~/ros2_humble/src/goosebot_sensors/goosebot_sensors/encoder_odom.py
```

Purpose:

* Read the left encoder.
* Read the right encoder.
* Track encoder counts.
* Convert encoder counts to wheel movement.
* Calculate velocity.
* Publish wheel odometry.

Published topic:

```
/wheel/odom
```

Message type:

```
nav_msgs/Odometry
```

Current encoder values:

```
COUNTS_PER_REV = 1092
WHEEL_DIAMETER_IN = 2.6
TRACK_WIDTH_IN = 5.3
```

---

# 6. Encoder Hardware

The encoder motors use GPIO inputs on the ROCK 5C.

Current physical pin assignments:

* Left encoder: physical pins 11 and 13
* Right encoder: physical pins 15 and 16

Before testing:

* Encoder power must be connected.
* Encoder GND must be connected to ROCK 5C GND.
* Encoder signal wires must be connected to the correct GPIO pins.

---

# 7. Check GPIO Configuration

Run:

```
gpioinfo
```

Use this to determine the GPIO chip and line associated with the physical pins.

The GPIO lines should not already be occupied by another program.

If a GPIO is already being used, an error such as:

```
Device or resource busy
```

may occur.

---

# 8. Test the Encoder Before ROS 2

Before involving ROS 2, make sure the physical encoder works.

Go to:

```
cd ~/goose/04_motor_test
```

If using the virtual environment:

```
source venv/bin/activate
```

Run the encoder test:

```
sudo python motor_encoder_keyboard_v4.py
```

Rotate the wheels.

The encoder counts should change when the wheels rotate.

Do not move to the ROS 2 portion until the encoder itself is working.

---

# 9. Troubleshoot Encoder GPIO

If an encoder does not count, first determine whether the GPIO is receiving pulses.

Check the GPIO:

```
gpioinfo
```

Then monitor the appropriate GPIO:

```
gpiomon /dev/gpiochipX LINE
```

Replace `X` and `LINE` with the correct GPIO chip and line.

Rotate the wheel.

## If events appear

The GPIO is receiving encoder pulses.

The problem is probably in the Python encoder code or its GPIO configuration.

## If no events appear

Check:

1. Encoder power
2. Encoder GND
3. Encoder signal wiring
4. GPIO pin mapping
5. Encoder hardware

## If only one encoder works

Swap the signal wires between the working and non-working inputs.

This helps determine whether the problem is:

```
Encoder
   ↓
Wiring
   ↓
GPIO pin
   ↓
GPIO chip
   ↓
Python code
```

---

# 10. Encoder Calibration

The measured encoder calibration is:

```
COUNTS_PER_REV = 1092
```

Current wheel diameter:

```
2.6 inches
```

Track width:

```
5.3 inches
```

Wheel circumference:

```
π × 2.6 inches
```

Distance from encoder counts:

```
distance = (counts / 1092) × (π × 2.6)
```

If the wheels or encoder configuration changes, these values may need to be recalibrated.

---

# 11. libgpiod

The encoder code uses `gpiod`.

Check the installed version:

```
gpiodetect --version
```

Check the Python version:

```
python3 -c "import gpiod; print(gpiod.__version__)"
```

## Important libgpiod Issue

During development, the Python `gpiod` API and the installed version did not always match.

For example, code using:

```
gpiod.request_lines()
```

may fail when an older Python `gpiod` API is installed.

If a `gpiod` error occurs:

1. Check the installed version.
2. Check which API the code uses.
3. Make the code and installed version compatible.

Do not assume that a GPIO problem is a ROS 2 problem.

---

# 12. Create the ROS 2 Encoder Node

Once the standalone encoder test works, the encoder can be connected to ROS 2.

The encoder ROS 2 node is:

```
goosebot_sensors/encoder_odom.py
```

It reads the encoder GPIOs and publishes:

```
/wheel/odom
```

The basic data flow is:

```
Left Encoder ──┐
               ├──> encoder_odom.py
Right Encoder ─┘          ↓
                     /wheel/odom
                          ↓
                   robot_localization
```

---

# 13. Configure setup.py

ROS 2 needs to know how to launch the Python nodes.

The `setup.py` file is located at:

```
~/ros2_humble/src/goosebot_sensors/setup.py
```

The Python nodes need to be registered as console scripts.

For example, the encoder node should have an entry point corresponding to:

```
encoder_odom = goosebot_sensors.encoder_odom:main
```

The exact entry-point names must match the Python files and their `main()` functions.

If `setup.py` is changed, rebuild the package afterward.

---

# 14. Build the ROS 2 Package

From the workspace:

```
cd ~/ros2_humble
```

Build the sensor package:

```
colcon build --packages-select goosebot_sensors --symlink-install
```

Then source the new installation:

```
source install/setup.bash
```

The `--symlink-install` option is useful when developing Python ROS 2 packages because Python files can be used directly from the source workspace.

---

# 15. Important: Rebuild After Changes

The normal development cycle is:

```
Edit Python code
      ↓
colcon build
      ↓
source install/setup.bash
      ↓
Run node
      ↓
Test
      ↓
Find problem
      ↓
Edit code again
```

For changes to the Python nodes, use:

```
cd ~/ros2_humble
colcon build --packages-select goosebot_sensors --symlink-install
source install/setup.bash
```

Then run the node again.

If `setup.py`, package dependencies, entry points, or other package configuration changes, a rebuild is required.

---

# 16. Run the Encoder ROS 2 Node

After building:

```
source ~/ros2_humble/install/setup.bash
```

Run:

```
ros2 run goosebot_sensors encoder_odom
```

Leave the node running.

Open another terminal and source the workspace:

```
source ~/ros2_humble/install/setup.bash
```

---

# 17. Verify the Encoder ROS 2 Topic

Check the available topics:

```
ros2 topic list
```

Look for:

```
/wheel/odom
```

Check the actual data:

```
ros2 topic echo /wheel/odom
```

Rotate the wheels.

The odometry values should change.

The `nav_msgs/Odometry` message contains:

* Position
* Orientation
* Linear velocity
* Angular velocity

---

# 18. Check the Publishing Rate

Run:

```
ros2 topic hz /wheel/odom
```

This shows how frequently the encoder node is publishing.

A continuously publishing node should produce a consistent rate.

---

# 19. Check the Running Nodes

If something does not work:

```
ros2 node list
```

This shows which ROS 2 nodes are currently running.

If the encoder node is not listed, it is not running correctly.

---

# 20. Important: Do Not Run Multiple Encoder Nodes

Only run one copy of the encoder node at a time.

If `encoder_odom` is already running and another copy is started, the second copy may attempt to claim the same GPIO pins.

This can produce:

```
Device or resource busy
```

If this happens, check the running ROS 2 nodes:

```
ros2 node list
```

Stop the existing encoder node before starting another copy.

---

# 21. `/wheel/odom` Does Not Appear

Check:

```
ros2 node list
```

Then:

```
ros2 topic list
```

If `encoder_odom` is not listed:

1. Check that the node was started.
2. Check for Python errors in the terminal.
3. Make sure the workspace was sourced.
4. Rebuild if the Python/package files were changed.

Rebuild:

```
cd ~/ros2_humble
colcon build --packages-select goosebot_sensors --symlink-install
source install/setup.bash
```

Then run again:

```
ros2 run goosebot_sensors encoder_odom
```

---

# 22. `/wheel/odom` Exists but Does Not Change

Do not immediately modify the ROS 2 code.

Work backward through the system:

```
/wheel/odom
     ↓
encoder_odom.py
     ↓
Python encoder code
     ↓
GPIO
     ↓
Wiring
     ↓
Encoder hardware
```

First check whether the GPIO receives pulses:

```
gpioinfo
```

Then:

```
gpiomon /dev/gpiochipX LINE
```

If `gpiomon` receives pulses but `/wheel/odom` does not change, investigate the Python/ROS 2 node.

If `gpiomon` receives no pulses, investigate the hardware/GPIO side first.

---

# 23. IMU ROS 2 Node

The MPU6050 is used as the robot's IMU.

The ROS 2 Python node is:

```
imu_publisher.py
```

Location:

```
~/ros2_humble/src/goosebot_sensors/goosebot_sensors/imu_publisher.py
```

Its purpose is to read the MPU6050 and publish IMU data to ROS 2.

The IMU hardware used:

```
GY-521 MPU6050
```

Current connections:

* VCC → physical pin 1
* GND → physical pin 9
* SDA → physical pin 27
* SCL → physical pin 28

The IMU data is intended to be used by `robot_localization`.

---

# 24. TF Broadcaster

The project also uses:

```
tf_broadcaster.py
```

Its purpose is to provide the appropriate TF relationship between the robot base and the IMU frame.

This becomes important when ROS 2 and `robot_localization` need to understand where the IMU is mounted relative to the robot.

---

# 25. Build After Adding IMU or TF Code

Whenever adding or modifying:

```
encoder_odom.py
imu_publisher.py
tf_broadcaster.py
```

rebuild:

```
cd ~/ros2_humble
colcon build --packages-select goosebot_sensors --symlink-install
```

Then:

```
source install/setup.bash
```

---

# 26. General ROS 2 Troubleshooting

## `ros2: command not found`

Source the workspace:

```
source ~/ros2_humble/install/setup.bash
```

If the workspace has not been built yet, build it first.

---

## Package cannot be found

Check that the package is inside:

```
~/ros2_humble/src
```

Then:

```
cd ~/ros2_humble
colcon build --packages-select goosebot_sensors --symlink-install
source install/setup.bash
```

---

## Python changes do not appear

Rebuild and source:

```
cd ~/ros2_humble
colcon build --packages-select goosebot_sensors --symlink-install
source install/setup.bash
```

Then restart the node.

---

## `Device or resource busy`

Possible causes include:

* Another program is using the GPIO.
* Another copy of `encoder_odom` is running.
* A previous encoder process was not stopped.

Check:

```
gpioinfo
```

And:

```
ros2 node list
```

Stop the conflicting process before trying again.

---

## `gpiod` API error

Check:

```
gpiodetect --version

python3 -c "import gpiod; print(gpiod.__version__)"
```

Make sure the code uses the API supported by the installed version.

---

# 27. Troubleshooting Order

Always troubleshoot from the bottom upward.

```
1. Hardware
       ↓
2. Wiring
       ↓
3. GPIO
       ↓
4. Standalone Python code
       ↓
5. ROS 2 Python node
       ↓
6. ROS 2 topic
       ↓
7. robot_localization
       ↓
8. Navigation
```

Do not troubleshoot the EKF if the sensor's ROS 2 topic is not working.

---

# 28. Current Encoder Checkpoint

At the encoder stage, the system should look like:

```
Wheel
  ↓
Encoder
  ↓
GPIO
  ↓
encoder_odom.py
  ↓
ROS 2
  ↓
/wheel/odom
  ↓
Verified with:
ros2 topic echo /wheel/odom
```

Once this works, the wheel encoder data is ready to be used by `robot_localization`.

---

# 29. Sensor Fusion Checkpoint

The eventual sensor-fusion architecture is:

```
Wheel Encoders ──> /wheel/odom ──────┐
                                     │
MPU6050 ────────> /imu/data ─────────┤
                                     ↓
                              robot_localization
                                     ↓
                              /odometry/filtered
                                     ↑
                                     │
GPS ────────────> GPS topic ─────────┘
```

The EKF combines the different measurements into a better estimate of the robot's position, velocity, and orientation.

---

# 30. Final Development Workflow

For future development, use this sequence:

```
1. Change a Python file.
2. Save the file.
3. Build the package:

   cd ~/ros2_humble
   colcon build --packages-select goosebot_sensors --symlink-install

4. Source the workspace:

   source install/setup.bash

5. Start the node:

   ros2 run goosebot_sensors encoder_odom

6. Check the node:

   ros2 node list

7. Check the topic:

   ros2 topic list

8. Check the data:

   ros2 topic echo /wheel/odom

9. Check publishing rate:

   ros2 topic hz /wheel/odom
```

10. Stop the node before starting another copy.

---

# Final Goal

The complete system being built is:

```
ROCK 5C
   │
   ├── Wheel Encoders
   │       ↓
   │   encoder_odom.py
   │       ↓
   │   /wheel/odom
   │
   ├── MPU6050
   │       ↓
   │   imu_publisher.py
   │       ↓
   │   IMU ROS 2 topic
   │
   └── GPS
           ↓
       GPS ROS 2 topic
            │
            ↓
    robot_localization
            │
            ↓
    /odometry/filtered
            │
            ↓
         Nav2
```

The important rule is:

**Get each sensor working by itself → publish it to ROS 2 → verify its topic → then connect it to sensor fusion → then move to navigation.**
