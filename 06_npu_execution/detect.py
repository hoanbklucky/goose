import cv2
import numpy as np
import sys
from rknnlite.api import RKNNLite
from flask import Flask, Response
import threading
import time

RKNN_MODEL = './yolo11.rknn' 
IMG_SIZE = 640
CLASSES = ("person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
           "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse",
           "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie",
           "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
           "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
           "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut",
           "cake", "chair", "sofa", "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop",
           "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
           "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush")


# --- Global variables for streaming ---
output_frame = None
lock = threading.Lock()

# --- Flask App Initialization ---
app = Flask(__name__)

def post_process(outputs, conf_threshold=0.25, nms_threshold=0.5):
    boxes, scores, class_ids = [], [], []
    output_data = np.squeeze(outputs[0]).T
    
    for row in output_data:
        box_score = row[4:].max()
        if box_score > conf_threshold:
            class_id = row[4:].argmax()
            cx, cy, w, h = row[:4]
            x = int(cx - w / 2)
            y = int(cy - h / 2)
            boxes.append([x, y, int(w), int(h)])
            scores.append(box_score)
            class_ids.append(class_id)

    if len(boxes) > 0:
        indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, nms_threshold)
        if len(indices) > 0:
            final_boxes = np.array(boxes)[indices]
            final_scores = np.array(scores)[indices]
            final_class_ids = np.array(class_ids)[indices]
            return final_boxes, final_scores, final_class_ids
            
    return None, None, None

def inference_loop():
    global output_frame, lock

    rknn = RKNNLite()
    print('--> Loading model')
    ret = rknn.load_rknn(RKNN_MODEL)
    if ret != 0: print('Load model failed!'); return
    print('done')

    print('--> Init runtime environment')
    ret = rknn.init_runtime()
    if ret != 0: print('Init runtime environment failed!'); return
    print('done')

    cap = cv2.VideoCapture(0)
    if not cap.isOpened(): print("Error: Could not open webcam."); return
        
    frame_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print("\n--- NPU Inference is running ---")
    while True:
        ret, frame = cap.read()
        if not ret: break

        input_frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
        input_frame = cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB)
        input_frame = input_frame.astype(np.float32) / 255.0
        
        input_frame_4d = np.expand_dims(input_frame, axis=0)
        input_for_npu = input_frame_4d.transpose(0, 3, 1, 2)
        
        outputs = rknn.inference(inputs=[input_for_npu])
        boxes, scores, classes = post_process(outputs)
        
        # Draw boxes on the original frame
        if boxes is not None and len(boxes) > 0:
            for box, score, cls in zip(boxes, scores, classes):
                x, y, w, h = box
                x_scaled = int(x / IMG_SIZE * frame_width)
                y_scaled = int(y / IMG_SIZE * frame_height)
                w_scaled = int(w / IMG_SIZE * frame_width)
                h_scaled = int(h / IMG_SIZE * frame_height)
                
                # Draw the bounding box
                cv2.rectangle(frame, (x_scaled, y_scaled), (x_scaled + w_scaled, y_scaled + h_scaled), (0, 255, 0), 2)
                # Draw the label
                label = f"{CLASSES[cls]}: {score:.2f}"
                cv2.putText(frame, label, (x_scaled, y_scaled - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        with lock:
            output_frame = frame.copy()

    cap.release()
    rknn.release()

def generate_frames():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            # Encode the frame in JPEG format
            (flag, encoded_image) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue

        # Yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encoded_image) + b'\r\n')
        time.sleep(0.05) # Limit frame rate slightly

@app.route("/")
def index():
    return "<html><head><title>NPU Video Stream</title></head><body><h1>NPU Video Stream</h1><img src='/video_feed'></body></html>"

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype = "multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    # Start the inference thread
    inference_thread = threading.Thread(target=inference_loop)
    inference_thread.daemon = True
    inference_thread.start()
    
    # Start the Flask web server
    print("--- Starting web server... ---")
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)