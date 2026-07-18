# 12_slam - Monocular ORB-SLAM3 Setup

Full working setup for running monocular ORB-SLAM3 via ROS 2, including camera calibration, SLAM pipeline, TF integration, and octomap based occupancy maping

## 1. Dependencies
It is important to build in the following order, as each layer depends on the previous one:

```
Ubuntu 22.04 Desktop (ARM64)
 └── ROS 2 Humble
 └── OpenCV 4.6 + Pangolin 0.6 + Sophus 1.22.10
 └── ORB-SLAM3
 └── orbslam3_ros2 (this repo, in 12_slam/)
```

It is assumed that you already have Ubuntu and ROS 2 Humble running.

To prevent running out of memory during compilation, set up a swap file:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
### 1.1 Install Apt Dependencies
Paste the following into the terminal:

```bash
sudo apt install -y \
    libglew-dev libboost-all-dev libssl-dev \
    libeigen3-dev libgtk2.0-dev pkg-config \
    libavcodec-dev libavformat-dev libswscale-dev \
    libjpeg-dev libpng-dev libtiff-dev \
    libepoxy-dev python3-wheel \
    libgl1-mesa-dev libgles2-mesa-dev \
    git cmake build-essential
```
These ROS 2 packages this project depends on, but are not part of a base ROS 2 install.

```bash
sudo apt install -y \
  ros-humble-cv-bridge \
  ros-humble-image-transport \
  ros-humble-camera-info-manager \
  ros-humble-v4l2-camera \
  ros-humble-octomap-server \
  ros-humble-octomap-msgs \
  ros-humble-camera-calibration
```

### 1.2 Build OpenCV 4.6.0
OpenCV is a general-purpose computer vision library. ORB-SLAM3 uses it for all its low-level image processing, such as reading camera frames, detecting features, etc.

OpenCV has to be built from source, this is because the apt version conflicts with ROS 2's bundled OpenCV.

```bash
mkdir -p ~/Dev && cd ~/Dev
git clone https://github.com/opencv/opencv.git
cd opencv && git checkout 4.6.0
mkdir build && cd build
cmake -D CMAKE_BUILD_TYPE=Release \
      -D WITH_CUDA=OFF \
      -D WITH_FFMPEG=OFF \
      -D CMAKE_INSTALL_PREFIX=/usr/local ..
make
sudo make install
```

### 1.3 Build Pangolin v0.6
Pangolin is a lightweight 3D visualization library. ORB-SLAM3 uses it to render its live viewer window and display tracked feature points on the camera feed alongside the growing 3D point cloud/map.

v0.6 is the last version compatible with ORB-SLAM3, newer versions are incompatible with ORB-SLAM3.

```bash
cd ~/Dev
git clone https://github.com/stevenlovegrove/Pangolin.git
cd Pangolin
git checkout v0.6
mkdir build && cd build
cmake .. -D CMAKE_BUILD_TYPE=Release \
         -D BUILD_PANGOLIN_PYTHON=OFF \
         -D BUILD_TOOLS=OFF \
         -D BUILD_EXAMPLES=OFF
make
sudo make install
```
### 1.4 Build Sophus v1.22.10
Sophus is a math library implementing Lie groups, which are the mathematical objects used to represent 3D rotations and rigid-body poses. ORB-SLAM3 uses this internally for essentially all of its pose and transform calculations. 

Newer Sophus versions require CMake 3.24, but Ubuntu 22.04 ships with CMake 3.22.

```bash
cd ~/Dev
git clone https://github.com/strasdat/Sophus.git
cd Sophus
git checkout 1.22.10
mkdir build && cd build
cmake .. -D CMAKE_BUILD_TYPE=Release
make
sudo make install
```

## 2. ORB-SLAM3
ORB-SLAM3 is the core SLAM (Simultaneous Localization and Mapping) library this project is built around. It takes a stream of camera images and simultaneously figures out where the camera is moving through space, and a 3D map of the surrounding environment. Using only visual features, with no depth sensor required for this monocular configuration.

```bash
cd ~/Dev
git clone https://github.com/UZ-SLAMLab/ORB_SLAM3.git
cd ORB_SLAM3
 
# Fix: ORB-SLAM3 declares C++11 but requires C++14
sed -i 's/++11/++14/g' CMakeLists.txt

export MAKEFLAGS="-j1"   # prevents parallelism to avoid exhausting the RAM — the 4GB swap set up earlier also helps here
chmod +x build.sh
./build.sh
```
After building, extract the vocabulary file and verify that the library was built:
 
