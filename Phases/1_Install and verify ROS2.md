# Phase 1 – Install and Verify ROS2

## Objective

Prepare the ROCK 5C for ROS2 Humble development by verifying the installation, sourcing the workspace, and confirming that the development environment is ready for Goosebot.

---

## Commands

```bash
# Verify ROS2 executable
which ros2

# Source the ROS2 workspace
source ~/ros2_humble/install/setup.bash

# Verify the ROS distribution
echo $ROS_DISTRO

# List active ROS2 topics
ros2 topic list

# Navigate to the workspace
cd ~/ros2_humble

# Build the workspace
colcon build
```

---

## Summary

These commands verify that the ROS2 Humble installation is functioning correctly, load the ROS2 environment into the current terminal, confirm that the correct ROS distribution is active, and ensure the workspace can be successfully built. This phase prepares the ROCK 5C for creating and developing ROS2 packages.

---

## Troubleshooting

### ROS2 command not found

```bash
source ~/ros2_humble/install/setup.bash
```

---

### Incorrect ROS distribution

```bash
echo $ROS_DISTRO
```

Expected:

```text
humble
```

---

### No topics shown

Run:

```bash
source ~/ros2_humble/install/setup.bash
```

then

```bash
ros2 topic list
```

Expected:

```text
/parameter_events
/rosout
```

---

### `colcon --version` does not work

`colcon` does not support the `--version` option.

Instead verify it by successfully running:

```bash
colcon build
```

---

## Phase Completion Checklist

- [ ] ROS2 executable found
- [ ] Workspace sourced
- [ ] ROS distribution verified
- [ ] ROS2 topics visible
- [ ] Workspace builds successfully

Phase 1 is complete.
