# goosebot_hw: Goose on real hardware

A ROS 2 (Jazzy) package that replaces everything Gazebo provided in the simulation (diff-drive plugin, sensor plugins,
ground-truth pose, camera_info) with real drivers, and keeps the sim-independent parts: URDF frames, EKF structure,
RTAB-Map stereo SLAM and the Nav2 layout.

Hardware: Radxa Rock 5C (**2 GB** RAM), 4 skid-steer TT motors on a PCA9685 + L298N, MPU6050 IMU, **one front-facing
VL53L1X ToF sensor**, and two USB webcams as a stereo pair.

This README is also the setup guide. Part 1 gets a freshly flashed board working, Part 2 tests the sensors, Part 3 is
calibration, Part 4 is a staged Nav2 test without SLAM, and Part 5 covers connecting to the robot from a laptop (copying
and viewing maps, live view). "Budget tradeoffs" lists what the hardware cannot do by design, and "Open problems" lists
everything that has not been verified on the robot yet. Verify anything that touches the motors before relying on it.

## Status (2026-11-05)

The navigation algorithm worked in simulation. On hardware, movement and sensor data are in good shape, and the current
focus is filtering the camera data.

| Item | State |
|---|---|
| Top height cutoff for the SLAM grid (`cutoffs.top` in `config/slam_params.yaml`) | Done, untested |
| Memory tests while navigating and mapping | Done, untested |
| Recognizing where it is at startup (relocalization) | Done, untested |
| One wrapper launch that starts all three hardware launchers (`hw_robot.launch.py`) | Done, untested |
| Separate mapping / navigating modes with map reading (`read`, `write`, `static`, `rtab`) | Done, untested |
| Stereo local filter (RTAB-Map parameters that go into `slam_params.yaml`) | In progress (someone else) |
| Estimate stereo depth accuracy against lidar with physical tests, to improve the stereo cameras | To do |

See "Open problems" at the end for what still needs to be checked on the robot.

## Hardware layout (verified by I2C scans)

| Device | Header pins | Overlay | Linux bus | Address |
|---|---|---|---|---|
| PCA9685 (motor driver) | 3 (SDA), 5 (SCL) | `rk3588-i2c8-m2` | `/dev/i2c-8` | 0x40 (also 0x70, all-call) |
| MPU6050 (IMU) | VCC pin 17 (3.3 V), SDA 27, SCL 28 | `rk3588-i2c6-m0` | `/dev/i2c-6` | 0x68 |
| VL53L1X (front ToF) | VCC pin 1 (3.3 V), SDA 23, SCL 24 | `rk3588-i2c4-m3` | `/dev/i2c-4` | 0x29 |

Connect each sensor's GND to any real GND pin on the header. Never use pins 2 or 4 (5 V) for a 3.3 V sensor.
Header pins reserved for other parts: 11, 13, 15, 16 (encoders), 7, 29 (GPS UART4), 36, 38 (ultrasonic).
Linux bus numbers are not the SoC names, so confirm them with the mapping loop in 1.3.

Cameras: two USB webcams on separate USB controllers, addressed through the udev symlinks `/dev/cam_left` and
`/dev/cam_right` (never `/dev/videoN`, which can swap on reboot). Mount geometry in the URDF: lens centre 132 mm above
the floor, 96.9 mm forward of the chassis centre, pitched 5 degrees nose-up, baseline about 78 mm.

## Sim -> hardware mapping

| Sim | Hardware |
|---|---|
| gz DiffDrive plugin | `motor_driver_node` (PCA9685 -> L298N), real units, deadband, watchdog |
| gz `/cmd_vel` bridge | `cmd_vel_mux_node` -> `/cmd_vel_mux` -> motor driver |
| `cmd_vel_to_odom.py` on raw `/cmd_vel` | same script on `/cmd_vel_applied` (what the motor driver actually sent) |
| gz IMU (perfect orientation) | `imu_node`: MPU6050, **orientation published as unknown**, gyro-z only |
| gz single-beam ToF | `tof_node`: one VL53L1X, `/tof_front/scan`, same LaserScan shape |
| gz stereo cameras + `stereo_camera_info_fixer` | `stereo_camera_node` + `stereo_image_proc` + your calibration YAMLs |
| `ground_truth_map_odom_bridge` + baked map | **removed**. RTAB-Map owns `map->odom` and `/rtabmap/map`; saved maps are handled by `map_session.py` |
| gz GPS | not ported (no use indoors; the EKF never used it) |
| sim `nav2_params.yaml` | `nav2_params.yaml` (hardware limits, ToF source, footprint) |

Node graph: `teleop/Nav2/lane -> cmd_vel_mux -> motor_driver -> (/cmd_vel_applied) -> cmd_vel_to_odom -> EKF(+IMU gyro z) -> /odometry/filtered -> RTAB-Map -> map->odom -> Nav2`.

