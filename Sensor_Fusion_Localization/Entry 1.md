# Goosebot — Step 1: ROCK 5C Setup

This step prepares the Radxa ROCK 5C for the Goosebot robotics project.

The goal is to prepare:

* Linux development environment
* SSH access
* Python
* Hardware diagnostic tools
* I²C/UART access
* Python virtual environment
* Additional virtual memory (swap)
* ROS 2 Humble
* `colcon`
* ROS 2 workspace

> **Important:** Do not install `robot_localization` or create the Goosebot sensor nodes during this step. Those are covered in later steps.

---

## 1. Update the ROCK 5C

```bash
sudo apt update
sudo apt upgrade -y
```

Reboot:

```bash
sudo reboot
```

Reconnect through SSH after the ROCK 5C restarts.

---

## 2. Verify the Operating System

```bash
cat /etc/os-release
```

Check the CPU architecture:

```bash
uname -m
```

Record these values before continuing because ROS 2 installation depends on the operating system and architecture.

---

## 3. Install Basic Development Tools

```bash
sudo apt install -y \
git \
curl \
wget \
vim \
nano \
build-essential \
cmake \
python3 \
python3-pip \
python3-venv \
python3-dev \
pkg-config \
software-properties-common
```

Verify:

```bash
git --version
python3 --version
pip3 --version
cmake --version
gcc --version
```

---

## 4. Install Hardware Diagnostic Tools

These tools are useful for testing the ROCK 5C before ROS 2 sensor nodes are created.

```bash
sudo apt install -y \
i2c-tools \
gpiod \
libgpiod-dev \
minicom \
screen \
usbutils \
pciutils
```

---

## 5. Check I²C Interfaces

List available I²C devices:

```bash
ls /dev/i2c*
```

Scan an I²C bus:

```bash
i2cdetect -y 0
```

Repeat for the other I²C buses that exist:

```bash
i2cdetect -y 1
i2cdetect -y 2
```

If another bus is being used:

```bash
i2cdetect -y 6
```

### Important

Do not assume that the I²C bus number is the same on every ROCK 5C installation.

The physical SDA/SCL pins must be matched to the correct Linux `/dev/i2c-X` interface.

For the Goosebot project, devices were eventually detected around:

```text
0x29  → VL53L1X ToF
0x40  → PCA9685
0x68  → MPU-6050
```

---

## 6. Check UART Interfaces

List serial interfaces:

```bash
ls /dev/ttyS*
```

Also check USB serial devices:

```bash
ls /dev/ttyUSB*
```

```bash
ls /dev/ttyACM*
```

The Goosebot GPS eventually used:

```text
/dev/ttyS4
```

However, verify the actual UART device on a different ROCK 5C instead of assuming it will be identical.

---

# 7. Create the Python Virtual Environment

Create the Goosebot Python environment:

```bash
python3 -m venv ~/goosebot_venv
```

Activate it:

```bash
source ~/goosebot_venv/bin/activate
```

Verify:

```bash
which python
```

The result should point to:

```text
~/goosebot_venv/bin/python
```

Check Python:

```bash
python --version
```

To leave the virtual environment:

```bash
deactivate
```

To activate it again:

```bash
source ~/goosebot_venv/bin/activate
```

---

# 8. Install Python Hardware Libraries

With the virtual environment activated:

```bash
pip install \
adafruit-extended-bus \
adafruit-circuitpython-pca9685 \
adafruit-circuitpython-vl53l1x \
gpiozero \
keyboard
```

Verify:

```bash
pip list
```

### Note about `gpiod`

The Goosebot project encountered compatibility problems between different `gpiod` versions.

Check the system version:

```bash
apt policy python3-gpiod
```

If using a Python package:

```bash
pip show gpiod
```

Do not assume that code written for one `gpiod` API will work with another version.

---

# 9. Check Available Memory

Before building ROS 2 packages, check RAM:

```bash
free -h
```

Check existing swap:

```bash
swapon --show
```

Large ROS 2 builds can consume significant memory on the ROCK 5C.

---

# 10. Expand Virtual Memory With Swap

If additional swap is required, create a swap file.

Example using an 8 GB swap file:

```bash
sudo fallocate -l 8G /swapfile
```

Set secure permissions:

```bash
sudo chmod 600 /swapfile
```

Format it:

```bash
sudo mkswap /swapfile
```

