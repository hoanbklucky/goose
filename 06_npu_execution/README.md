# Activity 06 - Run AI Detection on the ROCK 5C NPU

## Mission

Install RKNNLite on the ROCK 5C, load the converted model, run live USB-camera detection on the NPU, and view the annotated stream from a laptop browser.

## Why It Matters

This activity moves perception onto the robot. Browser streaming makes detections observable while GooseBot is untethered, and it verifies the exact model and camera pipeline later used by lane following.

## Success Criteria

- The RKNNLite wheel matches the ROCK 5C Python version and ARM64 architecture.
- `detect.py` loads the group's complete RKNN model folder.
- The USB camera produces frames.
- The browser displays annotated detections from another computer on the same approved network.
- Inference continues without an attached monitor.

## Prerequisites

- Complete [Activity 05](../05_npu_conversion/README.md).
- Complete the SSH/network setup from [Activity 04](../04_motor_test/README.md).
- Copy the complete `_rknn_model` folder to the ROCK 5C.
- Connect a USB webcam.

This is a perception test. Keep motor power disconnected or keep the robot safely lifted; `detect.py` does not need to move the robot.

## Part 1 - Create the ROCK 5C Environment

On the ROCK 5C:

```bash
sudo apt update
sudo apt install python3-full python3-dev python3-venv python3-pip git
cd ~
python3 -m venv yolovenv --system-site-packages
source ~/yolovenv/bin/activate
mkdir -p ~/yolodetect
cd ~/yolodetect
python --version
```

## Part 2 - Install RKNNLite

```bash
git clone -b v2.3.0 https://github.com/airockchip/rknn-toolkit2.git
cd rknn-toolkit2/rknn-toolkit-lite2/packages
ls
```

Choose the ARM64 wheel whose `cp` tag matches `python --version`. For Python 3.11, the course example is:

```bash
python -m pip install ./rknn_toolkit_lite2-2.3.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
```

Return to the working directory and install the remaining packages:

```bash
cd ~/yolodetect
python -m pip install --upgrade pip
python -m pip install flask ultralytics --no-cache-dir --prefer-binary
```

If installation is killed and `free -h` shows very little available memory, ask the instructor before adding swap. Swap can reduce memory pressure but increases microSD writes and is not a substitute for a correct package wheel.

## Part 3 - Prepare the Detection Directory

Copy the supplied script and the converted model folder:

```bash
cp ~/goose/06_npu_execution/detect.py ~/yolodetect/
cd ~/yolodetect
find . -maxdepth 2 -type f -printf '%p\n'
```

Open `detect.py` and set the named configuration variable to the exact model folder:

```python
MODEL_PATH = 'best_rknn_model'
```

Do not follow a fixed line number; search for `MODEL_PATH`, because code lines change over time.

## Part 4 - Verify the Camera

List video devices:

```bash
ls -l /dev/video*
```

Disconnect other webcams if camera numbering is ambiguous. The supplied script uses source `0`. If the camera is not `/dev/video0`, update the `model(source=0, ...)` call only after verifying the correct device.

## Part 5 - Run and View the Stream

```bash
source ~/yolovenv/bin/activate
cd ~/yolodetect
python detect.py
```

The Flask server binds to `0.0.0.0` on port `5000`, which means it listens on the ROCK 5C network interfaces. From the laptop, browse to:

```text
http://ROCK5C_IP_ADDRESS:5000
```

For example, if the approved local address is `192.0.2.10`, use `http://192.0.2.10:5000`. Do not press Ctrl+C in the SSH terminal until the demonstration is finished.

Place known lane, stop-line/sign, or duck examples in view and confirm that labels and boxes appear. This reference implementation prioritizes clarity over benchmark-quality frame-rate measurement.

## Part 6 - Untethered Verification

1. Stop the script with Ctrl+C.
2. Disconnect the monitor and local keyboard if remote boot/network access has already been validated.
3. Reboot, reconnect with SSH, reactivate `yolovenv`, and run `detect.py` again.
4. Open the browser stream from the laptop.
5. If assigned, use Activity 04 keyboard control to reposition the robot slowly while another group member observes the detection stream.

## Command Breakdown

| Command or setting | Meaning |
|---|---|
| `--system-site-packages` | allows the venv to see required packages installed by the OS |
| `cp311` | wheel built for CPython 3.11 |
| `aarch64` | 64-bit ARM architecture used by the ROCK 5C |
| `--no-cache-dir` | avoids retaining a second copy of downloaded packages |
| `--prefer-binary` | asks pip to use wheels instead of compiling source when possible |
| `MODEL_PATH` | path Ultralytics uses to locate the RKNN model directory |
| `HOST_IP = '0.0.0.0'` | listens on all local interfaces; it is not the address typed into the browser |
| `HOST_PORT = 5000` | TCP port used by the Flask stream |

## What to Submit

Unless Canvas says otherwise, submit a narrated video showing:

- the terminal successfully loading the RKNN model;
- the browser stream on the laptop;
- at least two relevant object classes detected from the live webcam; and
- the robot operating without a directly attached monitor.

Include the model-folder name, ROCK 5C Python version, and each group member's contribution.

## Troubleshooting

| Problem | Check |
|---|---|
| RKNNLite wheel will not install | match Python `cp` tag and `aarch64`; do not use the x86-64 toolkit wheel |
| model path error | use `find` to verify the directory name and set `MODEL_PATH` exactly |
| camera cannot open | inspect `/dev/video*`, close other camera programs, and verify USB power |
| browser cannot connect | use the ROCK 5C address rather than `0.0.0.0`, keep the script running, and verify both devices can reach each other |
| detections are wrong | confirm this is the group's trained model and that its class names match the dataset |
| package install is killed | check `free -h`; use the recommended wheel and ask before configuring swap |

## Next Activity

Continue to [Activity 09 - Autonomous Lane Following](../09_self_driving/README.md).