---

# Running the robot

## One command: `hw_robot.launch.py`

`hw_robot.launch.py` starts `hw_bringup` (drivers, TF, EKF, stereo), `hw_slam` (RTAB-Map) and `hw_nav2`, and handles map
files. Which mode you get is decided by `read`, `write`, `static` and `rtab`, not by separate flags per mode.

| Command | Mode | What happens |
|---|---|---|
| `hw_robot.launch.py` | new map | New map with an auto name (`map_<date>_<time>`). Nav2 off. |
| `... write:=lab` | new map | New map `lab`, saved as it is built. Asks before replacing an existing `lab` (the old one goes to `backups/`). |
| `... read:=lab` | dynamic | Navigate on `lab` and keep learning on a scratch copy. Nothing is saved. |
| `... read:=lab write:=lab` | update | Same, and on a clean exit `lab` is replaced by the updated map (old copy to `backups/`). |
| `... read:=lab write:=lab2` | duplicate | Updated copy saved as `lab2` on a clean exit. `lab` is untouched. |
| `... read:=lab static:=true` | static | RTAB-Map only localizes: it adds nothing to the map. Runs on a scratch copy that is discarded. |
| `... read:=lab rtab:=false` | no RTAB-Map | No vision at all. Nav2 trusts the saved grid (`lab.yaml` + `lab.pgm`) and assumes the robot starts at the map origin. |

**`static` vs `rtab:=false`.** With `static`, RTAB-Map still runs and still uses the cameras to find the robot's position
on the map; it just never learns anything new into it. With `rtab:=false` nothing corrects the robot's position, so
odometry drift accumulates, and the camera is off by default.

Rules enforced by the launch file: `static` needs `read` and cannot `write`; `rtab:=false` needs `read`, cannot `write`
and cannot be combined with `static`; map names may only contain letters, digits, `_`, `-` and `.`.

Other arguments: `overwrite:=true` (skip the "replace existing map?" question, for non-interactive use),
`with_imu`, `with_tof`, `with_stereo` (off when `rtab:=false`), `with_nav2` (off for a new map, on otherwise).

**Stop with ONE Ctrl+C and wait.** In update and duplicate modes the map is only saved after RTAB-Map has shut down.
Everything that starts from an existing map works on a scratch copy and replaces the real files only after a clean
shutdown, so a crash or power loss cannot damage the original. A new map is written straight to its final name so a
crash keeps what was mapped.

### Map files

Maps live in `~/goosebot_maps` (`maps.dir` in `slam_params.yaml`):

| File | Used by |
|---|---|
| `NAME.db` | RTAB-Map database (what gets loaded and updated) |
| `NAME.yaml` + `NAME.pgm` | Occupancy grid for Nav2's `map_server` (needed by `rtab:=false`), refreshed every 30 s while a map is written and once more on shutdown |
| `.work/` | Scratch copies for dynamic, update, duplicate and static runs |
| `backups/` | Maps that were replaced |

### Finding itself at startup (relocalization)

When a map is loaded with RTAB-Map on, Nav2 does not start until RTAB-Map reports that it recognises the surroundings on
that map. Dynamic, update and duplicate start RTAB-Map in localization mode and switch it to mapping only after the robot
has localized, so a lost robot cannot pollute the loaded map. `relocalization.mode` in `slam_params.yaml`:

- `auto`: the robot turns in place in short steps (turn, pause, turn) until localized. If `timeout_s` passes it stops
  turning and keeps waiting; Nav2 stays off.
- `manual`: the robot does not move; rotate or drive it with teleop until it localizes.
- `off`: no waiting, Nav2 starts immediately. Dynamic, update and duplicate then start mapping at once, and the new
  session only joins the old map if RTAB-Map happens to recognise a place.

"Localized" means `/rtabmap/localization_pose` reports an x variance below `max_covariance` (RTAB-Map reports 9999 until
it has a real localization). **Safety:** the spin has no obstacle check, so keep clear floor around the robot. Touching
teleop overrides the spin immediately. With `rtab:=false` there is no vision, so the robot is always assumed to start at
the map origin.

### `config/slam_params.yaml`

Read by `hw_slam.launch.py` and `hw_robot.launch.py` (it is not a ROS node parameter file). The first time it exists, run
`colcon build --packages-select goosebot_hw --symlink-install` once so the installed copy exists; later edits apply on
the next launch.

