# Goosebot TOF400C Sensor Setup

## Overview

The Goosebot uses a **TOF400C (VL53L1X)** Time-of-Flight distance sensor for obstacle detection.

The TOF400C shares the same I²C bus as the **MPU-6050 IMU** and **PCA9685 motor controller**.

### Current Configuration

| Setting | Value |
|---|---|
| Sensor | TOF400C / VL53L1X |
| I²C Bus | `/dev/i2c-6` |
| SDA | ROCK 5C Pin 27 |
| SCL | ROCK 5C Pin 28 |
| TOF400C Address | `0x29` |
| MPU-6050 Address | `0x68` |
| PCA9685 Address | `0x40` |
| Python Driver | `vl53l1x` |
| Python Version | 3.11 |
| Virtual Environment | `~/ros2_ws/venv` |

---

# 1. Hardware Wiring

Connect the TOF400C to the same I²C bus as the MPU-6050.

### TOF400C Wiring

| TOF400C | ROCK 5C |
|---|---|
| SDA | Pin 27 |
| SCL | Pin 28 |
| GND | GND |
| VCC/VIN | Appropriate sensor supply |

> **Important:** Verify the voltage requirements of your specific TOF400C board before connecting power.

### Shared I²C Bus

The TOF400C, MPU-6050, and PCA9685 can share SDA and SCL.