```bash
cd ~/Dev/ORB_SLAM3/Vocabulary
tar -xf ORBvoc.txt.tar.gz
ls ~/Dev/ORB_SLAM3/lib/libORB_SLAM3.so
```
The vocabulary file is a pre-trained "bag of visual words" dictionary used by ORB-SLAM3 to recognize places it has seen before. It is a large plain-text file, which is why it ships compressed and needs to be extracted.
ORBvoc.txt must be the full ~139MB extracted text file. If a later step reports "This is not a correct text file!", this file didn't extract correctly. Re-run the tar -xf step and verify with the command above

Add the built library paths to `~/.bashrc` (needed at runtime, not just build time):
```bash
echo 'export LD_LIBRARY_PATH=~/Dev/ORB_SLAM3/lib:~/Dev/ORB_SLAM3/Thirdparty/g2o/lib:~/Dev/ORB_SLAM3/Thirdparty/DBoW2/lib:/usr/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

## 3. ORB-SLAM3 ROS 2 Wrapper + TF Bridge
ORB-SLAM3 by itself is just a C++ library,that is, it does not interact with ROS 2 by its own. This wrapper connects the two, it subscribes to a ROS 2 camera image topic, feeds each frame into ORB-SLAM3, and republishes the results (pose, point cloud) as ROS 2 topics other nodes can use. This repo's version is a modified fork with several fixes (see Troubleshooting) and an added TF bridge node, which publishes SLAM's pose into ROS 2's transform (TF) tree and is required for octomap and navigation.

Clone the monorepo and set up a symlink so colcon builds directly from this subfolder
```bash
mkdir -p ~/colcon_ws/src
cd ~/colcon_ws/src
git clone -b slam https://github.com/hoanbklucky/goose.git goose
ln -s ~/colcon_ws/src/goose/12_slam ~/colcon_ws/src/orbslam3_ros2
```
 
Before building, confirm two paths in `CMakeLists.txt` match your actual install locations (they should already be correct if you followed this guide exactly, but double-check if your home directory or username differs):
```cmake
set(ORB_SLAM3_DIR "/home/<your-username>/Dev/ORB_SLAM3")
set(PANGOLIN_LIB_DIR "/usr/local/lib/libpangolin.so")
```

Copy the vocabulary file into the package's config directory — **this step is easy to miss and required**, since the wrapper looks for it here at runtime, not in `~/Dev/ORB_SLAM3/`:
```bash
cp ~/Dev/ORB_SLAM3/Vocabulary/ORBvoc.txt ~/colcon_ws/src/orbslam3_ros2/config/ORBvoc.txt
```

Now build the wrapper and source the workspace

```bash
cd ~/colcon_ws
export MAKEFLAGS="-j1"
colcon build --packages-select orbslam3_ros2 --cmake-args -DCMAKE_BUILD_TYPE=Release
echo "source ~/colcon_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```
Verify the executables exist:
 
```bash
ls ~/colcon_ws/install/orbslam3_ros2/lib/orbslam3_ros2/
# Should show: mono  rgbd  stereo
```

 ## 4. Camera Calibration
 Every camera lens causes some geometric distortion. Calibration measures this distortion and the camera's focal lenght/optical center, so ORB-SLAM3 can correct for it. Otherwise, tracking will be inaccurate or fail to initialize.
 
Plug in the USB webcam and verify it is detected:
 
```bash
ls /dev/video*
# Should show /dev/video0
```
Print a calibration checkerboard from https://calib.io/pages/camera-calibration-pattern-generator with these settings:
- Pattern: Chessboard
- Rows:7, Columns: 9
- Square size: 25mm
- Print at exactly 100% scale (disable "fit to page")

Mount the printed checkerboard on a flat, rigid surface like a clipboard, book, or cardboard. It is important for the paper to be completely flat without distortions to prevent bad readings.

Start the camera node at your intended runtime resolution:

```bash
ros2 run v4l2_camera v4l2_camera_node --ros-args \
  -p video_device:="/dev/video0" \
  -p image_size:="[640,480]"
```