| Key | Meaning |
|---|---|
| `cutoffs.top` | Height above the floor (m, `base_footprint` frame) above which points are ignored when building the occupancy grid. `0` disables it. Maps to RTAB-Map `Grid/MaxObstacleHeight`. The default 0.25 m leaves about 10 cm above the camera tops. It only affects the grid, not the features used for loop closure. |
| `maps.dir`, `maps.autosave_period_s`, `maps.copy_for_static` | Map folder, grid refresh period, and whether static mode works on a scratch copy (keep `true` until you have confirmed with `sha256sum` that localization never writes to the `.db`). |
| `localization.start_at_origin` | RTAB-Map localization only: `false` = assume the robot restarted where it last shut down, `true` = assume the map origin. |
| `relocalization.*` | `mode`, `timeout_s`, `spin_speed`, `step_deg`, `pause_s`, `max_covariance` (see above). |

A bottom height cutoff is not wired up. RTAB-Map's `Grid/MinGroundHeight` is the closest match, but how it treats points
below it has not been confirmed; test it on the robot before adding it.

### Launching the pieces separately

Bring-up order for bench work (**wheels off the ground** until calibration step 3):

1. `ros2 launch goosebot_hw hw_bringup.launch.py with_stereo:=false` (add stereo after calibration step 7)
2. `ros2 launch goosebot_hw hw_slam.launch.py` for mapping; `localization:=true` to localize; `delete_db:=false
   database_path:=/path/map.db` to continue an existing database
3. `ros2 launch goosebot_hw hw_nav2.launch.py`

`hw_bringup` also runs `calibration/set_cam_controls.sh` about 6 s after the camera node starts, to lock exposure
(default 80 x 100 us), gain (32) and white balance (4600 K) on both webcams. Disable with `cam_controls:=false`.

To drive by hand: `ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_teleop`

---

# Part 1: Setting up from a fresh OS

Use this after a reflash. Everything here was done on Ubuntu 24.04 LTS, kernel `6.1.0-1025-rockchip`, booting through
extlinux/u-boot-menu. If your image differs, check "Troubleshooting" first.

## 1.1 System packages and groups

```bash
sudo apt update
sudo apt install i2c-tools gpiod python3-libgpiod python3-pip python3-colcon-common-extensions \
  ros-jazzy-nav2-bringup ros-jazzy-robot-localization ros-jazzy-rtabmap-ros \
  ros-jazzy-stereo-image-proc ros-jazzy-image-proc ros-jazzy-xacro \
  ros-jazzy-camera-calibration ros-jazzy-teleop-twist-keyboard ros-jazzy-robot-state-publisher \
  v4l-utils
sudo usermod -aG gpio,i2c $USER
```

Log out and back in (or reboot) so the groups apply, then check with `groups`. `v4l-utils` provides `v4l2-ctl`, which
`set_cam_controls.sh` needs.

## 1.2 Python packages

Ubuntu 24.04 blocks system-wide `pip install` (PEP 668). ROS nodes run on the system Python, so install with the
override flag instead of a venv, as your normal user, **not** with sudo.

```bash
pip install --break-system-packages smbus2 adafruit-blinka adafruit-circuitpython-pca9685 \
  adafruit-circuitpython-vl53l1x adafruit-extended-bus pyyaml
```

If pip ever tries to uninstall an apt-managed package (for example `numpy`), stop. Replacing those can break ROS.

```bash
python3 -c "import gpiod, smbus2, board, busio, adafruit_vl53l1x, adafruit_pca9685, adafruit_extended_bus; print('ok')"
```

`tof_node` imports `gpiod` at startup even though no XSHUT pin is used, so it must import cleanly.

## 1.3 Enable the I2C overlays

This image does not have `rsetup` (Radxa-only). Overlays are applied through `u-boot-update`, which **generates**
`/boot/extlinux/extlinux.conf`. Do not edit that file by hand; it gets overwritten.

1. Confirm the overlay files exist (the kernel version in the path should match `uname -r`):
   ```bash
   ls /usr/lib/firmware/$(uname -r)/device-tree/rockchip/overlay/ | grep -E "i2c(4-m3|6-m0|8-m2)"
   ```
2. Back up, then edit `/etc/default/u-boot`:
   ```bash
   sudo cp /etc/default/u-boot /etc/default/u-boot.bak
   sudo cp /boot/extlinux/extlinux.conf ~/extlinux.conf.bak
   sudo nano /etc/default/u-boot
   ```
   Set these two lines (include the `.dtbo` extensions; the directory is deliberately unversioned):
   ```
   U_BOOT_FDT_OVERLAYS="device-tree/rockchip/overlay/rk3588-i2c4-m3.dtbo device-tree/rockchip/overlay/rk3588-i2c6-m0.dtbo device-tree/rockchip/overlay/rk3588-i2c8-m2.dtbo"
   U_BOOT_FDT_OVERLAYS_DIR="/lib/firmware/"
   ```
