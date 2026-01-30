# Objective
We want to get a basic, pre-existing computer vision model running on the GooseBot to verify that the model can in fact be executed upon the Rock5C's NPU and that performance is adequate for real-time autonomous functionality.

If you want to take it on faith that the model will run and instead cut straight to training our own model for use on Goose, you can skip to chapters 7 and 8, then return here when you have a trained model (.pt weights file) that you want to convert to RKNN to run on the Rock5c Lite's neural processing unit.

# Model selection
For robotics applications such as GooseBot, a YOLO model, developed by Ultralytics, is standard. There are numerous YOLO models available now, but the newer YOLO11 has proven to be highly efficient on even resource-constrained hardware.

# Model conversion
While many YOLO11 models are available (including from Ultralytics, themselves), these are often found as ONNX files. For the model to be executed aboard the Rock5C's NPU rather than CPU, the ONNX file must be converted to RKNN.

This process is fairly involved, and a detailed description is provided by Radxa at this repo:
https://github.com/airockchip/rknn_model_zoo/blob/main/examples/yolo11/README.md

While straightforward enough for the pre-existing YOLO11 ONNX file, this will be more complicated for the custom model trained on our dataset in the future. It's best we get acquainted with this process.

# Environment Setup
We'll perform conversion of the model on an Ubuntu 22.04 machine or WSL2 instance of Ubuntu 22.04. For this example, I'll use the latter.

Open a terminal window in the home directory of your WSL instance. Run this command to ensure that Python is up to date and you have the packages required to make Python virtual environments. We'll also install some other requisite packages.

    sudo apt update
    sudo apt install python3-full python3-dev python3-venv python3-pip git

Create a Python virtual environment for the packages used to convert the model. Then, source to activate it. If you leave the terminal or have to resume this process at any point, note that you'll have to re-source the environment.

    python -m venv convenv
    source convenv/bin/activate

Now, let's start installing the dependencies for the conversion process. Make a new folder in which to perform our conversion. Then we'll enter that directory and clone a specific version of Rockchip's neural network toolkit (RKNN-toolkit2)

    mkdir modelconv
    cd modelconv
    git clone -b v2.3.0 https://github.com/airockchip/rknn-toolkit2.git

This toolkit is exceptionally important because it will provide us with a comprehensive list of the other Python packages we need for conversion the following commands will go to the folder of lists.

    cd rknn-toolkit2/rknn-toolkit2/packages/x86_64

Now, if you run the 'ls' command to list the contents of the packages folder, you'll see that there are many files, each of which corresponds to a different Python version. I have found that this is most stable on Python 3.10.12, and the following instructions make the assumption that you will use that version.

Let's tell pip to install all the necessary packages for that Python version:

    pip install -r requirements_cp310-2.3.0.txt
    pip install rknn_toolkit2-2.3.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

We are almost there. Install the Ultralytics package.

    pip install ultralytics

You may see a warning that you have an incompatible Torch version for rknn-toolkit2. That's fine, ignore it for now. There is, however, a dependency that ultralytics automatically updated that will break your conversion, so we have to manually downgrade it before running the conversion command.

    pip install onnx==1.18.0 onnxruntime==1.18.0

Finally, our environment setup for NPU model conversion is complete.

# Convert the Model (finally...)

Training the YOLO11 model isn't within the scope of this document, as there are hundreds of tutorials online on that process. We will assume that you already have you trained model weights (.pt) file.

Move that weights file into the same modelconv folder where we set up our environment in the previous section. In my case, the weights file is called 'goose_yolo11_v1.pt', so the file in the directory looks like 

    ~/modelconv/goose_yolo11_v1.pt

Assuming that the Python venv we set up in the previous section is still active, run the following command to execute the RKNN conversion:

    yolo export model=goose_yolo11_v1.pt format=rknn name=rk3588

After the conversion has run, you can run the 'ls' command to list the directory contents. You should see a .onnx file with the same name as your weights file, as well as a new folder with the same name plus the 'rknn_model' suffix. That folder is our converted RKNN model. You will want to copy that whole folder and all its contents over to the Rock5c lite for execution.

As a side note, keen observers might notice that the "name" parameter in the above command specifies "rk3588", while the actual CPU of the Rock5c lite is rk3582. This isn't a mistake; the rk3582 is in the same processor family as the rk3588, and Rockchip kept their neural network architecture the same.
