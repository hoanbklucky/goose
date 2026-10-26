# goosebot_hw: sim -> real hardware

A ROS 2 (Jazzy) package that replaces everything Gazebo provided in `goosebot_0` (diff-drive plugin, sensor plugins,
ground-truth pose, camera_info) with real drivers, and keeps the sim-independent parts (URDF frames, EKF structure,
RTAB-Map stereo SLAM, Nav2 layout).

This README doubles as a setup guide: Part 1 gets a freshly flashed Rock 5C to a working state, Part 2 tests the
sensors, Part 3 is calibration, Part 4 is the first navigation test. Some of it was written by an AI assistant while
the project was in progress, so verify anything that touches the robot's motors before relying on it.

## Status (last updated 2026-10-26)

| Item | State |
|---|---|
| Ubuntu 24.04 + ROS Jazzy, I2C overlays, Python modules | Working. `bench_check.sh`: 41 OK, 1 WARN, 0 FAIL |
| PCA9685 (motor driver) on I2C8 | Detected; PWM outputs idle at 0%; wheel pulse test run |
| MPU6050 IMU on I2C6 | Working, `/imu/data` publishes |
| VL53L1X ToF on I2C4 | Working, `/tof_front/scan` publishes plausible ranges. **Only one sensor is wired** |
| Cameras | Two USB cameras detected on separate USB controllers; stereo calibration not done |
| Motor calibration, odometry, EKF, Nav2, SLAM, NPU/YOLO | **Not tested on hardware yet** |

The one remaining bench_check warning is `rknnlite` not importable (NPU inference is untested).

## Hardware layout (verified by I2C scans)

| Device | Header pins | Overlay | Linux bus | Address |
|---|---|---|---|---|
| PCA9685 (motor driver) | 3 (SDA), 5 (SCL) | `rk3588-i2c8-m2` | `/dev/i2c-8` | 0x40 (also 0x70, all-call) |
| MPU6050 (IMU) | VCC pin 17 (3.3 V), SDA 27, SCL 28 | `rk3588-i2c6-m0` | `/dev/i2c-6` | 0x68 |
| VL53L1X (ToF) | VCC pin 1 (3.3 V), SDA 23, SCL 24 | `rk3588-i2c4-m3` | `/dev/i2c-4` | 0x29 |

Connect each sensor's GND to any real GND pin on the header. Never use pins 2 or 4 (5 V) for a 3.3 V sensor.
Header pins already used by other parts per your notes: 11, 13, 15, 16 (encoders), 7, 29 (GPS UART4), 36, 38 (ultrasonic).

Linux bus numbers are not the SoC names, so never assume them. Confirm with the mapping loop in Part 1.

## Sim -> hardware mapping

| Sim | Hardware |
|---|---|
| gz DiffDrive plugin | `motor_driver_node` (PCA9685 -> L298N), real units, deadband, watchdog |
| gz `/cmd_vel` bridge | `cmd_vel_mux_node` -> `/cmd_vel_mux` -> motor driver |
| `cmd_vel_to_odom.py` on raw `/cmd_vel` | same script on `/cmd_vel_applied` (what the motor driver actually sent) |
| gz IMU (perfect orientation) | `imu_node`: MPU6050, **orientation published as unknown**, gyro-z only |
| gz gpu_lidar single beam ToF | `tof_node`: up to 4x VL53L1X, same LaserScan shape (currently 1 sensor, no XSHUT) |
| gz stereo cameras + `stereo_camera_info_fixer` | `stereo_camera_node` + `stereo_image_proc` + your calibration YAML |
| `ground_truth_map_odom_bridge` + baked map | **removed**. RTAB-Map owns `map->odom` and `/rtabmap/map` |
| gz GPS | not ported (no use indoors; EKF never used it) |
| sim `nav2_params.yaml` | `nav2_params.yaml` (same Jazzy naming; hardware limits, ToF sources, footprint) |

Node graph: `teleop/Nav2/lane -> cmd_vel_mux -> motor_driver -> (/cmd_vel_applied) -> cmd_vel_to_odom -> EKF(+IMU gyro z) -> /odometry/filtered -> RTAB-Map -> map->odom -> Nav2`.

---

# Part 1: Setting up from a fresh OS