3. Regenerate and check before rebooting:
   ```bash
   sudo u-boot-update
   grep -n fdtoverlays /boot/extlinux/extlinux.conf
   ```
   You want one `fdtoverlays` line in the first entry (`l0`) listing all three files under your *running* kernel's
   directory. If it is missing or shows the wrong kernel version, do not reboot; see Troubleshooting.
4. `sudo reboot`, then verify:
   ```bash
   ls /dev/i2c-*
   for d in /sys/class/i2c-dev/i2c-*; do echo "$d -> $(readlink -f $d/device)"; done
   sudo i2cdetect -y 8     # expect 0x40 and 0x70 (PCA9685)
   sudo i2cdetect -y 6     # expect 0x68 (MPU6050)
   sudo i2cdetect -y 4     # expect 0x29 (VL53L1X)
   ```

**After every kernel update, rerun `sudo u-boot-update` and confirm the `fdtoverlays` line still points at the new
kernel.** The overlays can silently stop applying otherwise.

If a reboot fails: restore `~/extlinux.conf.bak` and `/etc/default/u-boot.bak` from another computer (mount the boot
disk), or remove the `fdtoverlays` line from the `l0` entry. Enabling overlays one at a time (i2c8 first) makes a failure
easier to pin down.

## 1.4 Confirm Blinka's default bus

`motor_driver_node` has no bus parameter. It uses `busio.I2C(board.SCL, board.SDA)`, i.e. Blinka's default bus, which
should be I2C8 here:

```bash
python3 -c "import board,busio; i=busio.I2C(board.SCL,board.SDA); i.try_lock(); print([hex(a) for a in i.scan()]); i.unlock()"
# expect ['0x40', '0x70']
```

## 1.5 Workspace and build

The package lives in `~/goosebot_hw` and is linked into a ROS workspace so `ros2` can find it:

```bash
mkdir -p ~/ros2_ws/src
ln -s ~/goosebot_hw ~/ros2_ws/src/goosebot_hw
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
colcon build --packages-select goosebot_hw --symlink-install --parallel-workers 2
source install/setup.bash
ros2 pkg list | grep goosebot
```

With `--symlink-install`, Python and YAML edits take effect without a rebuild, but a **new** file (for example a new
config YAML) needs one rebuild so its link exists. Source both setup files in every new terminal (or add them to
`~/.bashrc`).

## 1.6 Configuration (`config/hw_params.yaml`)

- **Quote string values that look like numbers.** `none_as: "nan"` must be quoted, because the YAML parser reads a bare
  `nan` as a float and the node crashes with `InvalidParameterTypeException`.
- **ToF (single sensor):** `bus: 4`, `names: [front]`, `addresses: [0x29]`, `xshut_lines: [-1]` (`-1` = no XSHUT pin,
  use the sensor as-is).
- **IMU:** `bus: 6`, `address: 0x68`.
- **Stereo:** `left_device`/`right_device` are `/dev/cam_left` and `/dev/cam_right`, udev symlinks you create so that
  each webcam keeps its name across reboots (match on the USB port, not on `/dev/videoN`). `left_info`/`right_info` point at the
  calibration YAMLs under your home folder (`~/goosebot_calib/`); the copies in the package's `calibration/` folder are
  only backups and examples.
- **Motors:** values marked `CAL` are measured calibration results, see Part 3.

