# goosebot_hw with lidar and wheel encoders

The Goosebot hardware package (`goosebot_hw`, ROS 2 Jazzy) for the robot version with an **RPLIDAR C1** and **hall
encoders on the two front wheels**. It grew out of `12_new_hw/` and keeps everything that works there (stereo
RTAB-Map, Nav2, map modes, relocalization); this section adds the lidar and encoders, the 32 Hz motor recalibration,
rear-wheel speed matching and a measured speed table.

The lidar and encoders are permanent on this version. A later redesign plans to replace them with optical-flow
odometry and better-tuned stereo, so this section is kept separate from `12_new_hw/` on purpose.

Hardware: Radxa Rock 5C (2 GB), 4 skid-steer motors on a PCA9685 + 2x L298N (front: new hall-encoder motors, rear: old
TT motors), MPU6050 IMU, one front VL53L1X ToF, two USB webcams as a stereo pair, RPLIDAR C1 on USB.

For flashing the board, I2C overlays, the base install and the stereo calibration, follow `12_new_hw/README.md` Parts 1-3
first. Everything below assumes that works.

## Status (2026-11-19)

| Item | State |
|---|---|
| Lidar driver, URDF link, mount measured, orientation and self-hit checks | Done, tested on the bench |
| Front encoders: wiring, `encoder_node`, EKF forward speed from `/wheel/odom` | Done, tested (tape vs encoder within 1-2 %) |
| 32 Hz PWM, rear-wheel matching, speed table, floors, `v_max` | Done, tested on the floor at 11.73 V |
| Nav2 costmaps + collision monitor with the lidar, RTAB-Map with scans, AMCL for `rtab:=false` | Written, not run yet |
| Leftward drift (~6 deg per metre) | Open, see "Open problems" |
| `angular_scale`, 2 m square, first lidar map, navigation on it | To do |

---

## What changed vs `12_new_hw`

| Area | `12_new_hw` | This version |
|---|---|---|
| Obstacle sensing | one front ToF beam | ToF + 360 deg lidar (`/scan`) in both costmaps and the collision monitor |
| EKF forward speed | open-loop cmd_vel (`/odom_cmdvel`) | front-wheel encoders (`/wheel/odom`); cmd_vel odometry still runs for comparison only |
| RTAB-Map | stereo only, grid to 2 m | stereo + scans: ICP refines odometry between map nodes, grid from the lidar to 5 m |
| `rtab:=false` | fixed start pose, drift never corrected | AMCL localizes on the saved grid with the lidar |
| Motors | 100 Hz, one duty for all four, straight-line speed model | 32 Hz, rear duty matched to the front on each side, measured speed table |
| Optional | none | lidar odometry (`lidar_odom:=true`, RTAB-Map `icp_odometry` fused into the EKF) |

Node graph:
`teleop/Nav2 -> cmd_vel_mux -> motor_driver (speed table, rear matching) -> wheels -> encoder_node (/wheel/odom) ->
EKF (+ IMU gyro z, + optional /odom_icp) -> /odometry/filtered -> RTAB-Map (stereo + /scan) -> map->odom -> Nav2
(costmaps: ToF + /scan)`

---

## Hardware

### Header and buses

| Device | Pins | Linux | Notes |
|---|---|---|---|
| PCA9685 (motor PWM) | 3 SDA, 5 SCL | `/dev/i2c-8`, 0x40 | 32 Hz |
| MPU6050 IMU | SDA 27, SCL 28 | `/dev/i2c-6`, 0x68 | gyro z only is fused |
| VL53L1X front ToF | SDA 23, SCL 24 | `/dev/i2c-4`, 0x29 | |
| IMU + ToF power | pin 1 (3.3 V), Y-splice | | |
| Encoders power | pin 17 (3.3 V), Y-splice to FL and FR | | **3.3 V only.** Never 5 V or the PCA header |
| Encoder FL | A pin 16, B pin 18, GND pin 20 | gpiochip1 lines 5 / 8 | |
| Encoder FR | A pin 22, B pin 26, GND pin 25 | gpiochip1 lines 13 / 4 | |
| RPLIDAR C1 | USB (CP2102N adapter) | `/dev/rplidar` -> `/dev/ttyUSB0` | 460800 baud |
| Cameras | two USB ports on separate controllers | `/dev/cam_left`, `/dev/cam_right` | |

