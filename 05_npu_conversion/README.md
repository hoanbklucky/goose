# Objective
We want to get a basic, pre-existing computer vision model running on the GooseBot to verify that the model can in fact be executed upon the Rock5C's NPU and that performance is adequate for real-time autonomous functionality.

# Model selection
For robotics applications such as GooseBot, a YOLO model, developed by Ultralytics, is standard. There are numerous YOLO models available now, but the newer YOLO11 has proven to be highly efficient on even resource-constrained hardware.

# Model conversion
While many YOLO11 models are available (including from Ultralytics, themselves), these are often found as ONNX files. For the model to be executed aboard the Rock5C's NPU rather than CPU, the ONNX file must be converted to RKNN.

This process is fairly involved, and a detailed description is provided by Radxa at this repo:
https://github.com/airockchip/rknn_model_zoo/blob/main/examples/yolo11/README.md

While straightforward enough for the pre-existing YOLO11 ONNX file, this will be more complicated for the custom model trained on our dataset in the future. It's best we get acquainted with this process.

