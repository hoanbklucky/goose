# Activity 05 - Convert the Trained YOLO Model to RKNN

## Mission

Use an Ubuntu development environment to export the trained YOLO `.pt` weights into an RKNN model folder compatible with the ROCK 5C Lite NPU.

## Why It Matters

A PyTorch `.pt` model is convenient for training and laptop testing, but it does not automatically use the Rockchip NPU. RKNN conversion translates the network into the representation expected by Rockchip's runtime so inference can be fast enough for autonomous control.

## Success Criteria

- The conversion runs on an x86-64 Ubuntu 22.04 environment, not on the ROCK 5C.
- The input is the group's trained `best.pt` or equivalent weights file.
- The export produces an RKNN model directory containing the model and metadata.
- The output folder is copied intact for use in Activity 06.

## Prerequisites

- Complete [Activity 08 - Train and Test the AI Model](../08_model_training/README.md).
- A trained YOLO11 `.pt` file.
- A Windows laptop with WSL2 Ubuntu 22.04, or an x86-64 computer running Ubuntu 22.04.
- Several gigabytes of free storage and a reliable network connection.

Do not install the full x86-64 conversion toolkit in the ROCK 5C environment. Activity 06 uses the smaller ARM runtime on the robot.

## Part 1 - Prepare Ubuntu or WSL2

Windows users who do not already have WSL can open an administrator PowerShell and run:

```powershell
wsl --install
```

Restart if requested, install/select Ubuntu 22.04, and create the Linux username and password when prompted. Native Ubuntu users can continue in a terminal.

Install the required system packages:

```bash
sudo apt update
sudo apt install python3-full python3-dev python3-venv python3-pip git
```

## Part 2 - Create an Isolated Conversion Environment

```bash
cd ~
python3 -m venv convenv
source ~/convenv/bin/activate
python --version
mkdir -p ~/modelconv
cd ~/modelconv
```

Keep this environment separate from model training. Conversion depends on versions that may conflict with current training packages.

## Part 3 - Install RKNN Toolkit 2

The course procedure is validated against toolkit version 2.3.0:

```bash
git clone -b v2.3.0 https://github.com/airockchip/rknn-toolkit2.git
cd rknn-toolkit2/rknn-toolkit2/packages/x86_64
python --version
ls
```

Select the requirement file and wheel whose `cp` number matches the Python version. For Python 3.10:

```bash
python -m pip install -r requirements_cp310-2.3.0.txt
python -m pip install ./rknn_toolkit2-2.3.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

For Python 3.12, use the `cp312` files if they are present in the cloned version:

```bash
python -m pip install -r requirements_cp312-2.3.0.txt
python -m pip install ./rknn_toolkit2-2.3.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

Install the export tooling and the course-tested ONNX versions:

```bash
python -m pip install ultralytics
python -m pip install onnx==1.18.0 onnxruntime==1.18.0
```

Package compatibility changes over time. If the exact toolkit branch does not contain a wheel for your Python version, do not substitute a random wheel; use a supported Python environment or ask the instructor for the currently validated combination.

## Part 4 - Copy the Trained Weights

Place the trained weights in `~/modelconv`. For example:

```text
~/modelconv/best.pt
```

Return to the conversion folder and confirm the file is present:

```bash
cd ~/modelconv
ls -lh best.pt
```

## Part 5 - Export RKNN

With `convenv` active:

```bash
yolo export model=best.pt format=rknn opset=19 name=rk3588
```

If your tested environment does not require an explicit ONNX opset, the shorter form is:

```bash
yolo export model=best.pt format=rknn name=rk3588
```

The export may also create an ONNX file. The important deliverable is the complete directory whose name ends with `_rknn_model`. Although the ROCK 5C Lite uses RK3582, the RKNN export target is named `rk3588` because the processors use the same relevant NPU architecture.

Inspect the result:

```bash
find ~/modelconv -maxdepth 2 -type f -printf '%p\n'
```

Do not rename or move individual files inside the generated model directory.

## Part 6 - Transfer the Complete Folder

Copy the entire `_rknn_model` directory to the ROCK 5C with an approved method such as `scp`, SFTP, a flash drive, or cloud storage. Example from the development computer:

```bash
scp -r ~/modelconv/best_rknn_model radxa@192.0.2.10:~/yolodetect/
```

Replace both the folder name and example IP address with your real values.

## Command Breakdown

| Command or option | Meaning |
|---|---|
| `git clone -b v2.3.0 ...` | clones the repository and checks out the specified toolkit release |
| `cp310`, `cp312` | wheel compatibility tags for CPython 3.10 and 3.12 |
| `yolo export` | invokes Ultralytics model export |
| `model=best.pt` | selects the trained PyTorch weights |
| `format=rknn` | requests a Rockchip NPU model |
| `opset=19` | limits the intermediate ONNX operator set when newer operators are unsupported |
| `name=rk3588` | selects the RK3588-family export target used by this workflow |
| `scp -r` | recursively copies a directory over SSH |

## What to Submit

Unless Canvas says otherwise, submit:

- a screenshot or text log showing the successful `yolo export` completion;
- the name and size of the generated RKNN model folder;
- the output of `python --version`; and
- the exact conversion command used.

Do not upload multi-gigabyte toolkit clones or virtual environments to Canvas or GitHub.

## Troubleshooting

| Problem | Check |
|---|---|
| `Unsupported onnx opset` | repeat the export with `opset=19` |
| wheel is not supported | match the wheel's `cp` tag, CPU architecture, and Linux platform to the environment |
| dependency resolver replaces ONNX | reinstall the course-tested ONNX versions after Ultralytics |
| command runs on ARM/ROCK 5C | stop and move conversion to x86-64 Ubuntu/WSL; Activity 06 runs on ARM |
| RKNN directory is incomplete after transfer | recopy the entire folder recursively and compare its file listing |

## Next Activity

Continue to [Activity 06 - Run the RKNN Model on the ROCK 5C](../06_npu_execution/README.md).
