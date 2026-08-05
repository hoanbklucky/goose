# Phase 3 – Creating the Goosebot ROS2 Package

## Objective

Create the Goosebot ROS2 package inside the ROS2 Humble workspace. This package will become the central location for all ROS2 nodes, launch files, configuration files, and future autonomous driving software.

---

## Prerequisites

Before starting this phase, verify:

```bash
source ~/ros2_humble/install/setup.bash

echo $ROS_DISTRO
```

Expected Output

```text
humble
```

Verify that the ROS2 workspace exists:

```bash
cd ~/ros2_humble
ls
```

Expected folders:

```text
build
install
log
src
```

---

# Step 1 – Navigate to the Workspace Source Folder

```bash
cd ~/ros2_humble/src
```

Verify your current location:

```bash
pwd
```

Expected Output

```text
/home/radxa/ros2_humble/src
```

---

# Step 2 – Create the Goosebot Package

Create a Python-based ROS2 package.

```bash
ros2 pkg create --build-type ament_python goosebot
```

Expected Output

```text
going to create a new package
package name: goosebot
...
```

---

# Step 3 – Verify the Package

List the contents of the source folder.

```bash
ls
```

Expected Output

```text
goosebot
```

Move into the package.

```bash
cd goosebot
```

Expected structure:

```text
goosebot/

├── goosebot/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/
└── test/
```

---

# Step 4 – Return to the Workspace

```bash
cd ~/ros2_humble
```

---

# Step 5 – Build the Workspace

```bash
colcon build
```

Wait until the build completes successfully.

---

# Step 6 – Source the Updated Workspace

```bash
source install/setup.bash
```

---

# Step 7 – Verify the Package

Verify that ROS2 recognizes the new package.

```bash
ros2 pkg list | grep goosebot
```

Expected Output

```text
goosebot
```

If the package appears, the installation was successful.

---

# Summary

The Goosebot ROS2 package has now been created and successfully added to the ROS2 workspace. This package will contain every ROS2 node developed throughout the remainder of the project, including sensor interfaces, robot localization, navigation, motor control, launch files, and configuration files.

---

# Troubleshooting

## Package not found

Re-source the workspace.

```bash
source ~/ros2_humble/install/setup.bash
```

or

```bash
source install/setup.bash
```

---

## Package still not found

Rebuild the workspace.

```bash
colcon build
```

Then source it again.

```bash
source install/setup.bash
```

---

## Build failed

Read the error shown by `colcon`.

Most build failures are caused by:

- Python syntax errors
- Missing dependencies
- Incorrect package structure

Fix the issue and rebuild.

```bash
colcon build
```

---

# Phase Completion Checklist

- [ ] Goosebot package created.
- [ ] Workspace builds successfully.
- [ ] Workspace sourced.
- [ ] `ros2 pkg list` displays `goosebot`.
- [ ] Package structure verified.

✅ Phase 3 Complete

---

# Next Phase

Phase 4 – Creating the IMU ROS2 Node

The first working Python sensor script (MPU6050) will be converted into a ROS2 publisher node.
