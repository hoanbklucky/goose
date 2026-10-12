# goosebot sim — Nav2 / SLAM in Gazebo Harmonic (ROS 2 Jazzy)

A Docker-based simulation for Goosebot driving through a maze in Gazebo Harmonic, with Nav2 for navigation.
The first-time setup should take less than 20 minutes (depending on internet speed), and after that boots up in seconds. 
It supports two modes:

| Mode | Map comes from | `map → odom` comes from | Use it for |
|---|---|---|---|
| **Perfect map** (default) | A map baked from the Gazebo world file | Gazebo's ground-truth pose | Tuning Nav2 planning/control in isolation |
| **Stereo SLAM** (`slam:=true`) | RTAB-Map building a map live from the stereo cameras | RTAB-Map | Testing the whole perception → mapping → navigation chain |

Everything runs inside a container you use through your web browser. Nothing ROS-related needs to be
installed on your own machine.

---

## 1. Project layout

```
.
├── Dockerfile              # ROS 2 Jazzy desktop-in-browser image + Nav2/Gazebo packages
├── docker-compose.yml      # how the container is started (ports, mounted folders, GPU option)
└── ros2_ws/                # the ROS 2 workspace, mounted into the container as ~/ros2_ws
    ├── commands.txt        # copy-paste commands for everything below
    ├── configwimu.rviz     # RViz layout (costmaps, plans, camera, IMU, ToF scan)
    ├── src/goosebot_0/     # the one ROS package (details in section 5)
    ├── build/ install/ log/   # colcon output (auto-generated; safe to delete and rebuild)
```

---

## 2. Docker setup

### 2.1 Requirements
- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (recommended). It is available for Windows, macOS and
  Linux and already includes Docker Compose, so nothing else needs to be installed. Any other Docker-compatible setup that
  can run Compose files also works, for example Docker Engine with the Compose plugin on Linux, Podman with `podman-compose`,
  Rancher Desktop, or Colima.