```text
ROCK 5C Pin 27 (SDA)
        |
        +-------- MPU-6050 SDA
        |
        +-------- TOF400C SDA
        |
        +-------- PCA9685 SDA


ROCK 5C Pin 28 (SCL)
        |
        +-------- MPU-6050 SCL
        |
        +-------- TOF400C SCL
        |
        +-------- PCA9685 SCL


ROCK 5C GND
        |
        +-------- MPU-6050 GND
        |
        +-------- TOF400C GND
        |
        +-------- PCA9685 GND


                    ROCK 5C
                       |
                 /dev/i2c-6
                       |
             +---------+---------+
             |                   |
        Pin 27 SDA           Pin 28 SCL
             |                   |
             +---------+---------+
                       |
                   BREADBOARD
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
    MPU-6050        TOF400C        PCA9685
      0x68           0x29            0x40


Each I²C device has its own address.

0x29 → TOF400C
0x40 → PCA9685
0x68 → MPU-6050

Because the addresses are different, the devices can share the same SDA/SCL connections.

The Goosebot uses:

/dev/i2c-6
Step 3 — Check the I²C Bus

First check which I²C buses are available:

i2cdetect -l

The Goosebot TOF400C is connected to:

/dev/i2c-6

Scan I²C bus 6:

sudo i2cdetect -y 6

The TOF400C should appear as:

29

If all Goosebot I²C devices are connected, you should see:

29 → TOF400C
40 → PCA9685
68 → MPU-6050

Example:

     0 1 2 3 4 5 6 7 8 9 a b c d e f
00: -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- 29 -- --
30: -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- 68 -- -- -- --
70: -- -- -- -- -- -- -- --
Step 4 — Activate the Python Virtual Environment

Go to the Goosebot workspace:

cd ~/ros2_ws

Activate the virtual environment:

source ~/ros2_ws/venv/bin/activate

You should see:

(venv)

Your prompt should look similar to:

(venv) radxa@rock-5c:~/ros2_ws$

Important: The Goosebot virtual environment is ~/ros2_ws/venv.

Do not use ~/ros2_ws/.venv.

Step 5 — Install the TOF400C Python Driver

Install the required packages:

pip install vl53l1x smbus2

Verify the installation:

pip show vl53l1x

You should see information about:

Name: vl53l1x

Also verify smbus2:

pip show smbus2
Step 6 — Create the TOF Test Program

Create a Python test file:

nano ~/toftest2.py

Paste this code:

import time
import VL53L1X


# ==========================================
# Goosebot TOF400C Test
# ==========================================

I2C_BUS = 6
I2C_ADDRESS = 0x29


print()
print("==========================================")
print("        GOOSEBOT TOF400C TEST")
print("==========================================")
print()

print(f"I2C Bus     : {I2C_BUS}")
print(f"I2C Address : 0x{I2C_ADDRESS:02X}")
print()


try:

    print("Opening I2C bus...")

    tof = VL53L1X.VL53L1X(
        i2c_bus=I2C_BUS,
        i2c_address=I2C_ADDRESS
    )

    print("Initializing TOF400C...")

    tof.open()

    print("TOF400C detected!")
    print()


    # ======================================
    # Sensor Configuration
    # ======================================

    # Distance mode:
    # 1 = Short
    # 2 = Long

    tof.set_distance_mode(2)


    # Timing budget = 50 ms
    # Measurement interval = 60 ms

    tof.set_timing(50, 60)


    # Start continuous ranging

    tof.start_ranging(1)


    print("==========================================")
    print("        DISTANCE MEASUREMENT")
    print("==========================================")
    print()

    print("Move your hand/object in front of the sensor.")
    print("Press Ctrl+C to stop.")
    print()


    # ======================================
    # Measurement Loop
    # ======================================

    try:

        while True:

            distance_mm = tof.get_distance()

            distance_cm = distance_mm / 10.0
            distance_in = distance_mm / 25.4

            print(
                f"Distance: "
                f"{distance_mm:4d} mm | "
                f"{distance_cm:6.1f} cm | "
                f"{distance_in:6.2f} in"
            )

            time.sleep(0.1)


    except KeyboardInterrupt:

        print()
        print("Stopping TOF sensor...")


    finally:

        try:
            tof.stop_ranging()
        except Exception:
            pass

        try:
            tof.close()
        except Exception:
            pass

        print("TOF sensor stopped.")
        print("Test finished.")


except Exception as e:

    print()
    print("==========================================")
    print("             TOF ERROR")
    print("==========================================")
    print()

    print(f"Error: {e}")

    print()
    print("Check:")
    print("1. TOF400C power")
    print("2. SDA -> ROCK 5C Pin 27")
    print("3. SCL -> ROCK 5C Pin 28")
    print("4. GND -> ROCK 5C GND")
    print("5. TOF appears as 0x29")
    print("6. I2C bus is /dev/i2c-6")
    print()

    print("Run:")
    print("sudo i2cdetect -y 6")
    print()

Save the file:

Ctrl + O
Enter
Ctrl + X
Step 7 — Run the TOF400C Test

Make sure the virtual environment is active:

source ~/ros2_ws/venv/bin/activate

Run the program:

python3 ~/toftest2.py

A successful startup should display:

Opening I2C bus...
Initializing TOF400C...
TOF400C detected!

Then the sensor should continuously report distance:

Distance:  523 mm |   52.3 cm |  20.59 in
Distance:  521 mm |   52.1 cm |  20.51 in
Distance:  519 mm |   51.9 cm |  20.43 in
Step 8 — Test the Distance Measurement

Place your hand or an object in front of the TOF400C.

Move it closer.

The distance should decrease:

Distance:  500 mm |   50.0 cm |  19.69 in
Distance:  400 mm |   40.0 cm |  15.75 in
Distance:  300 mm |   30.0 cm |  11.81 in
Distance:  200 mm |   20.0 cm |   7.87 in

Move the object farther away.

The distance should increase.

The sensor reports:

Millimeters
Centimeters
Inches
Step 9 — Stop the Test

Press:

Ctrl + C

The program should display:

Stopping TOF sensor...
TOF sensor stopped.
Test finished.
Step 10 — Verify All I²C Devices

With the MPU-6050, PCA9685, and TOF400C connected, run:

sudo i2cdetect -y 6

Expected addresses:

0x29 → TOF400C
0x40 → PCA9685
0x68 → MPU-6050

The complete I²C layout is:

                         ROCK 5C
                            |
                      /dev/i2c-6
                            |
              +-------------+-------------+
              |                           |
         Pin 27 SDA                  Pin 28 SCL
              |                           |
              +-------------+-------------+
                            |
                        BREADBOARD
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v
      MPU-6050           TOF400C          PCA9685
        0x68              0x29              0x40
Step 11 — Quick Start After Installation

Once the sensor has been installed, the normal startup procedure is:

cd ~/ros2_ws
source ~/ros2_ws/venv/bin/activate
sudo i2cdetect -y 6
python3 ~/toftest2.py

You do not need to reinstall the Python packages every time.

Step 12 — Troubleshooting
TOF400C does not appear at 0x29

Run:

sudo i2cdetect -y 6

If 29 does not appear, check:

TOF400C power
TOF400C GND
SDA → Pin 27
SCL → Pin 28
Breadboard connections
I²C bus configuration
MPU-6050 disappears

The MPU-6050 should normally appear at:

0x68

If it disappears:

Power off the ROCK 5C.
Check SDA.
Check SCL.
Check GND.
Check for a short between SDA and SCL.
Check the shared breadboard connections.
No module named VL53L1X

Activate the virtual environment:

source ~/ros2_ws/venv/bin/activate

Then install:

pip install vl53l1x
No module named smbus2

Run:

source ~/ros2_ws/venv/bin/activate
pip install smbus2
No I2C device at address 0x29

Run:

sudo i2cdetect -y 6

If 29 is missing, the problem is likely hardware/I²C communication rather than the Python program.

Step 13 — One-Time Automated Setup Script

The following script can perform the Python installation and create the test program automatically.

Run this on the ROCK 5C after the TOF400C has been physically connected.

cd ~/ros2_ws

source ~/ros2_ws/venv/bin/activate

pip install vl53l1x smbus2

cat > ~/toftest2.py <<'PYTHON'
import time
import VL53L1X

I2C_BUS = 6
I2C_ADDRESS = 0x29

print()
print("==========================================")
print("        GOOSEBOT TOF400C TEST")
print("==========================================")
print()

try:

    print("Opening I2C bus...")

    tof = VL53L1X.VL53L1X(
        i2c_bus=I2C_BUS,
        i2c_address=I2C_ADDRESS
    )

    print("Initializing TOF400C...")

    tof.open()

    print("TOF400C detected!")
    print()

    tof.set_distance_mode(2)

    tof.set_timing(50, 60)

    tof.start_ranging(1)

    print("==========================================")
    print("        DISTANCE MEASUREMENT")
    print("==========================================")
    print()

    print("Move an object in front of the sensor.")
    print("Press Ctrl+C to stop.")
    print()

    try:

        while True:

            distance_mm = tof.get_distance()

            distance_cm = distance_mm / 10.0
            distance_in = distance_mm / 25.4

            print(
                f"Distance: "
                f"{distance_mm:4d} mm | "
                f"{distance_cm:6.1f} cm | "
                f"{distance_in:6.2f} in"
            )

            time.sleep(0.1)

    except KeyboardInterrupt:

        print()
        print("Stopping TOF sensor...")

    finally:

        try:
            tof.stop_ranging()
        except Exception:
            pass

        try:
            tof.close()
        except Exception:
            pass

        print("TOF sensor stopped.")

except Exception as e:

    print()
    print("TOF ERROR")
    print(f"Error: {e}")
    print()
    print("Run:")
    print("sudo i2cdetect -y 6")
Step 14 — Future ROS 2 Integration

Once the standalone TOF400C test is working, integrate the sensor into Goosebot's ROS 2 system.

Planned data flow:

TOF400C
   |
   | I²C
   v
ROCK 5C
   |
   v
Distance Measurement
   |
   v
ROS 2 TOF Node
   |
   v
Obstacle Detection
   |
   v
Navigation
   |
   v
Motor Control

The standalone TOF400C test should work successfully before integrating the sensor into autonomous navigation.