## 1.7 Run the self-check

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
bash ~/goosebot_hw/scripts/bench_check.sh
```

**Run it without sudo.** Under sudo the ROS environment is not inherited and the group and Python-module checks look at
root, so they report false failures. Flags: `--log` saves the report to `scripts/bench_check_logs/`, `--no-npu` skips
the NPU checks, `--pulse` briefly spins each wheel (wheels lifted, kill switch in reach). Expected leftovers on a healthy
setup: an `rknnlite` warning (NPU inference is untested) and "motor_driver_node is not running" when nothing is launched.

The board reports about 1960 MB of RAM. To save RAM it can boot headless (graphical sessions are lost):

```bash
sudo systemctl set-default multi-user.target
```

---

# Part 2: Testing sensor topics

Run the nodes directly rather than `hw_bringup`, which also starts `motor_driver_node`. Source ROS and the workspace in
every terminal.

## ToF

```bash
# terminal 1
ros2 run goosebot_hw tof_node --ros-args --params-file ~/goosebot_hw/config/hw_params.yaml
# terminal 2
ros2 topic hz /tof_front/scan
ros2 topic echo /tof_front/scan --field ranges
```

Expect about 15 Hz, ranges in meters that follow your hand, and `nan` (not `inf`) when nothing is in range. Check a few
tape-measured distances; a constant offset is fixed later with `offsets_m`.

## IMU

Keep the robot still when the node starts, because it measures its own gyro bias at startup.

```bash
# terminal 1
ros2 run goosebot_hw imu_node --ros-args --params-file ~/goosebot_hw/config/hw_params.yaml
# terminal 2
ros2 topic hz /imu/data
ros2 topic echo /imu/data --field orientation_covariance --once   # first value must be -1.0
ros2 topic echo /imu/data --field angular_velocity
```

- Stationary gyro should be near zero on all axes.
- **Gyro sign:** rotate the robot counterclockwise (seen from above). `angular_velocity.z` must go positive; if not, set
  `gyro_z_sign: -1.0`.
- Accelerometer noise (about +/-0.25 m/s², z near 9.2) is expected for an uncalibrated MPU6050. The EKF fuses gyro-z
  only, so it does not affect navigation. Recheck gyro noise with the motors running.
- `python3 scripts/imu_drift.py` integrates the gyro while the robot sits still and prints the drift in degrees per minute.

## Cameras

Cameras are tested through `stereo_camera_node` (publishes mono8 `/stereo/{left,right}/image_raw` and `camera_info`;
`stereo_image_proc` produces the rectified images RTAB-Map uses). Check that the two cameras are on different USB
controllers (`lsusb -t`) and that `/dev/cam_left` and `/dev/cam_right` exist and are not swapped. Only one program can
open a camera at a time, so stop the ROS camera node before running the calibration scripts.

---

# Part 3: Calibration (in this order; each step feeds the next)

1. **Geometry.** Measure and edit `urdf/robot_hw.urdf.xacro` and `wheel_separation` in `hw_params.yaml`. Track
   0.137 m and wheel diameter 66.1 mm are caliper values. Still guesses: wheel x-offset (0.07), the ToF mount position
   and the IMU position.
2. **IMU.** Warm up 2-3 min (MPU6050 bias drifts with temperature), robot stationary, start `imu_node`. Verify the gyro
   sign (Part 2). Drift check with `scripts/imu_drift.py` for about 5 min.
3. **Motor feedforward** (wheels on the floor, battery about 11.4 V; `scripts/drive_test.py lin|ang SPEED SECONDS` prints
   commanded vs EKF vs gyro motion): `min_duty` (straight) and `min_duty_spin` (in-place spin, needs much more duty),
   the speeds the robot really does at those duties (`v_floor`, `w_floor`), and `v_max`. Repeat at about 12.4 V and 10.8 V;
   if speed varies more than 15% across the pack range, open-loop odometry will be bad (the trigger for encoders). Confirm
   every wheel turns the right way; fix `invert_left`/`invert_right` or the channel mapping (`fl`/`fr`/`rl`/`rr`).
4. **Odometry scale.** Command 1.0 m straight x5 -> `linear_scale`. Command 360 deg in place x5 -> `angular_scale`
   (expect the robot to turn LESS than commanded). The run-to-run standard deviation is your real covariance: set
   `xy_var` and `vx_var` from it.
5. **EKF sanity.** Drive a 2 m x 2 m square, return to start, compare `/odometry/filtered` with a tape-measured end pose.
   `tf2_echo odom base_footprint` while stationary must not creep. Tune `process_noise_covariance` only after steps 2-4.
6. **ToF.** Put a flat matte target at 10/20/40/80/120 cm and fit `offsets_m`/`scales`. Test on dark and glossy surfaces
   and under bright light, and log how often NaN appears. Pick `distance_mode` (short is more ambient-light robust).
7. **Stereo.** Rigidly fix both cameras to one plate (any flex invalidates the calibration) and lock exposure and white
   balance (`set_cam_controls.sh`). Then, with the ROS camera node stopped:
   ```bash
   python3 scripts/capture_pairs.py --size 8x6 --count 35 --out pairs        # --size is INNER corners
   python3 scripts/calibrate_stereo.py --pairs pairs --size 8x6 --square <square size in m> --baseline <ruler cm in m>
   cp ~/.ros/camera_info/*.yaml ~/goosebot_calib/                               # the folder hw_params.yaml points at
   ```
   Gate: stereo RMS well under 0.5 px (under 1.0 is acceptable for cheap cameras) and row mismatch under 0.3 px.
   **Recalibrate whenever the cameras are moved, re-aimed or refocused.**
8. **Camera-to-base extrinsics.** Measure real height, pitch and offset and put them in the URDF (currently 132 mm, 96.9
   mm forward, 5 degrees nose-up). A few degrees of unmodelled pitch skews the SLAM grid projection.
9. **Latency/sync.** Wave an object in front of both cameras while recording and inspect left/right skew; tune
   `latency_s`; check `/stereo/*/image_raw` timestamps with `ros2 topic delay`.
10. **Nav2 limits.** Set `max_vel_x`, `max_vel_theta` and accelerations to about 70% of the achievable values from step 3.
    Check DWB does not command speeds below the deadband for long.
11. **Stereo depth accuracy.** Compare stereo depth with a lidar (or a tape measure) at several distances and fit an
    error curve. Expect it to fall off quickly: with a focal length of about 886 px and a 78 mm baseline, a 1 px
    disparity error is about 1.4 cm at 1 m, 5.8 cm at 2 m and 13 cm at 3 m (error grows with distance squared). Use the
    measured curve to set `Grid/RangeMax` and the stereo filter parameters.
12. **SLAM first, Nav2 second.** Map a small loop at slow speed with `rtabmap_viz` on a laptop; confirm loop closure and
    a clean `/rtabmap/map` before sending a Nav2 goal.

---

# Part 4: Staged Nav2 test without SLAM or cameras (odom-only)

Purpose: test the controller and your motor calibration on the real floor before the stereo mount and SLAM matter. This
is where the "motor deadband vs Nav2's small commands" risk shows up first.

```bash
ros2 launch goosebot_hw hw_bringup.launch.py with_stereo:=false
ros2 launch goosebot_hw hw_nav2.launch.py odom_only:=true
```

`odom_only` loads `nav2_params_odom_only.yaml` (global costmap without the static map layer, unknown space treated as
free, collision-monitor `source_timeout: 0.0`) and publishes an identity `map -> odom` transform. Send goals in the `map`
frame, from RViz on a laptop or with:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 0.3, y: 0.0}, orientation: {w: 1.0}}}}"
```