Do not use pins 8/10 (debug serial console). An encoder on pin 10 is invisible to Linux and its pulses can stop the
boot at the bootloader prompt.

### Motors

| Position | Motor | PCA channels (`hw_params.yaml`) |
|---|---|---|
| FL | new, hall encoder | `fl: [6, 7]` |
| FR | new, hall encoder | `fr: [0, 1]` |
| RL | old TT | `rl: [4, 5]` |
| RR | old TT | `rr: [3, 2]` |

Channel order sets the direction: swapping the two numbers reverses that motor. With the wheels lifted and the robot
told to drive forward, all four must turn forward.

### Mount geometry (URDF `urdf/robot_hw.urdf.xacro`)

| Part | Position |
|---|---|
| Lidar spin axis | x +0.030 m (forward of chassis centre), y 0 |
| Lidar scan plane | 0.182 m above the floor (middle of the C1's window band) |
| Lidar yaw | 180 deg (`${pi}`): the C1's zero angle points backwards |
| Stereo lens centre | 0.132 m above the floor, 0.0969 m forward, pitched 5 deg up, baseline ~78 mm |
| Wheels | radius 0.03305 m, track 0.137 m |

The scan plane must stay above the camera tops (~0.145 m) and below `cutoffs.top` in `slam_params.yaml` (0.25 m).

---

## Software setup (on top of `12_new_hw` Part 1)

### Lidar driver

```bash
cd ~/ros2_ws/src
git clone https://github.com/Slamtec/sllidar_ros2.git
sudo apt install ros-jazzy-nav2-amcl
cd ~/ros2_ws
MAKEFLAGS=-j1 colcon build --packages-select sllidar_ros2 --parallel-workers 1
colcon build --packages-select goosebot_hw --symlink-install
source install/setup.bash
ros2 pkg executables sllidar_ros2          # sllidar_node
ros2 pkg executables goosebot_hw | grep encoder   # encoder_node
```

The `sllidar_ros2` build prints many warnings from Slamtec's SDK (zero-size arrays, unused parameters). They are
harmless; success is `Summary: N packages finished`. The apt package `ros-jazzy-rplidar-ros` may not support the C1
yet, which is why the driver is built from source. `-j1` avoids running out of RAM on the 2 GB board.

### Lidar device name

```bash
lsusb | grep -i cp210                      # 10c4:ea60
sudo cp ~/goosebot_hw/scripts/99-rplidar.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add --sysname-match=ttyUSB0 && sudo udevadm settle
ls -l /dev/rplidar
```

If the link does not appear, unplug and replug the lidar. `/dev/serial/by-id/usb-Silicon_Labs_CP2102N_...` also works as
`serial_port`.

### Encoder lines

```bash
gpioinfo gpiochip1 | grep -E "line +(4|5|8|13):"     # all four: unused, input
```

The board ships libgpiod **v1** (`gpioget gpiochip1 5 8`); the code supports v1 and v2.

### Configuration files

| File | Contents |
|---|---|
| `config/hw_params.yaml` | motor driver (PWM, floors, speed table, wheel matching, trims), IMU, ToF, cameras, cmd_vel odometry |
| `config/lidar_params.yaml` | `sllidar_node`: port, 460800 baud, frame `lidar_link`, scan mode Standard |
| `config/encoder_params.yaml` | `encoder_node`: lines, signs, counts per turn, scale, variance |
| `config/ekf_hw.yaml` | EKF base config; `hw_bringup` swaps odom0 to `/wheel/odom` and adds odom1 for lidar odometry |
| `config/slam_params.yaml` | RTAB-Map: image filter, height cutoff, `lidar:` (grid sensor, ICP), maps, relocalization |
| `config/nav2_params.yaml` | Nav2 (ToF + lidar sources, AMCL section); `nav2_params_odom_only.yaml` for the staged test |

Python and YAML edits apply on the next launch (`--symlink-install`); a new file or a new node needs one rebuild.

---

## Running

All launch files from `12_new_hw` work as before (`hw_robot.launch.py` with `read` / `write` / `static` / `rtab`, see
that README). New arguments, accepted by `hw_robot.launch.py` and `hw_bringup.launch.py`:

| Argument | Default | Meaning |
|---|---|---|
| `with_lidar` | `true` | lidar driver; RTAB-Map subscribes to `/scan`; Nav2 uses it. `false` removes it everywhere |
| `with_encoders` | `true` | `encoder_node` on `/wheel/odom` |
| `odom_source` | `auto` | EKF forward speed: `auto` (encoders when on) / `encoders` / `cmd_vel` |
| `lidar_odom` | `false` | fuse RTAB-Map `icp_odometry` (scan matching) into the EKF |

`rtab:=false` with the lidar on runs AMCL on the saved grid. It assumes the robot starts at the map origin; give the real
pose with "2D Pose Estimate" in RViz if not. The grid must be a lidar grid (made by this version).

Bringup log lines to check:

```
[hw_bringup] EKF: forward speed from wheel encoders (/wheel/odom), yaw rate from gyro
[encoder_node]: encoders on /dev/gpiochip1 ... 1090 counts/rev = 0.191 mm/count
[motor_driver]: speed table on: 13 points, 0.10->0.073 m/s ... 0.33->0.352 m/s
[motor_driver]: wheel matching on (front duty -> rear duty): 0.08->RL 0.059/RR 0.064, ...
[motor_driver]: motor_driver up ... pwm=32 Hz ... trim L/R (1.0, 1.0)
[lidar]: current scan mode: Standard, sample rate: 5 Khz, max_distance: 16.0 m, scan frequency:10.0 Hz
```

**Only one program may drive the motors or read the encoders at a time.** Stop bringup before any test script
(`encoder_check.py`, `floor_calib.py`, motor test scripts); otherwise the driver writes zero to the PCA9685 50 times a
second and the wheels only twitch. Check with `pgrep -af "motor_driver_node|encoder_node"`.

### Mapping and driving from the laptop

Laptop: ROS 2 Jazzy, same Wi-Fi as the robot (the VPN blocks the UDP traffic), and in `~/.bashrc`:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
```

```bash
# robot: new map with Nav2 on (a new map normally starts without Nav2)
ros2 run rtabmap_slam rtabmap --params 2>/dev/null | grep "Grid/Sensor"     # must print the parameter
ros2 launch goosebot_hw hw_robot.launch.py write:=lab_lidar with_nav2:=true

# laptop
rviz2            # fixed frame map; add /rtabmap/map (Transient Local), /scan (Best Effort),
                 # /local_costmap/costmap, /global_costmap/costmap, /plan, RobotModel (/robot_description)
ros2 run rqt_image_view rqt_image_view        # /stereo/left/image_rect (raw, ~4-5 MB/s: may lag over Wi-Fi)
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_teleop
```

Send goals with **2D Goal Pose** in RViz. Safety when the robot is out of sight:

- Nav2 goals pass through the collision monitor (lidar + ToF). **Keyboard teleop bypasses it.** Use Nav2 goals when
  you cannot see the robot.
- If Wi-Fi drops, teleop stops within 0.5 s (mux + driver timeouts). A running Nav2 goal continues on the robot,
  protected by the collision monitor.
- The lidar sees nothing below ~0.18 m; only the front ToF and the cameras cover low obstacles, ahead only.
- Stop with one Ctrl+C on the robot and wait for `[maps] saved`.

If `ros2 node list` shows fewer nodes than are running, the ROS daemon is stale: `ros2 daemon stop`, then use
`--no-daemon`.

---

## Calibration (in this order)

Values measured on 2026-11-19 are in "Calibration record" below. Redo a step whenever its hardware changes.

### 1. Lidar orientation and self-hits (robot lifted or on a bench)

```bash
ros2 launch goosebot_hw hw_bringup.launch.py with_imu:=false with_tof:=false with_stereo:=false with_encoders:=false
python3 ~/goosebot_hw/scripts/scan_check.py
```

- Clear space: must print `OK: nothing closer than 0.15 m`. Near returns at a fixed angle are the robot itself (or
  your arm); fix the mount, do not filter. The collision monitor has no minimum range.
- Face a flat wall squarely: the closest return must read near 0 deg. With `lidar_yaw` 0 it read -178 deg, hence
  `${pi}`.

### 2. Encoders (bringup stopped)

```bash
python3 ~/goosebot_hw/scripts/encoder_check.py
```

- No counts on one wheel: check the pins with `gpioget gpiochip1 5 8` while turning it. A constant value (for example
  `0 1`) means nothing drives the lines (wrong pins, no power, loose plug).
- Counts per turn: tape mark, exactly 10 turns, Ctrl+C. Both wheels should agree within a few counts.
- **Sign: decide it by pushing the robot forward on the floor**, not by turning a lifted wheel by hand (easy to turn
  the wrong way). With bringup running, `ros2 topic echo /wheel/odom --field pose.pose.position.x` must rise by about
  the pushed distance. If it stays near 0, one sign is wrong; if it goes negative, both are.

### 3. Rear-wheel matching (wheels lifted, bringup stopped)

The rear motors turn ~1.46x faster than the front motors at the same duty, so each rear gets the duty that matches its
front's speed. Time each wheel (motor test script `hold --wheel <fl|fr|rl|rr> --dir fwd --duty D --freq 32`; stopwatch
over 5 turns, or encoder edges/s / 1090 for the fronts) at:

- fronts: 0.08, 0.15, 0.30
- rears: 0.05, 0.06, 0.08, 0.15, 0.30

and enter turns per second in `wheel_cal_fl/fr/rl/rr`. Time 5 turns, not 1: a single-turn timing gave a bad RR point.
Check after: drive slowly with teleop, lifted: front and rear on each side turn at the same speed.

### 4. Floors, top speed and the speed table (on the floor, bringup stopped)

```bash
python3 ~/goosebot_hw/scripts/floor_calib.py straight                              # ~1 m clear front and back
python3 ~/goosebot_hw/scripts/floor_calib.py spin                                  # ~0.4 m clear around
python3 ~/goosebot_hw/scripts/floor_calib.py vmax                                  # speed at max_duty
python3 ~/goosebot_hw/scripts/floor_calib.py straight --start 0.31 --stop 0.19 --step 0.03   # fill the table
```

The script drives exactly like the driver (32 Hz, kick, rear matching), measures speed with the encoders and turn rate
with the gyro, and prints values to paste:

- `straight` -> `min_duty` and the low end of the speed table
- `spin` -> `min_duty_spin`, `w_floor`
- `vmax` + gap fill -> the rest of the speed table. Table speed = mean of forward and reverse at each duty.

Note the battery voltage: floors rise as the pack sags. If the robot stalls at ~11 V, rerun `straight` and raise the
first table duty.

If `floor_calib` shows a high floor with the robot curving, check that all four wheels turn the right way (a reversed RL
looked exactly like that).

### 5. Distance (`linear_scale` in `encoder_params.yaml`)

```bash
ros2 launch goosebot_hw hw_bringup.launch.py with_stereo:=false
python3 ~/goosebot_hw/scripts/drive_test.py lin 0.15 6.67      # 1 m forward; lin -0.15 6.67 back
```

Tape the real distance; `linear_scale` = tape / encoder distance (mean over 3-5 runs). `vx_var` from the run-to-run
spread (about (spread in m / run time in s)^2, not below 0.0005). A single run that comes up far short (the robot hit a
cable or rug edge) is not a calibration point; repeat it.

### 6. Turn rate (`angular_scale` in `hw_params.yaml`)

```bash
python3 ~/goosebot_hw/scripts/drive_test.py ang 0.8 7.854      # 360 deg CCW
python3 ~/goosebot_hw/scripts/drive_test.py ang -0.8 7.854     # 360 deg CW
```

Three each. New `angular_scale` = current x (mean real angle / 360). The gyro reading should be within ~3 % of the real
angle.

### 7. EKF check: 2 m square

Restart bringup (EKF at 0,0,0), tape the start, then:

```bash
cd ~/goosebot_hw/scripts
for i in 1 2 3 4; do python3 drive_test.py lin 0.15 13.33; python3 drive_test.py ang 0.8 1.963; done
```

Compare the last `EKF end pose` with the real end position and heading (good: within ~10 cm and 5 deg after 8 m). Repeat
with `lidar_odom:=true` to see whether lidar odometry helps.

### 8. Nav2 limits

Keep Nav2's speeds inside what the robot can hold: `max_vel_x` above the slowest table speed and below ~70 % of `v_max`;
`max_vel_theta`, the recovery spin's `min_rotational_vel` and the relocalization `spin_speed` above `w_floor`; at most
1.0 rad/s for the cameras.

---

## Calibration record

Measured 2026-11-19, battery 11.73 V (~62 %), indoor floor.

| Parameter | Value | File |
|---|---|---|
| `pwm_frequency` | 32 | hw_params |
| `max_duty` | 0.33 (keep the motors at or below ~1/3 power) | hw_params |
| `kick_duty`, `kick_time` | 0.30, 0.04 s (one PWM period at 32 Hz is 31 ms) | hw_params |
| `min_duty_spin`, `w_floor` | 0.24, 0.545 rad/s (spins down to 0.22) | hw_params |
| Speed table duty | 0.10 0.11 0.12 0.13 0.14 0.15 0.16 0.19 0.22 0.25 0.28 0.31 0.33 | hw_params |
| Speed table m/s | 0.073 0.0985 0.125 0.146 0.163 0.179 0.1945 0.219 0.2505 0.2775 0.3055 0.3355 0.352 | hw_params |
| `wheel_cal_duty_front`; FL; FR (turns/s) | 0.08 0.15 0.30; 0.765 1.163 1.779; 0.781 1.142 1.779 | hw_params |
| `wheel_cal_duty_rear`; RL; RR (turns/s) | 0.05 0.06 0.08 0.15 0.30; 0.455 0.801 1.136 1.701 2.564; 0.345 0.687 1.111 1.667 2.688 | hw_params |
| Lifted start / run duty | 0.05-0.06 / 0.02-0.04, all four motors | (reference) |
| `counts_per_rev` | 1090 (FL 1090.1, FR 1089.3; 0.191 mm per count) | encoder_params |
| `fl_sign`, `fr_sign` | -1, 1 | encoder_params |
| `linear_scale`, `vx_var` | 0.98, 0.002 | encoder_params |
| `angular_scale` | 0.78 (old value, redo step 6) | hw_params |
| Nav2 | max_vel_x 0.2, max_vel_theta 1.0, recovery spin 0.77-1.0 rad/s | nav2_params |

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `motor_driver` dies: `speed_table is on but speed_table_duty / speed_table_speed are missing` | Table lines missing or outside the `motor_driver:` section / wrong indentation in `hw_params.yaml`. |
| Wheels only twitch during a motor test | Bringup is still running; its driver keeps writing zero. Stop it. |
| One encoder never counts | Check `gpioget gpiochip1 <A> <B>` while turning: a constant value means no signal (wrong pins, power, plug). |
| `encoder_node: counts_per_rev is 0` | Calibrate (step 2) or launch `with_encoders:=false`. |
| `encoder_node` / `encoder_check.py`: `Device or resource busy` | Another program holds the lines; only one at a time. |
| Robot drives but `/odometry/filtered` stays still or the EKF speed is ~0 | Encoder sign wrong (the two wheels cancel); push test in step 2. |
| `encoder_node` warns about missed edges | CPU cannot keep up with the edge rate; next step would be the kernel's encoder driver instead of Python. |
| `/dev/rplidar` missing | `udevadm trigger --action=add --sysname-match=ttyUSB0`, or replug. |
| Lidar node: timeout / no data | Wrong port or baud (460800 for C1), or no permission (udev rule, `dialout` group). |
| Robot will not drive forward under Nav2 | Collision monitor sees the robot itself: `scan_check.py` must show nothing closer than 0.15 m. |
| RTAB-Map makes no map | `/scan` not publishing while `with_lidar:=true`, or `cutoffs.top` below the scan plane. |
| `drive_test.py` reports `n/a` for the EKF | Old version of the script; the current one spins in a background thread and prints message counts. |
| `ros2 node list` misses running nodes | Stale daemon: `ros2 daemon stop`, then `--no-daemon`. |
| `colcon` build of `sllidar_ros2` killed | Out of RAM: `MAKEFLAGS=-j1 ... --parallel-workers 1`. |
| Unzipped files not used | Zip extracted into a nested `goosebot_hw/goosebot_hw/...`; copy the contents up a level and rebuild. |

---

## Budget tradeoffs (this version)

1. **Front wheels only are measured.** Rear motors are open loop (matched by a lifted-wheel table). Slip of the front
   wheels on a slippery floor over-reads distance. Skid-steer yaw still comes from the gyro; encoder yaw rate is
   published but not fused.
2. **Mismatched motors.** New front and old rear motors differ ~1.46x in speed per duty; the matching table holds only
   as long as the motors do. Re-measure after swapping a motor. Rear matching was measured driving forward only.
3. **Open-loop speed.** The speed table is measured at one battery voltage. Commanded vs real speed is within ~5 %
   forward and ~10 % reverse at 11.7 V; it drifts as the pack drains. Closed-loop speed control from the encoders is not
   implemented.
4. **Lidar above the cameras.** 360 deg coverage, but nothing below ~0.18 m is seen at the sides or rear.
5. **Python encoder decoding.** Every edge is one kernel event handled in Python (~1000 edges/s per wheel at hand speed,
   several thousand at full speed). Not yet checked with the full stack running.
6. Everything from `12_new_hw` "Budget tradeoffs" that is not listed here still applies (2 GB RAM, unsynchronized USB
   webcams, no magnetometer, no hardware cutoff, no RTC).

---

## Open problems

1. **Leftward drift.** ~6 deg per metre forward (gyro and EKF agree); the right front encoder reads ~2 % faster than the
   left. A right-side speed trim (`speed_trim_right` 0.98 down to 0.85, confirmed applied in the log) did not change it,
   so it is probably not steady front-wheel speed. Next: compare the yaw of a 1 m and a 2 m run and watch
   `/imu/data` `angular_velocity.z` while cruising. Steady rate = per-side rear matching; spikes at start/stop = kick.
   Not blocking: the gyro and EKF track the heading and Nav2 steers continuously.
2. **Not run yet:** Nav2 with the lidar sources, RTAB-Map with scans (`Grid/Sensor` name to confirm), AMCL in
   `rtab:=false`, lidar odometry, missed encoder edges under full load.
3. **Calibration not done:** `angular_scale` (step 6), the 2 m square (step 7), floors at low battery.
4. **Reverse rear matching** and closed-loop speed control (later).
5. **Stereo depth vs lidar** comparison (the cameras sit ~0.07 m ahead of the lidar: tape each sensor's distance
   separately).

The step-by-step task list lives in `claude/GOOSEBOT_TODO.md`.
