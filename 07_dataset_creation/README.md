# Objective
Our computer vision model that will be used aboard GooseBot must be able to detect the lines on a road and the rubber duckies used to simulate pedestrians. By default, YOLO11 is not trained to recognize these objects. We must create a dataset that can be used to train the model to recognize these objects.

# Dataset
The dataset has been created by taking photos from the perspective of the robot in the simulated town and labeling them using Roboflow. The produced dataset is included in this section of the repo. It has been formatted specifically to train YOLO11 models.