Preconditions (do not skip):
1. **IMU working, gyro sign verified.** Without the gyro the EKF never sees the robot rotate (cmd_vel odometry yaw is
   deliberately not fused) and Nav2 will keep commanding turns that "never happen".
2. Motor calibration steps 3-5 done.
3. Empty floor, at least about 2 m x 2 m, kill switch in hand.
4. **The only obstacle protection is the single front ToF** (nothing to the sides or rear), and `source_timeout: 0.0`
   means a dead ToF is not noticed. Do not run it together with RTAB-Map (both publish `map -> odom`).

Start with a 0.3 m goal straight ahead, then a 90 degree turn, then 1 m. Watch for stalls (raise `min_duty`),
oscillation or never reaching the goal (tolerances, `max_vel_theta`), and drift against a tape-measured distance.
Run RViz on a laptop, not on the robot.

---

# Part 5: Connecting to the robot

## 5.1 ROS settings on both machines

Put the same lines in `~/.bashrc` on the robot and on the laptop (adjust to whatever actually made discovery work; if you
needed `ROS_STATIC_PEERS`, add it on both sides):

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
```

Nodes only pick these up when they are launched after the exports, so restart them after any change. If a service
launches your nodes automatically, it needs the settings too. Reach the robot with `ssh goosebot@<robot-ip>`.

## 5.2 Look at saved maps from the laptop

`hw_robot.launch.py` keeps maps in `~/goosebot_maps` on the robot (file table under "Map files"). Only a **new map** is
written straight to `NAME.db` while the robot runs. In every mode that starts from an existing map the live data is in
`.work/`, and `NAME.db` is only replaced after a clean shutdown (one Ctrl+C), so look in `.work/` if you want to watch it
change. Mapping with `hw_slam.launch.py` directly (without the wrapper) still uses `~/.ros/goosebot_rtabmap.db`.

```bash
mkdir -p ~/robot_ros
sshfs goosebot@<robot-ip>:/home/goosebot/ ~/robot_ros
rtabmap-databaseViewer ~/robot_ros/goosebot_maps/NAME.db
fusermount -u ~/robot_ros            # unmount when done
```

Databases can be large, so for a smoother view copy one first and open the local copy:

```bash
scp goosebot@<robot-ip>:/home/goosebot/goosebot_maps/NAME.db ~/
```

Don't open a database while the robot is still writing to it. Finish the run first (one Ctrl+C, then wait for the
`[maps] saved ...` line), or copy the file and open the copy. The `.pgm` next to it opens in any image viewer.

## 5.3 Live view from the laptop

Both machines need to be on the same Wi-Fi network. The VPN blocked UDP from the robot to the laptop, so live viewing over
the VPN does not work unless that gets fixed. The VPN is still fine for SSH and for copying maps.

```bash
# check you can see the robot
ros2 daemon stop
ros2 topic list --no-daemon

# RViz
rviz2
# Fixed Frame: map
# Add -> By topic: /rtabmap/map, /tf
# map display: Durability Policy = Transient Local
# (with rtab:=false the map comes from Nav2's map_server on /map instead)

