# Activity 09 - Autonomous Lane Following

## Mission

Combine RKNN object detection with four-motor control, verify the controller while the wheels are off the ground, tune lane following at low speed, and complete a narrated autonomous run that follows the lane and responds to a red stop line.

## Why It Matters

This is the end-to-end autonomy activity. The camera measures the road, the model converts pixels into semantic objects, the controller estimates the lane center, and PWM commands change the robot's motion. Each layer can appear correct alone but fail when timing, camera geometry, motor asymmetry, and uncertainty interact.

## Success Criteria

- The RKNN model detects `yellowline`, `whiteline`, and `redline` using the exact class spellings expected by `drive.py`.
- Debug streaming works while motor output remains disabled.
- Motor direction is verified with the chassis lifted.
- Steering sign is correct for camera-left and camera-right errors.
- GooseBot follows the lane at low speed and stops for the assigned red line.
- The group records tuning changes and can explain the perception-control loop.

## Prerequisites

- Correct motor mapping from [Activity 04](../04_motor_test/README.md).
- Working RKNN browser detection from [Activity 06](../06_npu_execution/README.md).
- A verified editing connection from [Work on GooseBot Code - Three Editing Methods](../00_set_up/REMOTE_DEVELOPMENT.md).
- A model containing the required lane classes.
- An approved model-town course with dashed yellow lane dividers, solid white boundaries, and red stop bars.
- A clear test area, one operator, one spotter, and immediate access to power disconnect.

## Safety Gate

- Begin with the robot on a stand and motor output disabled in software.
- Use `BASE_SPEED = 0.08` or a lower instructor-approved value for initial motion tests.
- Keep people out of the course and never test near stairs, traffic, table edges, or fragile equipment.
- The spotter must be ready to lift the robot or disconnect power.
- Stop immediately if video freezes, detections disappear repeatedly, motion reverses, or control oscillates violently.
- This is an instructional demonstration, not a safety-rated autonomous vehicle controller.

## Part 1 - Prepare the Runtime Directory

Connect to the ROCK 5C using the [remote-development guide](../00_set_up/REMOTE_DEVELOPMENT.md). Run `hostname`, `whoami`, and `pwd` to verify the remote computer, then activate the working NPU environment and copy the supplied script:

```bash
source ~/yolovenv/bin/activate
cd ~/yolodetect
cp ~/goose/09_self_driving/drive.py ~/yolodetect/
python -m pip install adafruit-blinka adafruit-circuitpython-pca9685 gpiod flask ultralytics
```

The `board` module comes from Adafruit Blinka; do not install an unrelated package merely because it is named `board`.

## Part 2 - Configure Named Variables

Open `drive.py` on the ROCK 5C using VS Code Remote SSH or terminal SSH + `nano`. Confirm that VS Code shows the SSH host or that the terminal prompt is remote; do not edit the separate laptop clone. Search for these names rather than fixed line numbers.

### Model path

```python
MODEL_PATH = './self_driving_best_rknn_model'
```

Set it to the exact RKNN folder tested in Activity 06.

### Motor map

Inside `robot_control_loop()`, set the channel pairs using the Activity 04 map:

```python
left_motors = [Motor(pca, 0, 1), Motor(pca, 2, 3)]
right_motors = [Motor(pca, 6, 7), Motor(pca, 4, 5)]
```

These numbers are examples. Preserve the verified direction for each physical motor.

### Initial tuning values

```python
ROI_VERTICAL_CUTOFF = 0.65
Kp = 0.0007
Kd = 0.0009
BASE_SPEED = 0.08
LANE_WIDTH_PIXELS = 450
```

Change only one or two variables at a time and record each test.

## Part 3 - Run Perception with Motion Disabled

The supplied script contains this motor command commented out:

```python
# set_drive(BASE_SPEED, steering)
```

Leave it commented for the first test. Run:

```bash
cd ~/yolodetect
python drive.py
```

Open `http://ROCK5C_IP_ADDRESS:5000` on the laptop. The overlay reports:

| Value | Meaning |
|---|---|
| `best_w_x` | horizontal center of the selected white-line detection |
| `best_y_x` | horizontal center of the selected yellow-line detection |
| `target_x` | estimated center of the lane |
| `CENTER_X` | horizontal center of the camera frame |
| `error` | `target_x - CENTER_X` |
| `steering` | PD correction computed from error and its change |
| `BASE_SPEED` | forward command before steering correction |

Aim the camera forward and slightly downward so lane markings appear in the lower region of interest. Place the robot centered and straight, then manually rotate it left and right. Confirm the error and steering change sign. If the sign does not match the required corrective turn, do not enable motion.

## Part 4 - Lifted Motor Test

After perception behaves correctly:

1. stop the program;
2. place the robot on the stand with all wheels clear;
3. uncomment `set_drive(BASE_SPEED, steering)`;
4. save and rerun `python drive.py`; and
5. move the lane pattern or safely change the robot's viewing angle while observing the wheels.

Expected behavior:

- centered target: both sides move forward at similar speed;
- target to one side: the controller changes left/right speeds to steer toward it;
- red line close to the bottom of the frame: all motors stop for `STOP_DURATION`;
- no usable lane detection: the current reference controller uses a centered target, so supervise closely and stop rather than trusting this fallback.

If any wheel direction is wrong, stop power and correct the channel map. Do not compensate for wrong wiring with extreme controller gains.

A lifted reference test is shown in this [short video](https://youtube.com/shorts/GMXl9YynOF8?feature=share).

## Part 5 - Low-Speed Floor Test

1. Put GooseBot in the center of the outer lane, aligned between the dashed yellow and solid white lines.
2. Clear the course and position the spotter.
3. Start the script while the spotter controls when the robot is placed on the ground.
4. Complete a short straight segment first.
5. Add a gentle bend only after straight tracking is stable.
6. Add the red stop-line test last.
7. Stop with Ctrl+C or disconnect motor power at the first unsafe behavior.

A reference untuned run is available on [YouTube](https://youtu.be/XVL9MJ0nml4).

## Part 6 - Tune Systematically

Use a table like this for every run:

| Run | Camera angle | ROI cutoff | `Kp` | `Kd` | Base speed | Observation | Next change |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | | 0.65 | 0.0007 | 0.0009 | 0.08 | | |

Guidance:

- Adjust camera aim before changing control gains.
- `ROI_VERTICAL_CUTOFF` controls how much of the upper image is ignored. A larger value emphasizes nearby road markings.
- Increase `Kp` slightly if steering reacts too weakly; reduce it if the robot repeatedly overshoots.
- Increase `Kd` slightly if oscillation needs damping; excessive derivative gain can amplify noisy detections.
- Reduce `BASE_SPEED` whenever behavior is difficult to interpret.
- Tune `LANE_WIDTH_PIXELS` only after measuring the apparent lane spacing in the working camera view.
- Change one main factor per run so cause and effect remain clear.

## How the Controller Works

1. OpenCV captures and horizontally flips a frame.
2. YOLO performs RKNN inference and returns labeled boxes.
3. The controller searches the lower region of interest for the largest `yellowline` and `whiteline` boxes.
4. Their centers estimate the lane center. If only one boundary is visible, `LANE_WIDTH_PIXELS` estimates the missing side.
5. `error = target_x - CENTER_X` measures camera-to-lane offset.
6. Proportional and derivative terms produce `steering`.
7. `set_drive()` adds steering to one side and subtracts it from the other.
8. A nearby `redline` requests a timed stop with a cooldown before another stop can trigger.
9. Flask streams the annotated frame for observation.

The code names this a PID section, but the supplied controller uses proportional and derivative terms only; it is a PD controller because there is no integral term.

## Command Breakdown

| Command or variable | Meaning |
|---|---|
| `cp source destination` | copies the supplied script without changing the repository copy |
| `python drive.py` | starts the vision/control thread and Flask server |
| `MODEL_PATH` | identifies the converted model directory |
| `ROI_VERTICAL_CUTOFF` | ignores detections above a fraction of the frame height |
| `Kp` | proportional steering gain |
| `Kd` | derivative steering gain |
| `BASE_SPEED` | nominal forward motor command |
| `MIN_MOTOR_POWER` | compensates for the minimum command needed to turn a DC motor |
| `MAX_STEER` | limits steering magnitude |
| `STOP_DURATION` | time the motors remain stopped after a red-line event |

## What to Submit

Unless Canvas says otherwise, submit:

1. a short lifted-test video showing the annotated browser stream and correct wheel response to left/right lane error;
2. a narrated autonomous-driving video showing lane following and the assigned stop behavior;
3. the completed tuning table with at least three meaningful runs;
4. the final values for the named configuration variables; and
5. each group member's contribution.

Explain one failure or imperfect behavior and what evidence guided the next change. A controlled engineering test is more valuable than a video that hides failures.

## Troubleshooting

| Problem | Check |
|---|---|
| `best_w_x` or `best_y_x` remains `None` | camera aim, lighting, model classes, confidence, ROI cutoff, and visible lane markings |
| robot steers away from the lane | motor-side mapping or steering sign is wrong; return to the lifted test |
| robot oscillates | lower speed or `Kp`, then adjust `Kd` gradually |
| robot moves before testing is complete | stop immediately and re-comment `set_drive(BASE_SPEED, steering)` |
| one boundary works but center is wrong | measure and adjust `LANE_WIDTH_PIXELS` |
| stop triggers too early/late | inspect box center and tune `STOP_THRESHOLD_Y` at low speed |
| stream works but motors do not | recheck I2C overlay, venv packages, PCA9685 wiring, and Activity 04 mapping |
| inference freezes | stop motor power, end the script, and verify model/camera operation in Activity 06 |

## Completion

You have completed the required GooseBot sequence when every success criterion passes and the submitted evidence documents both the working system and the tuning process. Continue to [optional ROS 2 integration](../10_goose_ros2/README.md) only when assigned.