In a second terminal, run the calibration tool:
```bash
ros2 run camera_calibration cameracalibrator \
  --size 8x6 --square 0.025 \
  --ros-args -r image:=/image_raw -r camera/set_camera_info:=/v4l2_camera/set_camera_info
```

A GUI should load up with four bars labeled "X/Y/Size/Skew" and three grayed out buttons reading "CALIBRATE, SAVE, COMMIT." The Calibrate button only activates once enough samples are taken, which is when all four bars are green.

Place the checkerboard in front of the camera, multicolor lines should pick up the corners of the squares. Moving and tilting the board around at various angles and distances fills up the bars.

Click "CALIBRATE" **only once** and wait, the window will appear frozen while it solves which is expected. The progress is visible in the terminal, not in the GUI. **DO NOT click multiple times** as that would queue up multiple solves and slow down the process *significantly*. 

Once solved, click "SAVE." The calibration tool saves results to `/tmp/calibrationdata.tar.gz`. Extract the result:

```bash
cd /tmp
mkdir calib_output
tar -xf calibrationdata.tar.gz -C calib_output
```

The wrapper does not read the ROS 'camera_info' YAML format directly, but instead uses its own OpenCV FileStorage-style format with individually named fields:

```yaml
Camera.fx: <camera_matrix[0][0]>
Camera.fy: <camera_matrix[1][1]>
Camera.cx: <camera_matrix[0][2]>
Camera.cy: <camera_matrix[1][2]>
Camera.k1: <distortion[0]>
Camera.k2: <distortion[1]>
Camera.p1: <distortion[2]>
Camera.p2: <distortion[3]>
Camera.k3: <distortion[4]>
Camera.width: 640
Camera.height: 480
Camera.fps: 30
```

Manually write the calibration values from `calib_output/ost.yaml` into `~/colcon_ws/src/orbslam3_ros2/config/camera_and_slam_settings.yaml`. Leave the rest of the file (ORB extractor parameters, etc.) at its defaults unless you have a specific reason to change them.

Rebuild so the updated config is installed:
```bash
cd ~/colcon_ws
colcon build --packages-select orbslam3_ros2 --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

### Finding Your Camera's Stable Device Path
It is possible for USB device numbers (`/dev/video0`, `/dev/video1`, ...) to change due to reboots or reconnections. When this happens, ORB-SLAM3 loses access to the camera feed and the pipeline stops. To work around this, use the persistent `by-id` symlink instead:

```bash
ls -la /dev/v4l/by-id/
```

Use the exact filename ending in '-video-index0' ('-index1' is an auxiliary node, do not use that one). This project's included `start_camera.sh' script already looks up the camera by this stable path rather than a hardcoded device number. Update the vendor string inside that script to match your specific camera if it is different from the ICSpring camera used in development.

## 5. Running ORB-SLAM3
There are three components to run together: the camera node, the main SLAM/TF-bridge/octomap launch, and (optionally) visualization.

**Terminal 1 - Camera:**

```bash
~/start_camera.sh
```

**Terminal 2 - SLAM +TF bridge + octomap:**

```bash
ros2 launch orbslam3_ros2 orbslam3_ros2.launch.py \
  camera_type:=mono \
  visualize:=false \
  start_octomap:=true
```

Visualization is off in this file. The ORB-SLAM3 Pangolin viewer is controlled by a hardcoded flag in `src/orb_slam_mono.cpp` (`bool showPangolin = ...`), if you want to use it change `false` to `true` and save. 
`visualize:=false` controls RViz2 only.

**Terminal 3 - Verify everything is running:**
```bash
ros2 node list
```
Expect to see: `/v4l2_camera`, `/orbslam3_ros2`, `/odom_to_tf_bridge`, `/octomap_server`.

If everything is running correctly, move the camera through a textured area (that is, not a blank wall) with some side to side motion. Monocular SLAM needs translational parallax to initialize, rotation would not trigger it.

## 6. Verifying Outputs

| Check | Command | Expect |
|---|---|---|
| Image capture rate | `ros2 topic hz /camera/rgb/image_color` | ~20Hz, low jitter |
| SLAM pose | `ros2 topic hz /slam/odometry` | ~15Hz |
| SLAM point cloud | `ros2 topic hz /slam/pointcloud` | ~15Hz |
| TF bridge | `ros2 run tf2_ros tf2_echo map base_footprint` | Live, updating transform (not "frame does not exist") |
| Octomap | `ros2 topic hz /octomap_full` | ~13Hz once tracking is active |
| 2D costmap-ready output | `ros2 topic echo /projected_map --once --field info` | Non-zero width/height/resolution |