# or the rtabmap viewer
ros2 run rtabmap_viz rtabmap_viz
```

Save your RViz layout with File -> Save Config As, then reopen it with `rviz2 -d ~/goose.rviz`. Run RViz and
`rtabmap_viz` on the laptop, not on the robot.

To nudge the robot while it finds its position on a loaded map (`relocalization.mode: manual`, or after an `auto`
timeout), use teleop from either machine:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_teleop
```

You can also give an initial pose with "2D Pose Estimate" in RViz.

## 5.4 If it stops working

1. Check the robot's nodes are running and were launched with the right ROS settings.
2. Check both machines are on the same subnet (the first three IP numbers match).
3. Run `ros2 daemon stop` on the laptop and try `ros2 topic list --no-daemon` again.
4. If the robot's IP changed, update your SSH target and any `ROS_STATIC_PEERS`.
5. If Nav2 does not start after `read:=NAME`, the robot is still finding its position on the map: check the `relocalize`
   messages in the launch output (see "Finding itself at startup").

---

# Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `sudo rsetup` not found | Radxa-only tool. Use the `u-boot-update` method in 1.3. |
| `/boot/firmware/...` or `ubuntuEnv.txt` missing | Different image family. This image uses extlinux and `/etc/default/u-boot`. |
| `/dev/i2c-4/6/8` missing after reboot | `fdtoverlays` line absent or pointing at an old kernel directory. Check `U_BOOT_FDT_OVERLAYS_DIR`, rerun `sudo u-boot-update`, grep `extlinux.conf`. |
| Overlays stopped working after an update | The kernel version changed. Rerun `sudo u-boot-update`. |
| `ros2: command not found`, `ROS_DISTRO unset` | ROS not sourced, or script run under sudo. Source `/opt/ros/jazzy/setup.bash` and run without sudo. |
| `Package 'goosebot_hw' not found` | Not built into a workspace. Do 1.5, then source `~/ros2_ws/install/setup.bash`. |
| `InvalidParameterTypeException ... none_as ... DOUBLE` | Unquoted `nan` in YAML. Write `none_as: "nan"`. |
| bench_check: Python modules "missing" or not in group `gpio` | Installed or run under sudo, or `usermod` not applied. Install and run as your normal user; log out and back in after `usermod`. |
| `tof_node` finds no sensor | It scans the wrong bus. Set `bus: 4` in the yaml and confirm `0x29` with `i2cdetect -y 4`. |
| `hw_robot` fails at launch reading `slam_params.yaml` | The file is not installed yet. Run `colcon build --packages-select goosebot_hw --symlink-install` once. |
| `hw_robot` says a map name is invalid or not found | Names are letters, digits, `_ - .` only. `read:=` needs `NAME.db` in `~/goosebot_maps`; `rtab:=false` also needs `NAME.yaml` and `NAME.pgm`. |
| Nav2 never starts after `read:=lab` | Relocalization is still waiting. Watch the `relocalize` log; rotate the robot with teleop or set `relocalization.mode: off` to skip the wait. |
| Robot does not move or stops immediately in Nav2 | The collision monitor stops the robot if `/tof_front/scan` is not publishing (`source_timeout: 0.5`). Check `ros2 topic hz /tof_front/scan`. |
| A topic echo says "topic not published yet" | The node is not running. Nodes need their own terminal. |

---

# Budget tradeoffs

Things the hardware cannot do by design, so the software works around them or lives with them.

1. **Open odometry loop.** There are no wheel encoders. 4WD skid-steer scrubs hard in turns, and cmd_vel odometry cannot
   see slip, battery sag, carpet or stalls. The gyro rescues yaw rate but x/y drift. If calibration step 5 misses by more
   than about 10%, add rear-wheel encoders (config note in `ekf_hw.yaml`); header pins 11, 13, 15, 16 are reserved for them.
2. **2 GB board.** One Rock 5C runs two camera decoders, `stereo_image_proc`, RTAB-Map, Nav2 (two costmaps), the EKF and the
   Python I2C nodes. RAM is the limit, so camera fps and the SLAM rate are kept low (15 fps, 1 Hz), `rtabmap_viz`, RViz and
   rosbag recording stay off-board, and the board can boot headless (`sudo systemctl set-default multi-user.target`).
3. **Unsynchronized USB webcams.** No hardware sync, rolling shutter and a short 78 mm baseline, so useful stereo depth is
   only about 0.3-2 m (see calibration step 11). Fast turns smear, so keep Nav2's `max_vel_theta` at or below 1.0 rad/s.
4. **One front-facing ToF sensor.** Nothing watches the sides or rear, so the robot can back into or sideswipe things. The
   camera is the only other obstacle source, and only for what it sees ahead.
