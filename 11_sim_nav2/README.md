# 11_sim_nav2 — Nav2 in Isolation (Perfect-Map Navigation)

This container strips localization and mapping out of the picture so we can test
and tune Nav2's planning/control stack on its own. Instead of building a map
live with SLAM, the robot is given a **pre-made, ground-truth map** of the
Gazebo world, and its pose is read directly from Gazebo's simulated ground
truth rather than estimated from sensors.

![Navigation Video Example](goose/11_sim_nav2/goosebot_nav_9-3-26.gif)

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
These are all listed inside ~/ros2_ws/commands.txt for easy copy-pasting

```bash
# 1. Build the package (only after editing files)
cd ~/ros2_ws
colcon build --symlink-install

# 2. Launch Gazebo
cd ~/ros2_ws
source install/setup.bash
ros2 launch goosebot_0 spawn_robot.launch.py world:=$(ros2 pkg prefix goosebot_0)/share/goosebot_0/worlds/maze.world


# 3. Run the navigation script (second terminal)
cd ~/ros2_ws
source install/setup.bash
ros2 launch goosebot_0 nav2_bringup.launch.py map:=/home/ubuntu/ros2_ws/src/goosebot_0/maps/maze.yaml

# 4. Open RViz for visualization of the navigation algorithm (third terminal)
ros2 run rviz2 rviz2 -d ~/ros2_ws/default_config.rviz


# 5. Send a target for the robot to navigate to (fourth terminal)
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: -4.5, z: 0.0}}}}" --feedback

```

Drive manually instead with:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## Switching worlds / maps

Worlds for this exist in `worlds/`, for instance `worlds/maze.world`, `worlds/barely_maze.world`, and `worlds/brick_area.world`.
The brick area is used for camera depth detection, while the two mazes are used to test navigation scripts.
Each world needs a matching map in the `maps/` directory, which is what feeds into the navigation script in place of sensor data.

```bash
# Regenerate the map for a given world (output prefix is required)
cd ~/ros2_ws/src/goosebot_0/scripts
python3 sdf_to_map.py ../worlds/[world_name].world ../maps/[map_name]

# Spawn the robot in that world
ros2 launch goosebot_0 spawn_robot.launch.py \
  world:=$(ros2 pkg prefix goosebot_0)/share/goosebot_0/worlds/[world_name].world

# Point Nav2 at the matching map
ros2 launch goosebot_0 nav2_bringup.launch.py map:=/home/ubuntu/ros2_ws/src/goosebot_0/maps/[map_name].yaml
```

`sdf_to_map.py` only rasterizes box and cylinder `<collision>` shapes; mesh
colliders are skipped with a printed warning. Check the
script's console output after running it- it prints the shape count found.

## Upgrading navigation

Basically everything in `nav2_params.yaml` can be tuned to upgrade/change the navigation algorithm.
Documentation can be found here: https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/

## Known limitations / open issues

- **Sustained `Behavior Tree tick rate 100.00 was exceeded!` warnings** have
  been observed during active navigation, alongside occasional
  `Control loop missed its desired rate of 10.0000Hz` - indicates the
  simulation is CPU-constrained on some machines/VMs. If navigation behaves
  erratically, check CPU load (`top`/`htop`) during a run before assuming a
  logic bug; consider running Gazebo headless (`gzserver` only) later if this is
  consistently a bottleneck.