Enable it:

```bash
sudo swapon /swapfile
```

Verify:

```bash
free -h
```

and:

```bash
swapon --show
```

The swap file should now appear.

---

## Make Swap Permanent

Edit `/etc/fstab`:

```bash
sudo nano /etc/fstab
```

Add:

```text
/swapfile none swap sw 0 0
```

Save and exit.

Test the configuration:

```bash
sudo swapoff /swapfile
sudo swapon /swapfile
```

Verify:

```bash
free -h
```

```bash
swapon --show
```

> Swap is slower than physical RAM. It is being used as a memory-expansion workaround to reduce memory-related failures during large builds.

---

# 11. Install ROS 2 Humble

Verify the operating system first:

```bash
cat /etc/os-release
```

ROS 2 Humble installation depends on the Linux distribution and architecture.

Install ROS 2 Humble using the appropriate official ROS 2 installation procedure for the ROCK 5C's operating system.

After installation, source ROS 2:

```bash
source /opt/ros/humble/setup.bash
```

Verify:

```bash
ros2 --help
```

Run:

```bash
ros2 doctor
```

---

# 12. Automatically Source ROS 2

To automatically load ROS 2 whenever a new Bash terminal is opened:

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

Reload:

```bash
source ~/.bashrc
```

Verify:

```bash
ros2 --help
```

---

# 13. Install Colcon

Install the ROS 2 build system:

```bash
sudo apt install -y python3-colcon-common-extensions
```

Verify:

```bash
colcon --version
```

---

# 14. Create the Goosebot ROS 2 Workspace

Create the workspace:

```bash
mkdir -p ~/ros2_humble/src
```

Enter the workspace:

```bash
cd ~/ros2_humble
```

Verify:

```bash
pwd
```

Expected structure:

```text
~/ros2_humble/
└── src/
```

After building packages, the workspace will contain:

```text
~/ros2_humble/
├── src/
├── build/
├── install/
└── log/
```

---

# 15. Test Colcon

Enter the workspace:

```bash
cd ~/ros2_humble
```

Build:

```bash
colcon build
```

After the build:

```bash
source ~/ros2_humble/install/setup.bash
```

Verify ROS 2:

```bash
ros2 --help
```

---

# 16. Final System Verification

Run:

```bash
echo "===== OS ====="
cat /etc/os-release

echo "===== ARCHITECTURE ====="
uname -m

echo "===== PYTHON ====="
python3 --version

echo "===== GIT ====="
git --version

echo "===== CMAKE ====="
cmake --version

echo "===== COLCON ====="
colcon --version

echo "===== ROS 2 ====="
ros2 --help

echo "===== MEMORY ====="
free -h

echo "===== SWAP ====="
swapon --show

echo "===== I2C ====="
ls /dev/i2c*

echo "===== UART ====="
ls /dev/ttyS* 2>/dev/null
```

---

# Step 1 Completion Checklist

The ROCK 5C is ready for the next stage when:

* [ ] Linux is working
* [ ] SSH access works
* [ ] Internet access works
* [ ] System packages are updated
* [ ] Git is installed
* [ ] Python is installed
* [ ] Python virtual environment works
* [ ] Hardware diagnostic tools are installed
* [ ] I²C interfaces can be detected
* [ ] UART interfaces can be detected
* [ ] Python hardware libraries are installed
* [ ] Additional swap/virtual memory is configured if required
* [ ] ROS 2 Humble is installed
* [ ] `ros2` command works
* [ ] `colcon` is installed
* [ ] `~/ros2_humble/src` exists
* [ ] Empty workspace successfully builds

---

# What Comes Next

After completing Step 1, the ROCK 5C should be ready for the actual Goosebot hardware/software integration.

The next stages are:

```text
STEP 1
ROCK 5C + ROS 2 Foundation
        ↓
STEP 2
Install & Verify Sensors
        ↓
STEP 3
Create Sensor ROS 2 Nodes
        ↓
STEP 4
Encoder / Odometry
        ↓
STEP 5
GPS / NMEA
        ↓
STEP 6
IMU
        ↓
STEP 7
robot_localization
        ↓
STEP 8
EKF Configuration
        ↓
STEP 9
navsat_transform_node
        ↓
STEP 10
GPS + IMU + Encoder Fusion
```

**Step 1 should be completed before proceeding to the sensor-node development stages.**