5. **TT motors on an L298N.** There is no stiction or deadband model in simulation, but the real motors need a minimum
   duty to move, so Nav2's small commands can be ignored and the progress checker aborts; expect to retune DWB. PWM goes on
   the L298N IN pins, so the ENA/ENB jumpers must stay fitted. The L298N drops about 2 V, so a full 3S pack (12.6 V) puts
   about 10.6 V on 6-9 V motors at 100% duty; hence `max_duty: 0.85`. The Rock needs its own regulated 5 V; a sensor loading
   the 3.3 V rail has caused a boot failure before.
6. **No magnetometer.** The EKF fuses gyro-z only, so heading drifts until RTAB-Map corrects it through `map->odom`. In
   featureless corridors stereo SLAM loses tracking.
7. **No hardware cutoff.** The mux publishes zeros if Nav2 dies and the motor driver has a 0.5 s watchdog, but a hung Python
   process or I2C lockup leaves PWM at its last value. Add a physical kill switch or fuse.
8. **No real-time clock.** There is no `/clock` on hardware (`use_sim_time false` everywhere), and without an RTC the board
   may boot with a wrong time. Use chrony/NTP before starting ROS or timestamps jump.
9. **Separate I2C buses.** The PCA9685 is on I2C8, the IMU on I2C6 and the ToF on I2C4, so one failing device does not hang
   the others. The nodes catch `OSError` and keep going, so watch for stale data. Run 400 kHz only after verifying clean
   signals.
10. **No on-board object detection yet.** The `rknpu` driver loads, but `rknnlite` and `librknnrt.so` are not installed, and
    Python 3.12 needs a cp312 aarch64 `rknn-toolkit-lite2` wheel. The old `perception_node` opens `cv2.VideoCapture(0)`
    exclusively and its `control_node` publishes unitless steering on `/cmd_vel`, so both need rework before they can share
    the cameras and the mux (`/cmd_vel_lane`).

---

# Open problems

Everything below is unverified on the robot. Items from the status table that are "done, untested" are repeated here with
what to check.

### Starting-location recognition

1. **Relocalization signal.** The wait relies on `/rtabmap/localization_pose` reporting a variance of 9999 until RTAB-Map
   has localized. Restart in `static` mode and run `ros2 topic echo /rtabmap/localization_pose --field pose.covariance`
   before the robot has seen anything: it must be high, then drop once it recognises the area. If it is low right away,
   Nav2 starts from an unverified pose.
2. **Threshold and spin step.** `max_covariance: 1.0` is loose (about 1 m standard deviation); tighten it after seeing real
   numbers. `spin_speed: 0.8` is below the measured spin floor (`w_floor`), so the robot turns at about 1.1 rad/s and each
   30 degree step overshoots to roughly 40 degrees.

### Map modes and the wrapper

3. **Each mode on the real robot.** The mode logic passes tests on a PC (every `read`/`write`/`static`/`rtab` combination,
   save on clean exit, discard on exit), but `hw_robot.launch.py` has not been run with ROS here. Check that `static` leaves
   `NAME.db` byte-identical (`sha256sum` before and after) before relying on it, and only then consider turning off
   `maps.copy_for_static`.
4. **Top cutoff.** Confirm `--Grid/MaxObstacleHeight 0.25` appears in the RTAB-Map arguments and that ceilings and tables
   no longer mark obstacles in a real map. The bottom cutoff is not wired up (`Grid/MinGroundHeight` is the closest match;
   how it treats points below it is unconfirmed).
5. **Memory.** No memory test result is recorded in this repo. RTAB-Map loads every stored node in the localizing and
   continuing modes (`Mem/InitWMWithAllNodes true`) and `.work/` copies use disk, so measure `free -m` and the RTAB-Map
   process during a long mapping run and a long navigating run on a map you expect to grow.

### Camera and stereo

6. **Stereo local filter.** In progress by someone else (RTAB-Map parameters going into `slam_params.yaml`).
7. **Depth accuracy against lidar.** Not measured yet (calibration step 11).
8. **Calibration vs the current mount.** The URDF follows the last re-aim of the cameras, but the intrinsics and extrinsics in
   use must be from after it. Recalibrate if unsure.
9. **Camera device names.** `hw_params.yaml` expects the udev symlinks `/dev/cam_left` and `/dev/cam_right`; their rule was
   not checked.

### Navigation

10. **Nav2 after the single-ToF trim.** The costmaps and collision monitor now use `tof_front` only; confirm Nav2 comes up
    and moves with it, then rerun the odom-only test (Part 4).
11. **Guessed geometry.** Wheel x-offset (0.07 m), ToF mount position and IMU position are still guesses (calibration step 1).
12. **Loop closure and the first map.** Map a small loop slowly and confirm loop closure and a clean `/rtabmap/map` before
    sending any Nav2 goal (calibration step 12).