Use this after a reflash. Everything here was done on Ubuntu 24.04 LTS, kernel `6.1.0-1025-rockchip`, booting through
extlinux/u-boot-menu. If your image differs, check the "Troubleshooting" section first.

## 1.1 System packages and groups

```bash
sudo apt update
sudo apt install i2c-tools gpiod python3-libgpiod python3-pip python3-colcon-common-extensions \
  ros-jazzy-nav2-bringup ros-jazzy-robot-localization ros-jazzy-rtabmap-ros \
  ros-jazzy-stereo-image-proc ros-jazzy-image-proc ros-jazzy-xacro \
  ros-jazzy-camera-calibration ros-jazzy-teleop-twist-keyboard ros-jazzy-robot-state-publisher
sudo usermod -aG gpio,i2c $USER
```

Log out and back in (or reboot) so the groups apply, then check with `groups`.

## 1.2 Python packages

Ubuntu 24.04 blocks system-wide `pip install` (PEP 668). ROS nodes run on the system Python, so install with the
override flag instead of a venv. Run it as your normal user, **not** with sudo (user installs go to `~/.local`, which
root's Python does not see).

```bash
pip install --break-system-packages smbus2 adafruit-blinka adafruit-circuitpython-pca9685 \
  adafruit-circuitpython-vl53l1x adafruit-extended-bus pyyaml
```

If pip ever tries to uninstall an apt-managed package (for example `numpy`), stop. Replacing those can break ROS.

Check that everything imports:

```bash
python3 -c "import gpiod, smbus2, board, busio, adafruit_vl53l1x, adafruit_pca9685, adafruit_extended_bus; print('ok')"
```

`tof_node` imports `gpiod` at startup even when no XSHUT pin is used, so it must import cleanly.

## 1.3 Enable the I2C overlays

This image does not have `rsetup` (that is Radxa-only). Overlays are applied through `u-boot-update`, which
**generates** `/boot/extlinux/extlinux.conf`. Do not edit that file by hand, because it gets overwritten.

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

If a reboot fails: restore `~/extlinux.conf.bak` and `/etc/default/u-boot.bak` from another computer (mount the
boot disk), or remove the `fdtoverlays` line from the `l0` entry. Enabling overlays one at a time (i2c8 first) makes a
failure easier to pin down.

## 1.4 Confirm Blinka's default bus

`motor_driver_node` has no bus parameter. It uses `busio.I2C(board.SCL, board.SDA)`, i.e. Blinka's default bus,
which should be I2C8 here. Check:

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

With `--symlink-install`, Python and YAML edits take effect without a rebuild. Source both setup files in every new
terminal (or add them to `~/.bashrc`).

## 1.6 Configuration (`config/hw_params.yaml`)

- **Quote string values that look like numbers.** `none_as: "nan"` must be quoted, because the YAML parser reads a bare
  `nan` as a float and the node crashes with `InvalidParameterTypeException`. The same applies to `"inf"`.
- **ToF (single-sensor setup):** `bus: 4`, `names: [front]`, `addresses: [0x29]`, `xshut_lines: [-1]`.
  `-1` means "no XSHUT pin, use the sensor as-is at this address."
- **IMU:** `bus: 6`, `address: 0x68`.
- **Stereo:** `left_device`/`right_device` must be `/dev/v4l/by-path/...` paths, never `/dev/videoN`, which can swap on
  reboot. List them with `ls -l /dev/v4l/by-path/`. Fill in the calibration YAML paths for your user's home directory.
- **Adding more ToF sensors later:** every sensor on the same bus needs its own XSHUT GPIO (the node re-addresses them
  one at a time at startup, and the address is lost at power-off). Restore the 4-entry lists, set
  `xshut_chips`/`xshut_lines` from `gpioinfo`, and use addresses `0x30`-`0x33`. With two or more sensors on one bus,
  the first one needs XSHUT too, since only one sensor can be at 0x29.

## 1.7 Run the self-check

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
bash ~/goosebot_hw/bench_check.sh
```

**Run it without sudo.** Under sudo the ROS environment is not inherited and the group and Python-module checks look
at root, so they report false failures. Expected leftovers on a healthy setup: `rknnlite` warning, `CHANGE_ME` stereo
paths until the camera mount is done, and "motor_driver_node is not running" when nothing is launched.

Optional RAM saver on this 2 GB-class board (boots headless; graphical sessions are lost):
```bash
sudo systemctl set-default multi-user.target
```

---

# Part 2: Testing sensor topics

Run the nodes directly rather than `hw_bringup`, which also starts `motor_driver_node` (and `dry_run` is `false`).
Source ROS and the workspace in every terminal.

## ToF

```bash
# terminal 1
ros2 run goosebot_hw tof_node --ros-args --params-file ~/goosebot_hw/config/hw_params.yaml
# terminal 2
ros2 topic hz /tof_front/scan
ros2 topic echo /tof_front/scan --field ranges
```
Expect about 15 Hz, ranges in meters that follow your hand, and `nan` (not `inf`) when nothing is in range. Check a
few tape-measured distances; a constant offset is fixed later with `offsets_m`.

## IMU

Keep the robot still when the node starts, because it measures its own gyro bias at startup.

```bash
# terminal 1
ros2 run goosebot_hw imu_node --ros-args --params-file ~/goosebot_hw/config/hw_params.yaml
# terminal 2
ros2 topic hz /imu/data
ros2 topic echo /imu/data --field orientation_covariance --once   # first value must be -1.0
ros2 topic echo /imu/data --field angular_velocity
ros2 topic echo /imu/data --field linear_acceleration
```
- Stationary gyro should be near zero on all axes.
- **Gyro sign:** rotate the robot counterclockwise (seen from above). `angular_velocity.z` must go positive; if not,
  set `gyro_z_sign: -1.0`.
- **Accelerometer noise is expected.** On this unit, `linear_acceleration` shows about +/-0.25 m/s² of noise and z
  reads around 9.2 instead of 9.81. That is typical for an uncalibrated MPU6050 accelerometer. The EKF fuses gyro-z
  only, so it does not affect navigation. If you ever fuse acceleration, calibrate the offsets and low-pass filter it.
  Recheck gyro noise with the motors running, since vibration and switching supply noise can make it worse.

## Cameras

Cameras are tested through `stereo_camera_node`. Make sure the two cameras are on different USB controllers (`lsusb -t`)
and that their by-path names are in `hw_params.yaml`.

---

# Part 3: Bring-up and calibration

Bring-up order (bench first, **wheels off the ground** until calibration step 3):
1. `ros2 launch goosebot_hw hw_bringup.launch.py with_stereo:=false`
2. Add stereo after step 7.
3. `ros2 launch goosebot_hw hw_slam.launch.py` (mapping), drive manually, later `localization:=true`
4. `ros2 launch goosebot_hw hw_nav2.launch.py`

To drive by hand: `ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_teleop`

## Calibration procedure (in this order; each step feeds the next)

1. **Geometry.** The hardware URDF uses your notes: track 5.3 in = 0.1346 m, wheel diameter 2.6 in = 0.066 m (the v5
   encoder script says 2.5 in, so measure it), chassis ~0.161 x 0.102 m from the STEP file (treat as +-10 mm), footprint
   0.17 x 0.17 m. Still guesses: wheel x-offset (0.07), wheel width (0.025), all camera/ToF/IMU mount positions, and the
   stereo baseline (0.09). Measure those and edit `urdf/robot_hw.urdf.xacro` and `wheel_separation` in params.
2. **IMU.** Warm up 2-3 min (MPU6050 bias drifts with temperature), robot stationary, start `imu_node`; it measures bias
   and variance itself. Verify the gyro sign (Part 2). Drift check: leave still 5 min, integrate z, and record the rate.
3. **Motor feedforward** (wheels on the floor, battery ~11.4 V, measure with a stopwatch and tape):
   - `min_duty`: lowest duty at which all four wheels start from rest, on your real floor surface. Test driving
     straight AND spinning in place; skid-steer spin needs much more duty than straight driving.
   - `v_max`: drive 2 m at `max_duty` via `/cmd_vel_teleop`, time it. Repeat at 100% and 50% of v_max to check linearity.
   - Redo at ~12.4 V and ~10.8 V. If speed varies more than 15% across the pack range, open-loop odometry will be bad
     (this is your trigger for encoders).
   - Also confirm every wheel turns the right way on a forward command. If not, fix `invert_left`/`invert_right` or the
     channel mapping (`fl`/`fr`/`rl`/`rr`) in `hw_params.yaml`.
4. **Odometry scale.** Command 1.0 m straight x5 -> `linear_scale = measured/commanded`. Command 360 deg in place x5
   -> `angular_scale`. Expect the robot to turn LESS than commanded (skid-steer scrub) and expect run-to-run variance.
   The standard deviation across runs is your real covariance: set `xy_var` and `vx_var` from it.
5. **EKF sanity.** Drive a 2 m x 2 m square, return to start, and compare `/odometry/filtered` to a tape-measured end
   pose. Also tf-echo `odom->base_footprint` while stationary: it must not creep. Tune `process_noise_covariance` only
   after steps 2-4.
6. **ToF.** Put a flat matte target at 10/20/40/80/120 cm per sensor and fit `offsets_m`/`scales` per sensor. Test on dark
   and glossy surfaces and under bright light; log how often NaN appears. Pick `distance_mode` (short is more
   ambient-light robust; long reaches further). With several sensors, confirm adjacent cones do not interfere.
7. **Stereo.** Print a flat, rigid checkerboard and run `camera_calibration` stereo (`cameracalibrator` with
   `--approximate`) at your final resolution and fps; save to `left.yaml`/`right.yaml`. Gate: RMS reprojection error well
   under 0.5 px and epipolar lines horizontal. Rigidly fix both cameras to one plate, because any flex after
   calibration invalidates it. Use `v4l2-ctl` to set the same fixed exposure/white balance/focus on both. Verify depth
   against a tape measure at 0.5/1/1.5/2 m (the sim script `check_stereo_depth.py` is a starting point).
8. **Camera-to-base extrinsics.** The URDF assumes cameras centred and level. Measure real height, pitch, and offset, and
   put them in the URDF. A few degrees of unmodelled pitch skews the SLAM grid projection.
9. **Latency/sync.** Wave an object in front of both cameras while recording and inspect left/right frame skew. Tune
   `latency_s`. Check `/stereo/*/image_raw` timestamps with `ros2 topic delay`.
10. **Nav2 limits.** Set `max_vel_x`, `max_vel_theta`, and accelerations to ~70% of the measured achievable values from
    step 3, not the starting values in the YAML. Check DWB does not command speeds below the deadband for long.
11. **SLAM first, Nav2 second.** Map a small loop at slow speed with `rtabmap_viz` on a laptop; confirm loop closure and a
    clean `/rtabmap/map` before sending a Nav2 goal.

---

# Part 4: Staged Nav2 test without SLAM or cameras (odom-only)

Purpose: test the controller and your motor calibration on the real floor before the stereo mount and SLAM exist.
This is where the "motor deadband vs Nav2's small commands" risk shows up first.

```bash
ros2 launch goosebot_hw hw_bringup.launch.py with_stereo:=false
ros2 launch goosebot_hw hw_nav2.launch.py odom_only:=true
```

`odom_only` loads `nav2_params_odom_only.yaml` (global costmap without the static map layer, unknown space treated as
free) and publishes an identity `map -> odom` transform. Send goals in the `map` frame, from RViz on a laptop or with:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 0.3, y: 0.0}, orientation: {w: 1.0}}}}"
```

Preconditions (do not skip):
1. **IMU working, gyro sign verified.** Without the gyro, the EKF never sees the robot rotate (cmd_vel odometry yaw is
   deliberately not fused), and Nav2 will keep commanding turns that "never happen".
2. Motor calibration steps 3-5 done (`min_duty`, `v_max`, scales).
3. Empty floor, at least ~2 m x 2 m, kill switch in hand.
4. **No obstacle protection in this mode.** Nav2's collision monitor stops the robot when any of its sources has not
   published within `source_timeout`, including data that was never received (`source_timeout: 0.0` disables that).
   The normal config uses 0.5 s, and it lists multiple ToF sources. With only the front ToF wired, the others never
   publish, so the normal file would stop the robot. The odom-only file sets 0.0 for that reason. Once all ToFs are live
   (or the normal params are trimmed to the sensors that exist), use the normal file.
5. Do not run it together with RTAB-Map (both publish `map -> odom`).

Start with a 0.3 m goal straight ahead, then a 90 degree turn goal, then 1 m. Watch for stalls (raise `min_duty`),
oscillation or never reaching the goal (tolerances, `max_vel_theta`), and drift against a tape-measured distance.
Run RViz on a laptop, not on the Rock (needs the same `ROS_DOMAIN_ID` and a working network).

---

# Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `sudo rsetup` not found | Radxa-only tool. Use the `u-boot-update` method in 1.3. |
| `/boot/firmware/...` or `ubuntuEnv.txt` missing | Different image family. This image uses extlinux and `/etc/default/u-boot`. |
| `/dev/i2c-4/6/8` missing after reboot | `fdtoverlays` line absent or pointing at an old kernel directory. Check `U_BOOT_FDT_OVERLAYS_DIR`, rerun `sudo u-boot-update`, and grep `extlinux.conf`. |
| Overlays stopped working after an update | The kernel version changed. Rerun `sudo u-boot-update`. |
| `ros2: command not found`, `ROS_DISTRO unset` | ROS not sourced, or script run under sudo. Source `/opt/ros/jazzy/setup.bash` and run without sudo. |
| `Package 'goosebot_hw' not found` | Not built into a workspace. Do 1.5, then source `~/ros2_ws/install/setup.bash`. |
| `InvalidParameterTypeException ... none_as ... DOUBLE` | Unquoted `nan` in YAML. Write `none_as: "nan"`. |
| bench_check: Python modules "missing" | Installed under sudo, or run under sudo. Install and run as your normal user. |
| bench_check: not in group `gpio` | Run the `usermod` in 1.1, then log out and back in. |
| `tof_node` finds no sensor | It scans the wrong bus. Set `bus: 4` in the yaml and confirm `0x29` with `i2cdetect -y 4`. |
| A topic echo says "topic not published yet" | The node is not running. Nodes need their own terminal. |

---

# Known problems and risks (roughly by likelihood x severity)

1. **NPU/YOLO.** The `rknpu` driver loads (`rknpu 0.9.7`), but `rknnlite` is not installed and no `librknnrt.so` is
   present. Ubuntu 24.04 uses Python 3.12, so you need a cp312 aarch64 `rknn-toolkit-lite2` wheel (existence for v2.3.0
   was not verified). Test with `bash bench_check.sh --npu-model /path/to/model.rknn`. This decides whether
   `perception_node` can run at all.
2. **Skid-steer + open-loop odom.** 4WD skid-steer scrubs hard in turns; effective track is larger than geometric.
   cmd_vel odometry cannot see slip, battery sag, carpet, or stalls. The gyro rescues yaw rate, but x/y will drift. If
   calibration step 5 fails by more than ~10%, switch to rear-wheel encoders (config note in `ekf_hw.yaml`). Your repo
   already has the encoder code (1092 counts/rev measured).
3. **Sim physics is kinder than reality.** Gazebo DiffDrive has no stiction, deadband, battery sag, or slip. Real TT
   motors stall below `min_duty` and Nav2's small velocity commands get ignored, so the progress checker aborts. Expect
   to retune DWB (min speeds, `PathAlign`, oscillation critic) from scratch.
4. **Stereo from two unsynchronised USB webcams.** No hardware sync, rolling shutter, auto-exposure/white-balance
   mismatch, 0.09 m baseline (sim value; yours may differ), so useful depth is only ~0.3-2 m. Fast turns smear. Nav2's
   sim limit of `max_vel_theta: 3.0` rad/s will wreck stereo matching; keep it at or below 1.0 rad/s.
5. **CPU/RAM.** `bench_check` reports ~1960 MB total RAM, while earlier notes assumed a 4 GB Rock 5C Lite. Confirm with
   `free -m`. Concurrently: YOLO on NPU, 2x USB camera decode, stereo_image_proc, RTAB-Map, Nav2 (2 costmaps), EKF, and
   the Python I2C nodes. Expect to drop camera fps (15 -> 10) and SLAM rate (1 Hz), and to run `rtabmap_viz` and rosbag
   recording off-board. Measure with `top` early. A 1 GB swapfile exists; the headless boot target in 1.7 saves more.
6. **YOLO perception_node conflicts.** It opens `cv2.VideoCapture(0)` exclusively and mirrors frames (`cv2.flip`).
   Change it to subscribe to `/stereo/left/image_raw` (keep the flip local to its own copy, never on stereo images).
   Its `control_node` publishes `/cmd_vel` with unitless steering: re-route to `/cmd_vel_lane` and convert units/sign.
7. **Motor voltage.** Your wiring drives IN1/IN2 per motor from PCA9685 channels, so the L298N ENA/ENB jumpers must stay
   fitted; PWM goes on the IN pins, which is what `motor_driver_node` assumes. The L298N drops ~2 V, so a full 3S pack
   (~12.6 V) puts ~10.6 V on 6-9 V TT motors at 100% duty; hence `max_duty: 0.85`. Check pack voltage under load, the
   L298N 5V-enable jumper/regulator situation on the 12 V rail, and that the Rock 5C gets its own regulated 5 V (your GPS
   notes record a boot failure from a sensor loading the 3.3 V rail).
8. **I2C buses.** The PCA9685 is on I2C8, the IMU on I2C6, and the ToF on I2C4, so one failing device does not hang the
   others. Within a bus, one failing device can still hang it: the nodes catch `OSError` and keep going, but watch for
   stale data. Run at 400 kHz only after verifying clean signals; long wires may need 100 kHz. For four ToFs, each
   board needs XSHUT broken out (check the TOF400C silkscreen) or you need a TCA9548A mux, plus 4 free GPIOs
   (read chip/line with `gpioinfo`). Check whether the TOF400C boards have their own regulator before powering four
   from 3.3 V.
9. **Heading drift.** The EKF fuses gyro-z only, and the MPU6050 has no magnetometer. Heading drifts without bound until
   RTAB-Map corrects it through `map->odom`. In featureless corridors, stereo SLAM loses tracking and heading drifts.
10. **Robot geometry in sim was guessed.** Footprint, wheel radius, track, camera mount, and even weight (1.5 kg) came
    from a photo. Everything tuned in sim for these is provisional.
11. **Power/safety.** Add a physical kill switch or fuse on the battery. The mux publishes zeros if Nav2 dies, and the
    motor driver has a 0.5 s watchdog, but a hung Python process or I2C lockup leaves PWM at its last value (the PCA9685
    keeps running). A hardware cutoff is the only real fix.
12. **TF/time.** There is no `/clock` on hardware (`use_sim_time false` everywhere). The clock was synced when last
    checked, but without an RTC the Rock may boot with a wrong clock; use chrony/NTP before starting ROS or timestamps
    jump.

## Next steps

1. **Bench checks before driving.** Verify the gyro sign (Part 2) and confirm every wheel turns the right way on a
   forward command, with the wheels off the ground.
2. **Motor calibration.** Calibration steps 3-5: `min_duty`, `v_max`, odometry scales, and the EKF square test. Get
   motor stall/no-load figures for your exact TT motors along the way.
3. **Odom-only Nav2 test** (Part 4), starting with a 0.3 m goal in an empty area.
4. **Finish the ToF ring.** Wire the remaining sensors, check the TOF400C XSHUT pinout (or add a TCA9548A mux), pick free
   GPIOs from `gpioinfo`, and restore the 4-sensor config (1.6). Fit `offsets_m`/`scales` against tape-measured
   distances (calibration step 6). Then switch from the odom-only Nav2 params to the normal ones, which expect all
   the ToF sources.
5. **Stereo and SLAM.** Mount the cameras rigidly, fill in the by-path device names, run calibration steps 7-9, then
   SLAM (step 11). Before that, confirm that `rtabmap_launch` on Jazzy accepts every launch argument used in
   `hw_slam.launch.py` (`ros2 launch rtabmap_launch rtabmap.launch.py -s`) and that `robot_hw.urdf.xacro` expands
   cleanly with `xacro`.
6. **NPU/YOLO.** Install a cp312 `rknn-toolkit-lite2` wheel and `librknnrt.so`, then run
   `bash bench_check.sh --npu-model /path/to/model.rknn`.
7. **Confirm the board's RAM** with `free -m` (see risk 5).
