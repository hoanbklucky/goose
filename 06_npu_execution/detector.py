"""
Shared YOLO detector used by both the Flask app and the ROS2 node.
Run inference on frames and return annotated image + structured detections.
"""
import cv2
from pathlib import Path

# Lazy load to avoid pulling ultralytics when only running ROS2 (optional)
def get_model(model_path: str = "best.onnx"):
    from ultralytics import YOLO
    path = Path(model_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / model_path
    return YOLO(str(path))


def run_detection(model, frame, conf_threshold=0.25, iou_threshold=0.45):
    """
    Run YOLO on a single BGR frame.

    Args:
        model: Loaded YOLO model (from get_model()).
        frame: BGR numpy array (OpenCV format).
        conf_threshold: Confidence threshold for detections.
        iou_threshold: IOU threshold for NMS.

    Returns:
        tuple: (annotated_frame, detections)
        - annotated_frame: BGR image with boxes drawn (from model.plot()).
        - detections: list of dicts with keys:
            'bbox_xyxy': (x1, y1, x2, y2)
            'center_x', 'center_y', 'size_x', 'size_y'
            'class_id', 'class_name', 'score'
    """
    results = model.predict(
        frame,
        conf=conf_threshold,
        iou=iou_threshold,
        verbose=False,
        stream=False,
    )
    if not results:
        return frame, []

    r = results[0]
    annotated = r.plot()  # BGR image with boxes

    detections = []
    if r.boxes is None:
        return annotated, detections

    names = r.names or {}
    xyxy = r.boxes.xyxy.cpu().numpy()
    cls_ids = r.boxes.cls.cpu().numpy().astype(int)
    confs = r.boxes.conf.cpu().numpy()

    for i in range(len(xyxy)):
        x1, y1, x2, y2 = xyxy[i]
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        sx = float(x2 - x1)
        sy = float(y2 - y1)
        class_id = int(cls_ids[i])
        class_name = names.get(class_id, f"class_{class_id}")
        score = float(confs[i])
        detections.append({
            "bbox_xyxy": (float(x1), float(y1), float(x2), float(y2)),
            "center_x": cx,
            "center_y": cy,
            "size_x": sx,
            "size_y": sy,
            "class_id": class_id,
            "class_name": class_name,
            "score": score,
        })

    return annotated, detections
