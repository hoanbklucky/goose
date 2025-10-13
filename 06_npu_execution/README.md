# Objective
We previously converted the YOLO11 ONNX file to RKNN for execution aboard the Rock5C's neural processing unit. Now, we can write a Python script that executes the model and streams the live object detection via web server such that the user can evaluate its performance.

# Detection script
Our detection script makes use of the RKNNLite API to run the RKNN file on the NPU and retreive the outputs. We then use Flask to create a webserver which streams the video from the webcam to the user's browser and overlays bounding boxes with labels for detected objects. Note that Flask, cv2, and RKNNLite must be installed via pip before this can work. Further instructions will be added in the near future to detail this process.

The detect script is included in this section of the repo, as is the yolo11.rknn file.

