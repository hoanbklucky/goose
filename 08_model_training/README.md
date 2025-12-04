# YOLO11 Model Training
Training the YOLO11 model on our custom dataset is made remarkably easy through Ultralytics' provided Python package. 

The singular qualification for a smooth training experience is the use of a host machine with significant graphical computational resources. A desktop or laptop gaming computer with a reasonably modern Nvidia RTX graphics card is excellent for this purpose. More computationally-constrained systems can also accomplish training if they have at least 8GB of RAM installed, but they will use the CPU to train instead, and may thus take hours or even days to complete.

If a computer with discrete graphics is not at your disposal, you may also train the model on a Google Colab instance. There are numerous tutorials online instructing to this end.

In this example, training is completed upon a desktop computer with an Nvidia RTX 2060 with 6GB of dedicated video memory and 16GB of RAM. This is performed in Ubuntu 24.04 via WSL, but it is also fairly easy to train in Windows.

# Environment Setup
We are going to make a new Python virtual environment for training, as older virtual environments used for RKNN conversion and testing may have installed package versions that could complicate training execution. It is best practice to use different virtual environments for different functional purposes, such as these. Here's a refresher on the process.

Make sure the requisite Python packages are installed:

    sudo apt install python3-full python3-dev python3-venv

Create and activate the virtual environment (we'll call this one 'trainenv').

    python -m venv trainenv
    source trainenv/bin/activate

Install the Ultralytics Python package. This will automatically install all of Ultralytics' dependencies as well.

    pip install ultralytics

Make a directory for our training inputs and outputs.

    mkdir yolotrain
    cd yolotrain

# Write the Trainer Script
While it is possible to complete the entire training process using just a single terminal command, I find it more transparent to write a Python script for this purpose. It will show you each granular step in the process.

Take a look at the included 'trainer.py' file. Place this file in the yolotrain folder.

The script imports the Ultralytics Python package we just installed, and more specifically, loads the YOLO components within that library.

Then, it pulls the yolo11n.pt weights from Ultralytics pre-trained, standard YOLO11 nano model. This is an excellent basis upon which to build, as the training process would otherwise have to start from scratch with no context but the images we are providing.

The next line actually queues the training procedure, with the pre-trained model as its basis and the provided training data as the new information upon which to customize the model.

To this end, the script must know exactly where to find our training data. It is recommended to place the entire extracted dataset within the yolotrain folder to simplify the file paths used. For instance, the trainer.py file provided uses the 'goosedataset_final/data.yaml' path, which is able to find the data.yaml file inside the goosedataset_final folder, assuming that folder was extracted and placed inside the yolotrain folder.

The data.yaml file enumerates all the images and labels that will be used for training and validation. This will have been generated during the dataset creation stage.

# Train the Model
Now that we have completed the entire setup process, training the model is as simple as executing the trainer script. Note that the script specified 100 training epochs. This can be increased or decreased as necessary, but it was found during testing that 100 epochs yielded a reasonably accurate object detection model, even despite the relatively small, 44-image dataset.

Your trained model will either be placed directly within the yolotrain folder as a new file ending in '.pt', or it will appear inside a 'runs/weights/best.pt' file.

You can now repeat the RKNN conversion procedure outlined in chapter 5, but using this new customized weights file. 