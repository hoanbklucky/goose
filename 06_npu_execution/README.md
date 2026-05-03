# Objective
We previously converted the YOLO11 weights (.pt) file to RKNN for execution aboard the Rock5C's neural processing unit. Now, we can write a Python script that executes the model and streams the live object detection via web server such that the user can evaluate its performance.

# Detection script
Our detection script makes use of the RKNNLite API to run the RKNN file on the NPU and retreive the outputs. We then use Flask to create a webserver which streams the video from the webcam to the user's browser and overlays bounding boxes with labels for detected objects. Note that Flask, cv2, and RKNNLite must be installed via pip before this can work. Further instructions will be added in the near future to detail this process.

The detect script is included in this section of the repo, as is the yolo11.rknn file.

# Procedure
Let's set up the RKNNLite API, the appropriate Python environment, and the detection script to test our model. The following procedures assume:

- Your Rock5c lite is running Radxa's provided Debian-based operating system
- The Rock5c lite is connected to the same WiFi network as your host machine (laptop, probably)
- You've already completed the NPU conversion described in the previous chapter, or otherwise have a pre-converted RKNN-format YOLO11 model

## Install Dependencies
We installed the RKNN-Toolkit2 on our WSL instance or dedicated Ubuntu machine earlier to perform the model conversion. To actually run the model on the Rock5c lite, Rockchip provides a conveniently slimmed-down version of that toolkit that we can install. We start by installing some of the same packages as in the NPU conversion chapter.

    sudo apt install python3-full python3-dev python3-venv python3-pip git

Make and activate a new Python virtual environment just for YOLO.

    python -m venv yolovenv
    source yolovenv/bin/activate

Make and enter a folder for the YOLO detection script.

    mkdir yolodetect
    cd yolodetect

Clone the aforementioned Git repository in the new folder.

    git clone -b v2.3.0 https://github.com/airockchip/rknn-toolkit2.git

This might take a little while longer than it did on your WSL or dedicated Linux host machine, as the Rock5c lite's WiFi interface probably isn't quite as fast, and the microSD card read/write speeds are outmatched by your computer's. Be patient.

Change directory to the packages folder in the RKNN-toolkit-lite2 location. Note that this is very similar to what we did in WSL/Ubuntu22.04, but the 'lite' version of the toolkit.

    cd rknn-toolkit2/rknn-toolkit-lite2/packages

The Radxa image is likely running Python 3.11. You can confirm with

    python --version

Install the appropriate pip packages:

    pip install ./rknn_toolkit_lite2-2.3.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl 

Now, all that's left to install are some remaining Python dependencies: one for general Ultralytics YOLO support, and the last to create a local webserver to stream our object detection video.

    pip install ultralytics flask

That should conclude all of the dependencies that you require.

## Run the Model on NPU
You should have the output of your RKNN conversion from the previous chapter stored somewhere. Copy that whole folder an its contents into the yolodetect folder.

This can be done entirely through Google Drive (on dev computer you uppload the whole folder to Google Drive and on Rock 5C you log in into Google Drive to download it), a terminal in WSL using an SCP command, through SFTP with a client like Termius, or the old-fashioned way with a flash drive. That part is up to you.

Now, copy the detect.py script from this repo into the same folder. If you are using your own model, change the name of the folder on line 9 of the detect.py script before execution to match whatever your RKNN folder is called.

Ensure that your USB webcam is plugged into the Rock5c lite. Run the detection script with

    python detect.py

Once the terminal has shown the initialization process of the script, it should present to you a few URL's. Hold CTRL and click that URL (or copy it into your web browser WITHOUT pressing CTRL+C as it'll kill the script), and wait for the video stream to initialize.

Place an example of an object which was included in your model training in front of the camera, and observe as it is detected and labeled with a bounding box. Modify this script to your heart's content to experiment. Also note how *fast* the model runs on the NPU. In my experiments, the model appeared to be running at approximately 60FPS, and further optimzations can be made to improve this if desired.




