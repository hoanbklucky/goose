# Goosebot — Sensor Hardware Verification

This step verifies that each sensor is physically detected by the ROCK 5C and can produce valid measurements **before connecting the sensors to the ROS 2 EKF**.

## 1. Verify ROCK 5C Interfaces

Check available I²C buses:

```bash
ls /dev/i2c*
```

Check available UART ports:

```bash
ls -l /dev/ttyS*
```

Check GPIO chips:

```bash
gpiodetect
```

Install the required diagnostic tools:

```bash
sudo apt update
sudo apt install -y i2c-tools gpiod libgpiod-dev
```

---

# 2. I²C Sensor Detection

The I²C bus must be verified on the actual ROCK 5C installation. Do not assume the bus number is identical on every system.

The I²C bus used during Goosebot testing was:

```bash
sudo i2cdetect -y 6
```

Expected devices:

| Address | Device       |
| ------- | ------------ |
| `0x29`  | VL53L1X ToF  |
| `0x40`  | PCA9685      |
| `0x68`  | MPU-6050 IMU |

Example:

```text
     0 1 2 3 4 5 6 7 8 9 a b c d e f
00:          -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- 29
30: -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- 68 -- -- --
70: -- -- -- -- -- -- -- --
```

If the expected address appears, the ROCK 5C can communicate with the device at the I²C level.

---

# 3. MPU-6050 IMU Verification

## 3.1 Detect the IMU

```bash
sudo i2cdetect -y 6
```

Expected:

```text
0x68
```

## 3.2 Verify the IMU is responding

Read the WHO_AM_I register:

```bash
sudo i2cget -y 6 0x68 0x75
```

Expected response:

```text
0x68
```

This confirms that the IMU responds to I²C commands.

## 3.3 ROS 2 Verification

After the IMU ROS 2 node is running:

```bash
ros2 node list
```

Then:

```bash
ros2 topic list
```

Find the IMU topic and inspect it:

```bash
ros2 topic echo /imu/data
```

Check its publishing rate:

```bash
ros2 topic hz /imu/data
```

A functioning IMU should continuously provide acceleration and angular velocity measurements.

---

# 4. VL53L1X ToF Verification

## 4.1 Detect the ToF sensor

```bash
sudo i2cdetect -y 6
```

Expected:

```text
0x29
```

## 4.2 Python test

Activate the Goosebot virtual environment:

```bash
source ~/goosebot_venv/bin/activate
```

Install the required library:

```bash
pip install adafruit-circuitpython-vl53l1x
```

Create:

```bash
nano ~/tof_test.py
```

Test the sensor and verify that it produces distance measurements.

Example expected output:

```text
Opening I2C bus...
VL53L1X detected!
Distance: 42 cm
Distance: 41 cm
Distance: 42 cm
```

If the distance changes when an object is moved closer or farther away, the ToF sensor is functioning.

---

# 5. PCA9685 Verification

## 5.1 Detect the PCA9685

```bash
sudo i2cdetect -y 6
```

Expected:

```text
0x40
```

## 5.2 Python test

Activate the virtual environment:

```bash
source ~/goosebot_venv/bin/activate
```

Install the required libraries:

```bash
pip install adafruit-extended-bus adafruit-circuitpython-pca9685
```

Create:

```bash
nano ~/pca9685_test.py
```

Use:

```python
import board
import busio
from adafruit_pca9685 import PCA9685

print("Initializing I2C...")

i2c = busio.I2C(board.SCL, board.SDA)

pca = PCA9685(i2c)
pca.frequency = 1000

print("PCA9685 detected!")
print("Address: 0x40")
print("PWM frequency: 1000 Hz")

pca.deinit()
```

Run:

```bash
python3 ~/pca9685_test.py
```

Expected:

```text
Initializing I2C...
PCA9685 detected!
Address: 0x40
PWM frequency: 1000 Hz
```

---

# 6. Encoder Verification

The wheel encoders are Hall-effect sensors connected to the motor gearboxes.

Unlike the IMU, ToF, and PCA9685, the encoders are read through **GPIO**.

The purpose of this test is to verify:

1. The ROCK 5C can access the encoder GPIO.
2. The encoder generates pulses when the wheel rotates.
3. The pulse count changes correctly.
4. Encoder counts can be converted into wheel distance.
5. The encoder is ready to be converted into ROS 2 wheel odometry.

---

## 6.1 Encoder Parameters

Current Goosebot parameters:

```text
Encoder type: Hall-effect encoder
Counts per revolution: 1092
Wheel diameter: 2.6 inches
```

Wheel circumference:

```text
C = π × D

C = π × 2.6

C ≈ 8.168 inches
```

Therefore:

```text
1092 counts ≈ 8.168 inches
```

Distance per encoder count:

```text
8.168 / 1092

≈ 0.00748 inches/count
```

---

## 6.2 GPIO Library Requirement

**Goosebot requires the `libgpiod 1.6.3` GPIO interface.**

The encoder code is based on the **libgpiod 1.x / Python gpiod 1.x API**.

Do **NOT** use examples written for `gpiod 2.x`.

The older API uses functions such as:

```python
chip.get_line()
```

and:

```python
line.request()
```

The newer 2.x API uses a different interface, including:

```python
request_lines()
```

These APIs are not interchangeable.

### Required GPIO version

```text
libgpiod = 1.6.3
Python gpiod = 1.x API
```

Verify the installed system library:

```bash
dpkg -l | grep libgpiod
```

You can also check:

```bash
apt policy libgpiod2
```

Check the Python package:

```bash
python3 -c "import gpiod; print(gpiod.__version__)"
```

If available:

```bash
python3 -c "import gpiod; print(gpiod.version_string())"
```

The encoder implementation should be kept compatible with the **1.6.3/libgpiod 1.x environment used by Goosebot**.

---

## 6.3 Check GPIO Hardware

Run:

```bash
gpiodetect
```

Then:

```bash
gpioinfo
```

This verifies that Linux recognizes the GPIO controller.

Example:

```text
gpiochip0
gpiochip1
...
```

The actual encoder GPIO lines must correspond to the physical wiring on the ROCK 5C.

### Important

The previously used motor-control GPIO offsets:

```text
IN1 = 7
IN2 = 6
IN3 = 5
IN4 = 4
```

are **motor-control outputs**.

They should **not automatically be assumed to be the encoder inputs**.

Document the actual encoder wiring here:

```text
Left Encoder:
    Encoder A → GPIO ______
    Encoder B → GPIO ______

Right Encoder:
    Encoder A → GPIO ______
    Encoder B → GPIO ______
```

Determine these values using the actual ROCK 5C wiring and:

```bash
gpioinfo
```

---

# 6.4 libgpiod 1.x Encoder Test

Once the actual encoder GPIO offsets are known, the encoder can be read using the libgpiod 1.x API.

The basic structure is:

```python
import gpiod

chip = gpiod.Chip("/dev/gpiochip1")

line = chip.get_line(ENCODER_PIN)

line.request(
    consumer="goosebot_encoder",
    type=gpiod.LINE_REQ_EV_BOTH_EDGES
)
```

This is intentionally written for the **older gpiod 1.x API**.

Do not replace it with:

```python
gpiod.request_lines(...)
```

because that belongs to the newer gpiod 2.x API.

---

# 6.5 Encoder Test Program

Create:

```bash
nano ~/encoder_test.py
```

Use the following structure after replacing the GPIO values with the actual encoder inputs:

```python
#!/usr/bin/env python3

import time
import gpiod

# ============================================================
# GOOSEBOT ENCODER TEST
# libgpiod 1.x / libgpiod 1.6.3
# ============================================================

GPIO_CHIP = "/dev/gpiochip1"

# Replace these with the ACTUAL encoder GPIO offsets.
LEFT_ENCODER_A = 0
LEFT_ENCODER_B = 1

RIGHT_ENCODER_A = 2
RIGHT_ENCODER_B = 3

COUNTS_PER_REV = 1092
WHEEL_DIAMETER_IN = 2.6

WHEEL_CIRCUMFERENCE_IN = (
    3.14159265359 * WHEEL_DIAMETER_IN
)

INCHES_PER_COUNT = (
    WHEEL_CIRCUMFERENCE_IN / COUNTS_PER_REV
)

left_count = 0
right_count = 0


def counts_to_inches(counts):
    return counts * INCHES_PER_COUNT


print("========================================")
print("       GOOSEBOT ENCODER TEST")
print("========================================")
print("GPIO API: libgpiod 1.x")
print("Required libgpiod: 1.6.3")
print("----------------------------------------")
print(f"Counts/revolution : {COUNTS_PER_REV}")
print(f"Wheel diameter    : {WHEEL_DIAMETER_IN} in")
print(
    f"Wheel circumference: "
    f"{WHEEL_CIRCUMFERENCE_IN:.3f} in"
)
print(
    f"Distance/count    : "
    f"{INCHES_PER_COUNT:.6f} in"
)
print("----------------------------------------")
print("Rotate the wheels manually.")
print("Press CTRL+C to stop.")
print("----------------------------------------")


# ------------------------------------------------------------
# GPIO initialization
# ------------------------------------------------------------

chip = gpiod.Chip(GPIO_CHIP)

left_a = chip.get_line(LEFT_ENCODER_A)
left_b = chip.get_line(LEFT_ENCODER_B)

right_a = chip.get_line(RIGHT_ENCODER_A)
right_b = chip.get_line(RIGHT_ENCODER_B)

left_a.request(
    consumer="goosebot_left_encoder_a",
    type=gpiod.LINE_REQ_EV_BOTH_EDGES
)

left_b.request(
    consumer="goosebot_left_encoder_b",
    type=gpiod.LINE_REQ_EV_BOTH_EDGES
)

right_a.request(
    consumer="goosebot_right_encoder_a",
    type=gpiod.LINE_REQ_EV_BOTH_EDGES
)

right_b.request(
    consumer="goosebot_right_encoder_b",
    type=gpiod.LINE_REQ_EV_BOTH_EDGES
)


try:

    while True:

        # ----------------------------------------------------
        # Encoder event processing
        #
        # The exact quadrature state machine should be added
        # once the actual encoder A/B GPIO wiring is confirmed.
        # ----------------------------------------------------

        print(
            f"\rLeft: {left_count:6d} counts "
            f"({counts_to_inches(left_count):8.3f} in)   "
            f"Right: {right_count:6d} counts "
            f"({counts_to_inches(right_count):8.3f} in)",
            end=""
        )

        time.sleep(0.1)


except KeyboardInterrupt:

    print("\n\nEncoder test stopped.")


finally:

    left_a.release()
    left_b.release()
    right_a.release()
    right_b.release()

    chip.close()
```

> **Important:** The GPIO offsets in this example are placeholders. They must be replaced with the actual encoder GPIO offsets. The code should not be used with guessed GPIO numbers.

---

# 6.6 Encoder Functional Test

After starting the test:

```bash
python3 ~/encoder_test.py
```

The initial state should resemble:

```text
========================================
       GOOSEBOT ENCODER TEST
========================================
GPIO API: libgpiod 1.x
Required libgpiod: 1.6.3
----------------------------------------
Counts/revolution : 1092
Wheel diameter    : 2.6 in
Wheel circumference: 8.168 in
Distance/count    : 0.007480 in
----------------------------------------
Rotate the wheels manually.
Press CTRL+C to stop.
----------------------------------------

Left:      0 counts (   0.000 in)
Right:     0 counts (   0.000 in)
```

Rotate a wheel.

The corresponding count should change:

```text
Left:     25 counts (   0.187 in)
Right:     0 counts (   0.000 in)
```

Continue rotating:

```text
Left:     50 counts (   0.374 in)
Right:     0 counts (   0.000 in)
```

This confirms that the GPIO encoder is generating detectable events.

---

# 6.7 Encoder Direction Test

For a quadrature encoder, rotate the wheel forward:

```text
0 → 10 → 20 → 30 → 40
```

Then rotate it backward:

```text
40 → 30 → 20 → 10 → 0
```

If the count always increases, the test may only be reading encoder pulses rather than decoding direction.

A proper quadrature implementation uses both encoder channels:

```text
Encoder A ──┐
             ├──> Quadrature decoder ──> ± counts
Encoder B ──┘
```

---

# 6.8 One-Revolution Test

Mark the wheel with tape.

Reset the encoder count:

```text
Left = 0
Right = 0
```

Rotate the wheel exactly one revolution.

Expected:

```text
Encoder ≈ 1092 counts
```

Physical distance:

```text
Distance = π × 2.6

Distance ≈ 8.168 inches
```

Therefore:

```text
1 wheel revolution
≈ 1092 encoder counts
≈ 8.168 inches
```

Some variation may occur depending on whether the specified encoder count represents pulses, edges, or decoded quadrature counts.

---

# 6.9 Encoder Verification Checklist

Before moving to ROS 2 wheel odometry:

```text
[ ] GPIO subsystem detected
[ ] libgpiod 1.6.3 installed
[ ] Python gpiod uses 1.x API
[ ] Correct encoder GPIO pins identified
[ ] Encoder GPIO inputs can be accessed
[ ] Left encoder generates pulses
[ ] Right encoder generates pulses
[ ] Counts change when wheels rotate
[ ] Forward rotation verified
[ ] Reverse rotation verified
[ ] Counts/revolution verified
[ ] Wheel diameter = 2.6 inches
[ ] Wheel circumference ≈ 8.168 inches
[ ] Distance/count ≈ 0.00748 inches
```

