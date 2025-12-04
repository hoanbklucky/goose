from ultralytics import YOLO

# Load a model
model = YOLO("yolo11n.pt")

# Train the model
results = model.train(data="goosedataset_final/data.yaml", epochs=100, imgsz=640)
