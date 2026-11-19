# Goosebot: what is left to do (status 2026-11-19)

Lidar, encoders and the 32 Hz motor calibration were done on 2026-11-19. Remaining steps are below, in order. The
detailed command sheets for steps 1-6 are in the chat of 2026-11-19 and in `README_lidar_encoders.md` (Parts 6-7).

## Done 2026-11-19 (measured values)

| Item | Result |
|---|---|
| sllidar_ros2 driver | built; `/dev/rplidar` udev link; C1 healthy, scan mode Standard, 10 Hz |
| Lidar mount (URDF) | x +0.030 m, y 0, scan plane 0.182 m above floor, yaw 180 deg (`${pi}`); no self-hits |
| Encoder wiring | FL A pin 16 / B pin 18 (was wrongly on 10/12, the debug UART), FR A 22 / B 26 |
| `encoder_params.yaml` | `counts_per_rev: 1090`, `fl_sign: -1`, `fr_sign: 1`, `linear_scale: 0.98`, `vx_var: 0.002` (tape vs encoder within 1-2 %) |
| Motor wiring | `rl: [4, 5]` (was `[5, 4]`, RL ran backwards in every earlier ROS session) |
| `hw_params.yaml` motor_driver | `pwm_frequency: 32` (was missing: driver ran at 100 Hz), `max_duty: 0.33`, `kick_duty: 0.30`, `kick_time: 0.04`, `min_duty_spin: 0.24`, `w_floor: 0.545` |
| Rear wheel matching | rears ~1.46x faster than fronts per duty; driver maps rear duty from `wheel_cal_*` (lifted, forward) |
| Speed table | 13 points 0.10-0.33 duty -> 0.073-0.352 m/s on the floor at 11.73 V; commanded vs real now within ~5 % forward, ~10 % reverse |
| Nav2 limits | recovery spin max 1.0 rad/s; odom-only spin 0.6-1.0 rad/s; other limits unchanged (max_vel_x 0.2, max_vel_theta 1.0) |
| New scripts | `encoder_check.py`, `scan_check.py`, `floor_calib.py`, `drive_test.py` (rewritten: background spin thread, encoder distance) |

## Left to do

1. **Leftward drift (open).** Robot yaws ~+5.5-6.7 deg per 1 m forward. A right-side speed trim (`speed_trim_right`
   0.98 -> 0.85) did not change it, although the log confirms it is applied. Set `speed_trim_right: 1.0`, then:
   watch whether it twists at the start or curves steadily; compare `drive_test.py lin 0.15 6.67` (1 m) with
   `lin 0.15 13.33` (2 m); during the 2 m run watch `ros2 topic echo /imu/data --field angular_velocity.z`.
   2 m yaw ~double + steady gyro rate = steady drift (fix: rear matching per side). Same yaw + spikes at start/stop =
   kick transient (fix: kick settings). Not blocking for Nav2/mapping (gyro + EKF track heading).
2. **Turn check -> `angular_scale`.** Tape strip along the robot's side; `drive_test.py ang 0.8 7.854` (360 CCW) and
   `ang -0.8 7.854` (CW), 3 each; record the real angle and the gyro angle. New `angular_scale` = 0.78 x (mean real / 360).
   Flag if the gyro differs from the real angle by more than ~3 %.
3. **2 m square (EKF check).** Restart bringup (EKF at 0,0,0), tape the start pose, then
   `for i in 1 2 3 4; do python3 drive_test.py lin 0.15 13.33; python3 drive_test.py ang 0.8 1.963; done`.
   Compare the last `EKF end pose` with the real end position/heading (good: within ~10 cm and 5 deg after 8 m).
   Optional: repeat with `hw_bringup ... lidar_odom:=true`.
4. **Laptop setup.** ROS 2 Jazzy, same `ROS_DOMAIN_ID=0` and `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`, same Wi-Fi (not the
   VPN). Check with `ros2 daemon stop && ros2 topic list --no-daemon`.
5. **First lidar map with Nav2.** On the robot: `ros2 run rtabmap_slam rtabmap --params | grep Grid/Sensor` (must print
   something), then `ros2 launch goosebot_hw hw_robot.launch.py write:=lab_lidar with_nav2:=true`. On the laptop: RViz
   (fixed frame `map`; `/rtabmap/map` Transient Local, `/scan` Best Effort, costmaps, `/plan`, RobotModel), send goals
   with 2D Goal Pose; `rqt_image_view` on `/stereo/left/image_rect` (may lag over Wi-Fi; ask for a compressed stream if
   so); teleop backup on `/cmd_vel_teleop`. Use Nav2 goals when the robot is out of sight: teleop bypasses the
   collision monitor. Lidar does not see anything below ~0.18 m.
6. **Navigate on the map.** `read:=lab_lidar` (RTAB-Map localizing) and `read:=lab_lidar rtab:=false` (AMCL).
7. **Load check.** During a full-stack run (cameras + RTAB-Map + Nav2): watch for `missed edges` from encoder_node,
   `free -m`, `dmesg | grep -i oom`.
8. **Floors at low battery.** Re-run `floor_calib.py straight` at ~11.0 V; raise the first speed-table duty if the floor
   moved up (measured at 11.73 V: moves down to 0.09, table starts at 0.10).
9. **Later / optional:** reverse rear-matching data (rears timed with `--dir rev`), closed-loop speed control from the
   front encoders, depth check stereo vs lidar (tape each sensor separately: cameras are ~0.07 m ahead of the lidar),
   README: paste Parts 6-7 and the listed edits from `README_lidar_encoders.md`, retire `lidar_ref.launch.py`.
