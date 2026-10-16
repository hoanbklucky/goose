# goosebot_hw: sim -> real hardware
# This is just the package, paste it inside a ros2_ws/src in order to build the other necessary files
# Note that a majority of this README is AI-generated while progress is ongoing, though this will be redone when the project is complete. Verify everything you see here before doing anything to the robot

What this is: a ROS 2 package that replaces everything Gazebo provided in `goosebot_0` (diff-drive plugin,
sensor plugins, ground-truth pose, camera_info) with real drivers, and keeps the parts that are
sim-independent (URDF frames, EKF structure, RTAB-Map stereo SLAM, Nav2 layout).

**Nothing here has been run on hardware.** Python files compile and the motor math / YAML were checked on a
laptop; no ROS, no I2C, no cameras were available. Treat every node as "reviewed code", not "tested code".

## Sim -> hardware mapping

| Sim | Hardware |
|---|---|
| gz DiffDrive plugin | `motor_driver_node` (PCA9685 -> L298N), real units, deadband, watchdog |
| gz `/cmd_vel` bridge | `cmd_vel_mux_node` -> `/cmd_vel_mux` -> motor driver |
| `cmd_vel_to_odom.py` on raw `/cmd_vel` | same script on `/cmd_vel_applied` (what the motor driver actually sent) |
| gz IMU (perfect orientation) | `imu_node`: MPU6050, **orientation published as unknown**, gyro-z only |
| gz gpu_lidar single beam ToF | `tof_node`: 4x VL53L1X, XSHUT address assignment, same LaserScan shape |
| gz stereo cameras + `stereo_camera_info_fixer` | `stereo_camera_node` + `stereo_image_proc` + your calibration YAML |
| `ground_truth_map_odom_bridge` + baked map | **removed**. RTAB-Map owns `map->odom` and `/rtabmap/map` |
| gz GPS | not ported (no use indoors; EKF never used it) |
| sim `nav2_params.yaml` | `nav2_params.yaml` (same Jazzy naming; hardware limits, 4 ToF sources, footprint) |

Node graph: `teleop/Nav2/lane -> cmd_vel_mux -> motor_driver -> (/cmd_vel_applied) -> cmd_vel_to_odom -> EKF(+IMU gyro z) -> /odometry/filtered -> RTAB-Map -> map->odom -> Nav2`.

## Distro / OS (updated: sim = Jazzy, Rock 5C = Ubuntu 24.04 + Jazzy)

Sim and hardware are now on the same distro, so the sim's Nav2 params, plugin names, `opennav_docking`, and the
RTAB-Map/EKF launch structure carry over unchanged (`config/nav2_params.yaml` is the sim file with hardware edits).
The earlier Humble/Debian source-build problem no longer applies. New things to check on the Ubuntu 24.04 image
(none of these could be verified from here):

1. **NPU driver.** YOLO on the RK3582 NPU needs a kernel with Rockchip's `rknpu` driver. Check
   `sudo dmesg | grep -i rknpu` and `ls /dev/dri`. If the Ubuntu 24.04 image runs a mainline kernel, the NPU may be unavailable.
   This is the first thing to test: it decides whether `perception_node` can run at all.
2. **RKNN runtime wheel.** Ubuntu 24.04 uses Python 3.12. Your notes install the cp311 `rknn_toolkit_lite2` wheel.
   Check `rknn-toolkit2/rknn-toolkit-lite2/packages/` for a cp312 aarch64 wheel; I did not verify one exists for v2.3.0.
3. **libgpiod version.** Your old notes require v1.6.3. Ubuntu 24.04 may have v1 or v2 via apt. `python3 -c "import gpiod; print(gpiod.__version__)"`.
   `tof_node` supports both; your old encoder scripts (`motor_encoder_keyboard_v4/v5.py`, `encoder_odom.py`) are v1-only.