---

# 6.10 Encoder Checkpoint

The encoder portion of Goosebot is considered functional when:

```text
Wheel rotates
      ↓
Hall encoder produces pulses
      ↓
ROCK 5C GPIO detects pulses
      ↓
libgpiod 1.6.3 reads GPIO events
      ↓
Encoder count changes
      ↓
Count converted to wheel distance
      ↓
Ready for ROS 2 /odom
```

The next stage is to convert the encoder measurements into a ROS 2 wheel-odometry node.

The eventual localization chain is:

```text
Encoder
   ↓
Wheel Odometry
   ↓
/odom
   ↓
robot_localization EKF
```

The encoder should be verified independently before it is connected to the EKF.

# 7. GPS — SAM-M8Q Verification

The GPS communicates through UART.

## 7.1 Check UART

```bash
ls -l /dev/ttyS*
```

The UART used during Goosebot testing was:

```text
/dev/ttyS4
```

## 7.2 Check raw NMEA data

Set the UART speed:

```bash
sudo stty -F /dev/ttyS4 9600
```

Read the GPS:

```bash
sudo cat /dev/ttyS4
```

A working GPS should produce NMEA sentences similar to:

```text
$GNGGA,...
$GNRMC,...
$GNGSA,...
$GNGSV,...
```

Stop with:

```text
Ctrl+C
```

---

# 8. GPS ROS 2 Verification

Start the NMEA driver:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash

ros2 run nmea_navsat_driver nmea_serial_driver \
--ros-args \
-p port:=/dev/ttyS4 \
-p baud:=9600 \
-r /fix:=/gps/fix
```

In another terminal:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_humble/install/setup.bash
```

Check the topic:

```bash
ros2 topic list
```

Expected:

```text
/gps/fix
```

View the GPS messages:

```bash
ros2 topic echo /gps/fix
```

Check publishing rate:

```bash
ros2 topic hz /gps/fix
```

The GPS should produce `sensor_msgs/NavSatFix` messages containing latitude, longitude, altitude, status, and covariance information.

---

# 9. ROS 2 General Verification

Check running nodes:

```bash
ros2 node list
```

Check available topics:

```bash
ros2 topic list
```

Inspect a topic:

```bash
ros2 topic info /gps/fix
```

Display messages:

```bash
ros2 topic echo /gps/fix
```

Check publishing frequency:

```bash
ros2 topic hz /gps/fix
```

These commands are useful for verifying that a sensor node is not only running but actually publishing data.

---

# 10. Sensor Verification Checklist

Before proceeding to `robot_localization`, verify:

* [ ] ROCK 5C I²C bus detected
* [ ] ROCK 5C UART detected
* [ ] GPIO chips detected
* [ ] MPU-6050 detected at `0x68`
* [ ] MPU-6050 produces acceleration/gyro data
* [ ] VL53L1X detected at `0x29`
* [ ] VL53L1X produces distance measurements
* [ ] PCA9685 detected at `0x40`
* [ ] PCA9685 initializes correctly
* [ ] Wheel encoder counts change when wheels rotate
* [ ] Wheel diameter set to **2.6 inches**
* [ ] GPS UART `/dev/ttyS4` detected
* [ ] GPS produces NMEA data
* [ ] GPS ROS 2 driver runs
* [ ] `/gps/fix` publishes valid GPS messages

---

# 11. Important Architecture

The sensors should be verified **before** attempting EKF fusion.

```text
                    ROCK 5C
                       │
       ┌───────────────┼────────────────┐
       │               │                │
      I²C             GPIO             UART
       │               │                │
   ┌───┼───┐        Encoders           GPS
   │   │   │           │                │
  IMU ToF PCA        /odom          /gps/fix
   │   │   │           │                │
   └───┴───┘           │                │
       │               │                │
       └───────────────┼────────────────┘
                       ↓
                ROS 2 SENSOR NODES
                       ↓
              navsat_transform_node
                       ↓
              robot_localization EKF
                       ↓
                FUSED ODOMETRY
```

## Checkpoint

At the end of this stage, Goosebot should have independently verified:

```text
IMU       → detected + producing data
Encoder   → counting wheel movement
GPS       → producing NMEA + /gps/fix
ToF       → detected + measuring distance
PCA9685   → detected + responding
```

**Only after these checks pass should the project move to the EKF/fusion stage.**

The core localization chain will then be:

```text
IMU ──────────────────────┐
                          │
Encoder → /odom ──────────┼──→ EKF
                          │
GPS → /gps/fix → navsat ──┘
```
