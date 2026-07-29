# 11_sim_nav2 — Nav2 in Isolation (Perfect-Map Navigation)

This container strips localization and mapping out of the picture so we can test
and tune Nav2's planning/control stack on its own. Instead of building a map
live with SLAM, the robot is given a **pre-made, ground-truth map** of the
Gazebo world, and its pose is read directly from Gazebo's simulated ground
truth rather than estimated from sensors.

[![Navigation Video Example](https://youtube.com)](https://www.youtube.com/watch?v=lLug-Tid4TY)

Three pieces had to be built to make a perfect map actually usable by Nav2:

1. **`sdf_to_map.py`** — bakes a Gazebo `.world` file into a standard ROS
   occupancy grid (`map.pgm` + `map.yaml`) that `map_server` can serve.
2. **`ground_truth_map_odom_bridge.py`** — publishes the `map → odom`
   transform Nav2 needs, sourced from Gazebo's ground-truth pose plugin
   instead of a SLAM pose estimate.
3. **An upgraded ToF sensor + local costmap `static_layer`** — the global
   costmap gets wall knowledge for free from the baked map, but the local
   costmap (used by the DWB controller for moment-to-moment obstacle
   avoidance) needs its own obstacle awareness. See "Known limitations"
   below — this area is still being tuned.


## Architecture

```
Gazebo (brick_area.world or maze_world.world)
  ├─ robot_state_publisher       → base_footprint → ... → sensor link TF (static)
  ├─ libgazebo_ros_diff_drive    → odom → base_footprint TF (dynamic) + /odom
  ├─ libgazebo_ros_p3d (ground truth) → /ground_truth/pose
  └─ tof_front sensor            → /tof_front/range

ground_truth_map_odom_bridge.py
  └─ /ground_truth/pose + /odom  → map → odom TF

map_server (loads maps/map.yaml)
  └─ publishes on /projected_map (remapped from default /map)

Nav2 (navigation_launch.py)
  ├─ global_costmap: static_layer (/projected_map) + inflation_layer
  ├─ local_costmap:  static_layer (/projected_map) + range_layer (ToF) + inflation_layer
  ├─ planner_server, controller_server, bt_navigator, behavior_server, ...
```

No `map_server`/AMCL from `nav2_bringup`'s default `bringup_launch.py` is
used — only `navigation_launch.py`, with `map_server` + its own lifecycle
manager started separately in `nav2_bringup.launch.py`. There is no SLAM node
running in this setup at all.

## Quickstart

All commands run **inside the container's browser desktop terminal**
(`http://localhost:6080` once the container is up — see `docker-compose.yml`).

```bash
# 1. Build (only needed after editing files)
cd ~/ros2_ws
colcon build --symlink-install

# 2. Launch Gazebo + spawn the robot (terminal 1)
source install/setup.bash
ros2 launch goosebot_0 spawn_robot.launch.py world:=/home/ubuntu/ros2_ws/src/brick_area.world

# 3. Launch Nav2 + map_server + the ground-truth bridge (terminal 2)
source install/setup.bash
ros2 launch goosebot_0 nav2_bringup.launch.py

# 4. Send a navigation goal (terminal 3), coordinates in the `map` frame
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 1.5, z: 0.0}, orientation: {w: 1.0}}}}" \
  --feedback
```

Drive manually instead with:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## Switching worlds / maps

Two worlds currently exist under `worlds/`: `brick_area.world` (open square
room) and `maze_world.world` (zigzag corridor). Each needs a matching baked
map — the map is **not** generated automatically at launch, it has to be
regenerated whenever the world changes.

```bash
# Regenerate the map for a given world (output prefix is required)
cd ~/ros2_ws/src/goosebot_0/scripts
python3 sdf_to_map.py ../worlds/maze_world.world ../maps/maze_map

# Spawn the robot in that world
ros2 launch goosebot_0 spawn_robot.launch.py \
  world:=$(ros2 pkg prefix goosebot_0)/share/goosebot_0/worlds/maze_world.world

# Point Nav2 at the matching map
ros2 launch goosebot_0 nav2_bringup.launch.py map:=/full/path/to/maze_map.yaml
```

`sdf_to_map.py` only rasterizes box and cylinder `<collision>` shapes; mesh
colliders are skipped with a printed warning, not baked in. Check the
script's console output after running it — it prints the shape count found,
which is a quick sanity check that nothing was silently missed.

## Upgrading navigation

These are the primary variables to upgrade the navigation algorithm in `nav2_params.yaml`:

```bash
      BaseObstacle.scale: 0.2
      PathAlign.scale: 32.0
      GoalAlign.scale: 24.0
      PathDist.scale: 32.0
      GoalDist.scale: 24.0
      RotateToGoal.scale: 16.0
```

The values given are the ones in the first version of the program.

## Known limitations / open issues

- **Local costmap obstacle awareness relies entirely on live sensing +
  the static map** - there's no SLAM-derived point cloud source in this
  setup (that's intentional, but worth remembering if `obstacle_layer` is
  ever re-added: it has no valid topic to subscribe to here).
- **Sustained `Behavior Tree tick rate 100.00 was exceeded!` warnings** have
  been observed during active navigation, alongside occasional
  `Control loop missed its desired rate of 10.0000Hz` - indicates the
  simulation is CPU-constrained on some machines/VMs. If navigation behaves
  erratically, check CPU load (`top`/`htop`) during a run before assuming a
  logic bug; consider running Gazebo headless (`gzserver` only) if this is
  consistently a bottleneck.
- **Navigating to a corner** - The robot struggles to navigate into a corner
  of the maze map. I believe this can be fixed by adjusting the BaseObstacle.scale
  attribute, but I have yet to fully fix it.

## Debugging checklist

If navigation is failing or behaving strangely, check in this order:

1. **`use_sim_time`** — every node needs it set `true` when running against
   Gazebo's `/clock`. A single node missing it (commonly
   `robot_state_publisher`, since it's launched separately from the rest of
   the stack) desyncs the TF tree and breaks costmap transforms.
   `ros2 param get <node> use_sim_time` to check.
2. **TF tree connectivity** — `ros2 run tf2_tools view_frames`, confirm
   `map → odom → base_footprint → ...` is one connected chain with no
   "unconnected trees" errors.
3. **Robot position vs. map bounds** — `Robot is out of bounds of the
   costmap!` means the robot's current `map`-frame position (check with
   `ros2 run tf2_ros tf2_echo map base_footprint`) is outside the baked
   map's extent (check with
   `ros2 topic echo /projected_map --field info --once`, bounds are
   `[origin_x, origin_x + width*resolution]` etc.). This is expected if the
   robot has driven outside the world's mapped area — not a bug.
4. **CPU load** during active navigation, per "Known limitations" above.