4. **Overlays.** Confirm `rsetup` (or the 24.04 image's equivalent) still lets you enable I2C8-M2 (PCA9685) and I2C6-M0 (IMU).
5. **apt packages on arm64.** `apt install ros-jazzy-{nav2-bringup,robot-localization,rtabmap-ros,stereo-image-proc,xacro}`
   then check `apt-cache policy` for each; availability for arm64 was not verified.
6. **Python packages.** 24.04 enforces PEP 668. ROS nodes run on the system Python, so use
   `pip install --break-system-packages smbus2 pyyaml adafruit-circuitpython-vl53l1x adafruit-circuitpython-pca9685 adafruit-blinka`
   (your own Debian notes already use that flag) rather than a venv.
7. **Blinka on this board.** `adafruit-blinka` must recognise the Rock 5C; your motor test already worked with it on the Debian image.

## Install (after OS decision)

```bash
cd ~/ros2_ws/src && cp -r <this package> goosebot_hw
# see 'Python packages' above; keep whatever gpiod apt installs, tof_node handles v1 and v2
cd ~/ros2_ws && colcon build --packages-select goosebot_hw --symlink-install --parallel-workers 2
source install/setup.bash
```

Before first launch fill in `config/hw_params.yaml`: ToF XSHUT chips/lines, stereo device paths, calibration YAML paths.

Bring-up order (bench first, **wheels off the ground** until step 3):
1. `ros2 launch goosebot_hw hw_bringup.launch.py with_stereo:=false`
2. Add stereo after step 7.
3. `ros2 launch goosebot_hw hw_slam.launch.py` (mapping) -> drive manually -> later `localization:=true`
4. `ros2 launch goosebot_hw hw_nav2.launch.py`

## Calibration procedure (in this order; each step feeds the next)

1. **Geometry.** Per your instruction the hardware URDF now uses your notes, not the sim guesses: track 5.3 in = 0.1346 m,
   wheel diameter 2.6 in = 0.066 m (`EncoderCalibration` doc; the v5 encoder script says 2.5 in, so measure it),
   chassis ~0.161 x 0.102 m from the STEP file (raw STEP points, treat as +-10 mm), footprint 0.17 x 0.17 m.
   NOT in any note, so still guesses: wheel x-offset (0.07), wheel width (0.025), all camera/ToF/IMU mount positions,
   and the stereo baseline (0.09). Measure those and edit `urdf/robot_hw.urdf.xacro` + `wheel_separation` in params.
2. **IMU.** Warm up 2-3 min (MPU6050 bias drifts with temperature), robot stationary, start `imu_node`; it measures bias
   and variance itself. Then rotate the robot CCW by hand: `/imu/data` `angular_velocity.z` must be **positive**; if not,
   `gyro_z_sign: -1.0`. Check `ros2 topic echo /imu/data --field orientation_covariance` starts with -1.
   Drift check: leave still 5 min, integrate z; record the drift rate.
3. **Motor feedforward** (wheels on the floor, battery ~11.4 V, measure with a stopwatch + tape):
   - `min_duty`: lowest duty at which all four wheels start from rest, on your real floor surface. Do it driving
     straight AND spinning in place; skid-steer spin needs much more duty than straight driving.
   - `v_max`: drive 2 m at `max_duty` via `/cmd_vel_teleop`, time it. Repeat at 100%, 50% of v_max to check linearity.
   - Re-do at ~12.4 V and ~10.8 V. If speed varies >15% across the pack range, open-loop odometry will be bad
     (this is your trigger for encoders).
4. **Odometry scale.** Command 1.0 m straight x5 -> `linear_scale = measured/commanded`. Command 360 deg in place x5
   -> `angular_scale`. Expect the robot to turn LESS than commanded (skid-steer scrub); expect run-to-run variance.
   The std-dev across runs is your real covariance: set `xy_var`, `vx_var` from it, not from my placeholders.
5. **EKF sanity.** Drive a 2 m x 2 m square, return to start, compare `/odometry/filtered` end pose to a tape-measured one.
   Also tf-echo `odom->base_footprint` while stationary: it must not creep. Tune `process_noise_covariance` only after
   steps 2-4 are done.
6. **ToF.** Put a flat matte target at 10/20/40/80/120 cm per sensor, fit `offset_m`/`scale` per sensor. Test on dark
   and glossy surfaces and under bright light; log how often `None`/NaN appears. Pick `distance_mode` (short is more
   ambient-light robust; long reaches further). Confirm the sensors do not interfere (adjacent cones).
7. **Stereo.** Print a checkerboard (flat, rigid), run `camera_calibration` stereo (`cameracalibrator` with
   `--approximate`) at your final resolution and fps; save to `left.yaml`/`right.yaml`. Gate: RMS reprojection error
   well under 0.5 px and epipolar lines horizontal. Rigidly fix both cameras to one plate: any flex after calibration
   invalidates it. Use `v4l2-ctl` to set the same fixed exposure/white balance/focus on both. Verify depth against a tape
   measure at 0.5/1/1.5/2 m (sim script `check_stereo_depth.py` is a starting point).
8. **Camera-to-base extrinsics.** The URDF assumes cameras centred and level. Measure real height, pitch, offset, put
   them in the URDF. A few degrees of unmodelled pitch skews the SLAM grid projection.
9. **Latency/sync.** Wave an object in front of both cameras while recording; inspect left/right frame skew. Tune
   `latency_s`. Check `/stereo/*/image_raw` timestamps vs `ros2 topic delay`.
10. **Nav2 limits.** Set `max_vel_x`, `max_vel_theta`, accelerations to ~70% of the measured achievable values from
    step 3, not the starting values in the YAML. Check DWB does not command speeds below the deadband for long.
11. **SLAM first, Nav2 second.** Map a small loop at slow speed with `rtabmap_viz` on a laptop; confirm loop closure
    and a clean `/rtabmap/map` before ever sending a Nav2 goal.

## Known problems and risks (roughly by likelihood x severity)

1. **Ubuntu 24.04 image unknowns** (NPU kernel driver, RKNN cp312 wheel, libgpiod version, arm64 apt coverage; see
   "Distro / OS"). The NPU one is the only potential blocker; the rest are small.
2. **Skid-steer + open-loop odom.** 4WD skid-steer scrubs hard in turns; effective track is larger than geometric.
   cmd_vel odometry cannot see slip, battery sag, carpet, or stalls. Gyro rescues yaw rate, but x/y will drift. If step 5
   fails by more than ~10%, switch to rear-wheel encoders (config note in `ekf_hw.yaml`). Cheap to do; your repo already has
   the encoder code (1092 counts/rev measured).
3. **Sim physics is kinder than reality.** Gazebo DiffDrive has no stiction, no motor deadband, no battery sag, no slip,
   and torque of 10 N·m per wheel. Real TT motors will stall below `min_duty` and Nav2's small velocity commands will be
   ignored -> progress checker aborts. Expect to retune DWB (min speeds, `PathAlign`, oscillation critic) from scratch.
4. **Stereo from two unsynchronised USB webcams.** No hardware sync, rolling shutter, auto-exposure/white-balance mismatch,
   0.09 m baseline (sim value; yours may differ) => useful depth only ~0.3-2 m, noisier than the sim's perfect pair. Fast
   turns smear. Nav2's sim limit of `max_vel_theta: 3.0` rad/s will wreck stereo matching; keep <=1.0 rad/s.
5. **CPU/RAM on the Rock 5C Lite (4 GB, RK3582).** Concurrently: YOLO on NPU, 2x USB camera decode, stereo_image_proc,
   RTAB-Map, Nav2 (2 costmaps), EKF, 4 Python I2C nodes. Expect to drop camera fps (15 -> 10), SLAM rate (1 Hz), and
   possibly to run rtabmap_viz and rosbag recording off-board. Measure with `top` early; add swap (your repo already notes it).
6. **YOLO perception_node conflicts.** It opens `cv2.VideoCapture(0)` exclusively and mirrors frames (`cv2.flip`).
   Change it to subscribe to `/stereo/left/image_raw` (and keep the flip local to its own copy, never on stereo images). Its
   `control_node` publishes `/cmd_vel` with unitless steering: re-route to `/cmd_vel_lane` and convert units/sign.
7. **Motor voltage.** (Your wiring diagram drives IN1/IN2 per motor from PCA9685 channels, so the L298N ENA/ENB jumpers
   must stay fitted; PWM goes on the IN pins, which is what `motor_driver_node` assumes.) L298N drops ~2 V (verified in several datasheet-derived sources). A full 3S pack (~12.6 V) puts
   ~10.6 V on 6-9 V TT motors at 100% duty; hence `max_duty: 0.85`. Check pack voltage under load; also confirm the L298N
   5V-enable jumper/regulator situation on the 12 V rail and that Rock 5C gets its own regulated 5 V (your GPS notes
   already record a boot failure from a sensor loading the 3.3 V rail).
8. **I2C bus.** PCA9685 + 4x VL53L1X share I2C8 with stacked pull-ups; MPU6050 is on I2C6. Run at 400 kHz only after
   verifying clean signals; long wires to side/rear ToFs may need 100 kHz. One failing device can hang the bus: the nodes
   catch `OSError` and keep going, but watch for stale data. All 4 ToF boards need XSHUT broken out, or add a TCA9548A. ToF is not in your current wiring diagram or notes at all,
   so pick 4 free GPIOs yourself. Header pins already in use per your notes: 3,5 (I2C8/PCA9685), 27,28 (I2C6/IMU),
   11,13,15,16 (encoders), 7,29 (GPS UART4), 36,38 (ultrasonic), plus power/ground. Read the chip/line with
   `gpioinfo` and put them in `tof_node` params. Check whether the TOF400C boards have their own regulator before
   powering four of them from 3.3 V (your GPS notes record a boot failure from a sensor loading that rail).
9. **Heading drift.** The EKF fuses gyro-z only, MPU6050 has no magnetometer. Heading is unbounded-drift until RTAB-Map
   corrects it through `map->odom`. In featureless corridors (blank walls) stereo SLAM loses tracking and heading drifts.
10. **Robot geometry in sim was guessed.** Footprint, wheel radius, track, camera mount, even weight (1.5 kg) came from a
    photo. Everything tuned in sim for these is provisional.
11. **Power/safety.** Add a physical kill switch / fuse on the battery. The mux publishes zeros if Nav2 dies, and the
    motor driver has a 0.5 s watchdog, but a hung Python process or I2C lockup leaves PWM at its last value (PCA9685
    keeps running). A hardware cutoff is the only real fix.
12. **USB device naming.** `/dev/video0/1` can swap on reboot -> left/right silently swapped -> garbage depth. Use by-path.
13. **TF/time.** No `/clock` on hardware (`use_sim_time false` everywhere). Without an RTC the Rock may boot with a wrong
    clock; use chrony/NTP before starting ROS or timestamps jump.

## Things I could not verify
- Real values: chassis dimensions, TOF400C pinout (XSHUT), motor stall/no-load figures for your exact TT motors.
- Adafruit VL53L1X API details beyond what the Adafruit docs example shows (`set_address`, ranging start); `distance` units
  are cm in my memory of the library.
- That `rtabmap_launch` on Jazzy accepts every launch argument used in `hw_slam.launch.py` (`database_path`,
  `localization`, etc.): confirm with `ros2 launch rtabmap_launch rtabmap.launch.py -s`.
- `xacro` expansion of `robot_hw.urdf.xacro` (no xacro in my sandbox; XML is well-formed).


## Staged Nav2 test without SLAM or cameras (odom-only)

Purpose: test the controller and your motor calibration on the real floor before the stereo mount and SLAM exist.
This is where the "motor deadband vs Nav2's small commands" risk shows up first.

```
ros2 launch goosebot_hw hw_bringup.launch.py with_stereo:=false
ros2 launch goosebot_hw hw_nav2.launch.py odom_only:=true
```

What `odom_only` does: loads `nav2_params_odom_only.yaml` (global costmap without the static map layer, unknown space
treated as free) and publishes an identity `map -> odom` transform. Send goals in the `map` frame.

Preconditions (do not skip):
1. **IMU working, gyro sign verified.** Without the gyro, the EKF never sees the robot rotate (cmd_vel odometry
   yaw is deliberately not fused), and Nav2 will keep commanding turns that "never happen".
2. Motor calibration steps 3-5 done (min_duty, v_max, scales).
3. Empty floor, at least ~2 m x 2 m, kill switch in hand.
4. **No obstacle protection in this mode.** Nav2's collision monitor stops the robot when any of its
   sources has not published within `source_timeout`, including data that was never received (Nav2 docs; setting
   `source_timeout: 0.0` disables that). Normal config uses 0.5 s, so with the ToFs unplugged the robot would not move at all.
   The odom-only file sets it to 0.0 for that reason. Once the ToFs are live use the normal file.
5. Do not run it together with RTAB-Map (both publish `map -> odom`).

Start with a 0.3 m goal straight ahead, then a 90 degree turn goal, then 1 m. Watch for: stalls (raise `min_duty`),
oscillation or never reaching the goal (tolerances, `max_vel_theta`), and drift against a tape-measured distance.
Run RViz on a laptop, not on the 2 GB Rock (needs the same ROS_DOMAIN_ID and a working network; not verified here).