Octomap: It is a library that converts SLAM's raw 3D point cloud into an occupancy grid (and octree), which marks space as occupied, free, or unknown. This is the format the navigation stack needs for path planning and obstacle avoidance, rather than working with a raw, unstructured point cloud.
However, it received the data from TF, which is a problem as the wrapper only publishes pose as a plain topic. TF is ROS 2's transform library which tracks the geometric relationship between different coordinate frames, so this project includes a custom bridge node to broadcast pose into TF, so that octomap can find it.
 
If `/octomap_full` produces nothing: confirm `odom_to_tf_bridge` is running and check `ros2 param get /octomap_server base_frame_id` matches the bridge's `child_frame_id` (both should be `base_footprint` by default in this repo).

---

## 7. Known Limitations / Provisional Items 
- **`base_footprint` is currently coincident with the camera** — the TF bridge publishes the camera's pose directly as `base_footprint`, with no physical offset modeled. This is fine for early testing but should be replaced with a proper `base_link`/`base_footprint` chain (via a static transform reflecting the camera's real mounting position) once the robot's physical geometry is finalized.
- **Odometry covariance values are ORB-SLAM3 defaults** (not empirically measured) — treat pose confidence values as provisional, not validated, if used for sensor fusion weighting.
- **Monocular scale is not absolute** — without a second sensor (stereo, depth, or IMU) to ground it, ORB-SLAM3's scale estimate can drift or be a wrong constant factor. Recommended before relying on it for navigation: move the camera a known real-world distance and confirm `/slam/odometry`'s reported displacement matches, to quantify any scale error.
- **IMU (mono-inertial) support is not yet implemented** — the current `orbslam3_ros2` wrapper only supports vision-only mono mode; adding mono-inertial requires wrapper-level changes (IMU subscription, time sync, extrinsic calibration), not just a config flag.
- **No physical robot model (URDF)** exists yet — the TF tree currently stops at `base_footprint`; sensor offsets, wheel odometry, etc. would need to be added as this is built out.

## 8. Troubleshooting
Issues encountered during original development, for reference if similar problems recur:
 
| Symptom | Cause | Fix |
|---|---|---|
| `Package 'orbslam3_ros2' not found` | Workspace overlay not sourced in current shell | `source ~/colcon_ws/install/setup.bash` (add to `~/.bashrc`) |
| `libORB_SLAM3.so: cannot open shared object file` | `LD_LIBRARY_PATH` missing ORB_SLAM3/Thirdparty lib paths | See Section X.x |
| `Vocabulary loading failure: This is not a correct text file!` | `ORBvoc.txt` not correctly extracted/copied | Re-extract from `ORB_SLAM3/Vocabulary/ORBvoc.txt.tar.gz`, re-copy to package config dir |
| SLAM always loads `TUM_RGB-D_Dataset.yaml` regardless of `camera_type` | Known bug: launch file hardcodes the settings path | Already fixed in this repo's launch file — if you see this, your checkout may be stale |
| Camera frame rate unstable (~10Hz, high jitter) despite everything else working | Pangolin viewer + remote display forwarding overhead starving the capture process | Not expected on desktop with a local display; if it recurs, set `showPangolin = false` and rebuild `orbslam3_ros2` |
| `/octomap_full` never publishes, `octomap_server` logs "Nothing to publish, octree is empty" indefinitely | Missing TF broadcast from `map` to `base_footprint` | Ensure `odom_to_tf_bridge` node is running (it's included in this repo's launch file by default) |
| Camera randomly disconnects when handled/moved | Mechanical USB connector fit issue (varies by port, even on the same board) | Test all available ports by physically tugging the plug in each; standardize on whichever holds most securely; consider cable strain relief |

## 9. Still In Progress
- Mono-inertial IMU integration
- Support Nav2 integration

---

## 10. References
ORB-SLAM3: https://github.com/UZ-SLAMLab/ORB_SLAM3/tree/master

ORB-SLAM3 ROS 2 Wrapper (upstream, before modifications in this repo): https://github.com/sagar16812/orbslam3_ros2/tree/main