- **Disk space:** the base image is about 2.8 GB to download ([Docker Hub](https://hub.docker.com/r/tiryoh/ros2-desktop-vnc/tags)),
  and it takes more once extracted and with the added Nav2, Gazebo and RTAB-Map packages. Keep roughly 10 GB free to be safe
  (an estimate). After the build, `docker images nav-sim:jazzy` shows the actual size.
- **Memory/CPU:** a few GB of RAM; Gazebo plus Nav2 is CPU-hungry.
- *(Optional)* an NVIDIA GPU plus the NVIDIA Container Toolkit, only for the `gpu` profile.

### 2.2 Start and stop the container

From the folder containing `docker-compose.yml`:

```bash
docker compose up -d --build          # CPU/software rendering (default)
# or, with an NVIDIA GPU:
docker compose --profile gpu up -d --build nav-sim-gpu
```

Then open **http://localhost:6080** in a browser. You get a Linux desktop; open a terminal in it
(that is where every command in this README is run). Both services use port 6080, so run only one at a time.

| Command | Effect |
|---|---|
| `docker compose up -d` | Creates the container if needed and starts it. If it already exists and nothing changed, it is simply started. This is all you need day to day. |
| `docker compose up -d --build` | Same, but rebuilds the image first. **Required after editing the `Dockerfile`**, because `up` alone reuses the existing image. |
| `docker compose stop` / `start` | Stops / resumes the existing container without recreating it (the same as the stop/play buttons in Docker Desktop). |
| `docker compose down` | Stops and removes the container. Your `ros2_ws` folder is untouched. |

The compose file sets `restart: unless-stopped`, so the container comes back automatically when Docker restarts unless you stopped it manually.

### 2.3 What the compose file does
- `build: .` builds the `Dockerfile` into the image `nav-sim:jazzy`.
- `./ros2_ws` on your computer is mounted at `/home/ubuntu/ros2_ws` in the container. Files are shared, so you can
  edit them from either side. Build output (`build/`, `install/`) also lands on your computer, so recreating the
  container does not require rebuilding the package.
- `seccomp:unconfined` and `shm_size: 512m` are needed for the browser desktop and Gazebo's rendering.
- The `gpu` profile is identical but reserves one NVIDIA GPU.

### 2.4 What the image contains
The Dockerfile starts from Tiryoh's `ros2-desktop-vnc:jazzy` image (ROS 2 Jazzy, RViz, and a desktop served over
noVNC) and adds:

- **Navigation / localization:** `navigation2`, `nav2-bringup`, `nav2-map-server`, `nav2-lifecycle-manager`, `robot-localization`
- **Simulation:** `ros-gz` (Gazebo Harmonic + ROS bridge), `xacro`
- **SLAM:** `rtabmap-ros` (stereo SLAM mode)
- **Tools:** `teleop-twist-keyboard`, `imu-tools` (RViz Imu display), `python3-lxml` / `python3-pil` / `python3-numpy` (map baking script)
- Also installed but not used by `goosebot_0`: `slam-toolbox`, `gz-ros2-control`, `turtlebot3*`

After changing the Dockerfile, rebuild with `docker compose up -d --build`.

---

## 3. Using the simulation

Open **a separate terminal for each numbered step** in the browser desktop. All of these are also in
`ros2_ws/commands.txt`.

### 3.0 Build (first time, and after adding new files)
```bash
cd ~/ros2_ws
colcon build --symlink-install
```
With
`--symlink-install`, edits to existing YAML/xacro/launch/Python files take effect immediately without rebuilding.
You only need to rebuild when you **add** new files or change `CMakeLists.txt`. If the build ever acts strangely:
`rm -rf build install log` and build again.

In every new terminal, source the workspace first:
```bash
cd ~/ros2_ws && source install/setup.bash
```

### 3.1 Mode A — Perfect map (default)

Open a terminal in the browser desktop for each numbered step below. (Run `cd ~/ros2_ws && source install/setup.bash` first in each.)

```bash
# Terminal 1: Gazebo + robot
# Wait until the robot appears in the maze. The default spawn point (0, 0) may land in a wall, hence x:=-0.5.
# You can also set y:=, z:= and yaw:= (radians).
ros2 launch goosebot_0 spawn_robot.launch.py \
  world:=$(ros2 pkg prefix goosebot_0)/share/goosebot_0/worlds/maze.world x:=-0.5

# Terminal 2: Nav2 with the baked ground-truth map
ros2 launch goosebot_0 nav2_bringup.launch.py \
  map:=/home/ubuntu/ros2_ws/src/goosebot_0/maps/maze.yaml

# Terminal 3: RViz
ros2 run rviz2 rviz2 -d ~/ros2_ws/configwimu.rviz

# Terminal 4: send a goal (map frame, metres). Heading is effectively ignored (yaw_goal_tolerance is 6.28),
# but orientation w must be non-zero for a valid quaternion.
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: -4.5, z: 0.0}, orientation: {w: 1.0}}}}" --feedback

# Alternative to Terminal 4: click "2D Goal Pose" in RViz, or publish a one-off goal
ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: map}, pose: {position: {x: 1.0, y: 0.0}, orientation: {w: 1.0}}}"
```

To drive the robot yourself instead of using Nav2, see [3.3 Manual control](#33-manual-control).

### 3.2 Mode B — Live stereo SLAM

Do not run Mode A's Nav2 at the same time; both would publish `map → odom`.
Before sending goals, explore with manual control first (see [3.3](#33-manual-control)).

```bash
# Terminal 1: Gazebo + robot (same as Mode A)
ros2 launch goosebot_0 spawn_robot.launch.py \
  world:=$(ros2 pkg prefix goosebot_0)/share/goosebot_0/worlds/maze.world x:=-0.5

# Terminal 2: RTAB-Map stereo SLAM (passing rtabmap_args replaces the launch file's defaults)
ros2 launch goosebot_0 stereo_slam.launch.py rtabmap_viz:=false \
  rtabmap_args:="--delete_db_on_start --Grid/RangeMax 2.0 --Grid/RayTracing true --Reg/Force3DoF true --Rtabmap/DetectionRate 2 --RGBD/LinearUpdate 0 --RGBD/AngularUpdate 0"

# Terminal 3: Nav2 on top of the SLAM map
ros2 launch goosebot_0 nav2_bringup.launch.py slam:=true

# Terminal 4: RViz
ros2 run rviz2 rviz2 -d ~/ros2_ws/configwimu.rviz

# Terminal 5: manual control to explore and build the map (see 3.3)
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Terminal 6: send a goal once enough of the map exists
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: -4.5, z: 0.0}, orientation: {w: 1.0}}}}" --feedback
```

### 3.3 Manual control

> **Important in Mode B:** drive the robot around with the keyboard *before* sending Nav2 goals, so SLAM has built a map
> of the areas the robot needs to plan through. Goals into unexplored space will fail or behave poorly.

```bash
# Drive with the keyboard (focus this terminal and follow the on-screen key list)
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Check that the SLAM map exists and see its size/origin
ros2 topic echo /rtabmap/map --once --field info
```

### 3.4 Handy diagnostics
```bash
ros2 run tf2_tools view_frames                 # TF tree -> frames.pdf
ros2 topic list                                # what's being published
python3 ~/ros2_ws/src/goosebot_0/scripts/check_heading.py        # compare heading: truth vs EKF vs SLAM
python3 ~/ros2_ws/src/goosebot_0/scripts/check_stereo_depth.py   # compare stereo depth vs the ToF (robot stationary, facing a wall)
```

### 3.5 Troubleshooting
- **`Behavior Tree tick rate ... exceeded` / `Control loop missed its desired rate`**: the machine is CPU-bound. Close
  other apps, use the GPU profile, or run Gazebo without its GUI.
- **Robot spawns inside a wall / is stuck**: change `x:=`/`y:=`/`yaw:=` on the spawn command.
- **Nav2 doesn't move / "timeout waiting for transform"**: Gazebo must be running first (it provides `/clock`), and
  exactly one `map → odom` source must be active (ground-truth bridge *or* RTAB-Map).
- **Robot drifts away from where RViz thinks it is**: in Mode A the ground-truth bridge corrects this, so it
  usually means that node isn't running (check the Nav2 terminal output).

---

## 4. How it works

```
Gazebo (maze.world + robot)
 ├─ DiffDrive plugin ......... moves the wheels from /cmd_vel
 ├─ IMU, ToF, stereo cams, GPS  ──► ros_gz_bridge ──► ROS topics
 └─ OdometryPublisher ........ /ground_truth/pose (perfect pose, sim only)

/cmd_vel ─► cmd_vel_to_odom.py ─► /odom_cmdvel ─┐
IMU (yaw rate) ────────────────────────────────┴─► EKF ─► /odometry/filtered + TF odom→base_footprint

Mode A:  map_server (baked map → /projected_map)
         ground_truth_map_odom_bridge.py ─► TF map→odom
Mode B:  RTAB-Map (stereo) ─► /rtabmap/map + TF map→odom

Nav2: global costmap + local costmap + planner (Navfn) + controller (DWB) + BT navigator
      → /cmd_vel_nav → velocity_smoother → collision_monitor → /cmd_vel
```
Notes:
- The robot has **no wheel encoders** (matching the real hardware). Odometry is dead-reckoned from the commanded
  velocity and corrected only by the gyro, so it drifts. That is why Mode A needs the ground-truth bridge.
- Nav2 here uses `navigation_launch.py` only (no AMCL).
- The ToF is a **single beam** straight ahead, so it only sees a thin line in front of the robot.

---

## 5. What's inside `src/goosebot_0/`

### 5.1 Top level
| File | Purpose |
|---|---|
| `package.xml` | Package metadata and dependencies. |
| `CMakeLists.txt` | Installs `urdf/ launch/ config/ maps/ worlds/` and three scripts into the package. **Any new script you want to `ros2 run`/launch must be added to its `install(PROGRAMS ...)` list.** |
| `goosebot-simulation.zip` | A packaged copy of the package for sharing. A snapshot only; nothing uses it and it may be out of date. |

### 5.2 `launch/`
| File | What it starts |
|---|---|
| `spawn_robot.launch.py` | Gazebo with the chosen world, `robot_state_publisher` (robot model from the xacro), the robot spawner, the `ros_gz_bridge`, `cmd_vel_to_odom.py`, and the EKF. Args: `world`, `x`, `y`, `z`, `yaw`, `entity_name`, `use_sim_time`. |
| `nav2_bringup.launch.py` | Nav2's navigation stack with this package's `nav2_params.yaml`. Args: `map` (map yaml path, default `maps/map.yaml`), `params_file`, `use_sim_time`, `slam`. With `slam:=false` it also starts `map_server` (remapped to `/projected_map`) and the ground-truth bridge. With `slam:=true` it skips them and points the costmaps at `/rtabmap/map`. |
| `stereo_slam.launch.py` | The camera-info fixer plus RTAB-Map in stereo mode, using the EKF for odometry (RTAB-Map's own visual odometry is off). Args: `baseline`, `rtabmap_viz`, `rviz`, `rtabmap_args`, `approx_sync`. Passing `rtabmap_args` **replaces** the defaults rather than adding to them. |

### 5.3 `urdf/`
| File | What it defines |
|---|---|
| `robot.urdf.xacro` | The robot: a 0.18 × 0.14 × 0.06 m body and four 3 cm-radius wheels, plus a stereo camera pair (9 cm baseline, 640×480, 90° FOV, 20 Hz), IMU (100 Hz), front single-beam ToF (a 1-beam `gpu_lidar`, range 0.04–8 m) and GPS (5 Hz). Gazebo plugins: `DiffDrive` (skid-steer, listens on `cmd_vel`) and `OdometryPublisher` (ground truth on `ground_truth/pose`). Dimensions and camera settings are `xacro:property` values at the top of the file. |

### 5.4 `config/`
| File | What it does |
|---|---|
| `ros_gz_bridge.yaml` | Which topics cross between Gazebo and ROS: `clock`, `cmd_vel`, `joint_states`, `ground_truth/pose`, `imu/data`, stereo images + raw camera info, `tof_front/scan`, `gps/fix`. The names must match the `<topic>` tags in the xacro. |
| `ekf.yaml` | `robot_localization` EKF at 30 Hz. Fuses x/y velocity from `/odom_cmdvel` and yaw rate from the IMU. Publishes `/odometry/filtered` and the `odom → base_footprint` TF. |
| `nav2_params.yaml` | All Nav2 settings: DWB controller (max 0.30 m/s), Navfn planner, global (20 m rolling window) and local (1 m window) costmaps with static, ToF obstacle and inflation layers, behaviors, velocity smoother, collision monitor. |

### 5.5 `maps/`
| File | What it is |
|---|---|
| `maze.yaml` / `maze.pgm` | 13 × 13 m occupancy-grid map (0.05 m/pixel) baked from `worlds/maze.world`. The `.yaml` holds the resolution and origin; the `.pgm` is the image. |
| `map.yaml` / `map.pgm` | Near-identical copy of the maze map. It is the default for `nav2_bringup.launch.py` when no `map:=` is given. |

### 5.6 `worlds/`
| File | What it is |
|---|---|
| `maze.world` | The Gazebo world: a ~10 × 10 m maze built from box walls, with the ground plane, sun and the sensor/physics plugins. |
| `textures/` | Wall images used by the maze. The stereo cameras need textured walls to find visual features. |

### 5.7 `scripts/`
| Script | Role |
|---|---|
| `cmd_vel_to_odom.py` | Integrates `/cmd_vel` into dead-reckoning odometry on `/odom_cmdvel` (no TF by default). Started by `spawn_robot.launch.py`. |
| `ground_truth_map_odom_bridge.py` | Computes `map → odom` from the ground-truth pose and the EKF's `odom → base` so Nav2 has perfect localization in Mode A. Sim only. |
| `stereo_camera_info_fixer.py` | Gazebo's camera info lacks the stereo baseline term; this republishes it correctly. Used by SLAM mode. |
| `sdf_to_map.py` | Bakes a `.world` file into an occupancy-grid map (see section 7). |
| `check_heading.py` | Debug tool: compares total rotation from ground truth, the EKF, and the map-frame pose. |
| `check_stereo_depth.py` | Debug tool: compares RTAB-Map's stereo distance with the ToF reading. |

---

## 6. Useful commands to copy/paste in the Docker, in `commands.txt`

The browser desktop at `localhost:6080` does not share your computer's clipboard, so you can't paste commands into it from outside.
`ros2_ws/commands.txt` exists for that reason: it holds the commands that get used often. Because `ros2_ws` is mounted into the container,
you can edit `commands.txt` on your computer, save it, and reopen it inside the Docker desktop to copy commands from there into a terminal.


| Command | What it does |
|---|---|
| `colcon build --symlink-install` | Compiles/installs the package; symlinks mean config edits apply without rebuilding. |
| `source install/setup.bash` | Makes this workspace's packages visible in the current terminal (needed in every new terminal). |
| `ros2 launch goosebot_0 spawn_robot.launch.py world:=… x:=-0.5` | Starts Gazebo with the maze and puts the robot at x = −0.5 m, plus the bridge, odometry and EKF. |
| `ros2 launch goosebot_0 stereo_slam.launch.py rtabmap_viz:=false rtabmap_args:="…"` | Starts stereo SLAM without the RTAB-Map GUI. The args: fresh map each run (`--delete_db_on_start`), use depth only up to 2 m (`Grid/RangeMax`), ray-trace to clear stray obstacles, assume a planar robot (`Reg/Force3DoF`), process at 2 Hz, and add nodes on every update (`RGBD/LinearUpdate 0`, `RGBD/AngularUpdate 0`). *(There's a stray `\` before `rtabmap_args` in the file; the shell happens to accept it, but you can delete it.)* |
| `ros2 launch goosebot_0 nav2_bringup.launch.py slam:=true` | Nav2 using the live RTAB-Map map. |
| `… nav2_bringup.launch.py map:=…/maze.yaml` | Nav2 using the baked perfect map. |
| `ros2 run rviz2 rviz2 -d ~/ros2_ws/configwimu.rviz` | Opens RViz with the saved layout. |
| `ros2 action send_goal /navigate_to_pose …` | Asks Nav2 to drive to (x, y) in the map frame and prints feedback. |
| `ros2 run teleop_twist_keyboard teleop_twist_keyboard` | Drive with the keyboard. |
| `ros2 topic echo /rtabmap/map --once --field info` | Prints the SLAM map's size/origin to confirm it exists. |
| `ros2 topic pub --once /goal_pose …` | Sends a goal to (1, 0) in the map frame without using the action client. |

---

## 7. How to modify it

Remember: with `--symlink-install`, editing existing files needs only a **restart of the launch** (Ctrl-C and rerun), not a rebuild. New files need `colcon build --symlink-install`.

### Tune navigation → `config/nav2_params.yaml`
| Goal | Edit |
|---|---|
| Max speed | `controller_server → FollowPath → max_vel_x` / `max_speed_xy`, **and** `velocity_smoother → max_velocity`; also `collision_monitor`'s `time_before_collision` scales with speed |
| Turning speed | `max_vel_theta`, velocity smoother's third `max_velocity` value |
| Keep farther from walls | `inflation_layer → inflation_radius` (and `cost_scaling_factor`) in the global and local costmaps |
| Goal strictness | `goal_checker → xy_goal_tolerance`, `yaw_goal_tolerance` |
| Path vs. goal preference | DWB critic `scale` values (`PathDist`, `GoalDist`, `PathAlign`, …) |
| Different planner | `planner_server → planner_plugins` (e.g. Smac) |
| Local costmap size | `local_costmap → width/height` — if you enlarge it, raise the ToF `obstacle_max_range` too |
| Robot size | `footprint` in **both** costmaps (and the collision monitor uses the local one) |

Full parameter reference: https://docs.nav2.org/configuration/index.html

### Change or add a world / map
1. Put your SDF file in `worlds/` (e.g. `myworld.world`). Copy the plugin block from `maze.world`; without the Sensors/IMU/NavSat plugins, sensors won't publish.
2. Bake a matching map:
   ```bash
   cd ~/ros2_ws/src/goosebot_0/scripts
   python3 sdf_to_map.py ../worlds/myworld.world ../maps/myworld
   ```
   It prints how many shapes were rasterized. Only `box` and `cylinder` collisions are rasterized; meshes are skipped with a warning. Models whose name contains `ground_plane`, `sun`, `robot` or `goosebot` are ignored.
3. Rebuild (`colcon build --symlink-install`) so the new files get installed, then launch with `world:=…/myworld.world` and `map:=…/maps/myworld.yaml`.

### Change the robot → `urdf/robot.urdf.xacro`
- Body, wheel and camera dimensions are `xacro:property` values at the top.
- If you change `stereo_baseline`, also change the `baseline` argument in `stereo_slam.launch.py` (they must match).
- If you change the footprint, update the `footprint` in `nav2_params.yaml`.
- If you change wheel size/spacing, DiffDrive reads them from the same properties, so it follows automatically.

### Add or change a sensor
1. Add the link/joint and a `<sensor>` with a `<topic>` in the xacro.
2. Add a matching entry in `config/ros_gz_bridge.yaml` (same topic name, correct ROS and Gazebo message types).
3. Consume it (e.g. add an `observation_sources` entry in a costmap layer, or add it to `ekf.yaml`).

### Change localization
- `config/ekf.yaml` selects which values are fused (the boolean arrays are in the order x, y, z, roll, pitch, yaw, vx, vy, vz, vroll, vpitch, vyaw, ax, ay, az). Absolute IMU yaw is intentionally **not** fused because Gazebo's IMU orientation has zero noise, which made the filter over-trust it.
- Never have two publishers of the same transform (`odom → base_footprint` is the EKF's; `map → odom` is either the ground-truth bridge or RTAB-Map).
- This package's localization is sim-only; for real hardware you'd replace the ground-truth bridge with something like AMCL or SLAM, and `use_sim_time:=false` alone does not make the launch files hardware-ready.

### Change the spawn point or SLAM tuning
- Spawn: `x:= y:= yaw:=` on `spawn_robot.launch.py`.
- SLAM: pass `rtabmap_args:="…"`, or edit the defaults in `stereo_slam.launch.py` (all RTAB-Map parameters: https://github.com/introlab/rtabmap/wiki).

### Add a new script
Put it in `scripts/`, `chmod +x` it, add it to `install(PROGRAMS …)` in `CMakeLists.txt`, rebuild, and run it with `ros2 run goosebot_0 <name>.py` (or add a `Node(...)` to a launch file).
