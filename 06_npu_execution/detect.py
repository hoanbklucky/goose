import cv2
from flask import Flask, Response, render_template_string
from ultralytics import YOLO

# --- Configuration ---
# IMPORTANT: Use the exact model path you were using in your command.
# If your model file is named 'yolo11n_dts_rknn_model.rknn', use that.
# The YOLO class is smart and will load .pt, .rknn, etc.
MODEL_PATH = 'goose_yolo11_v1_rknn_model' 

# Set the host IP to '0.0.0.0' to make it accessible on your network
HOST_IP = '0.0.0.0'
HOST_PORT = 5000
# ---------------------

app = Flask(__name__)

# Load your YOLOv11 RKNN model
try:
    model = YOLO(MODEL_PATH)
    print(f"Successfully loaded model from {MODEL_PATH}")
except Exception as e:
    print(f"Error loading model: {e}")
    print("Please ensure the MODEL_PATH is correct and the model file exists.")
    exit()

def generate_frames():
    """
    Generator function to stream video frames with YOLO detection.
    """
    print("Starting prediction stream from source 0 (webcam)...")
    
    # Use stream=True for continuous video processing
    # show=False prevents Ultralytics from opening its own cv2 window
    try:
        results_generator = model(source=0, stream=True, show=False)
    except Exception as e:
        print(f"Error starting video stream (source=0): {e}")
        print("Is the camera connected and accessible?")
        return

    for r in results_generator:
        try:
            # .plot() is the easiest way to get the frame with boxes drawn
            annotated_frame = r.plot() 

            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if not ret:
                print("Failed to encode frame")
                continue

            # Convert to bytes and yield in multipart format
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        except Exception as e:
            print(f"Error during processing/streaming: {e}")
            break

@app.route('/')
def index():
    """Video streaming home page."""
    # A simple HTML page to display the video feed
    html_page = """
    <html>
    <head>
        <title>YOLO RKNN Stream</title>
        <style>
            body { font-family: sans-serif; text-align: center; background-color: #222; color: white; }
            img { background-color: #000; border: 1px solid #555; margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>YOLO RKNN Live Stream</h1>
        <h3>(Running on Radxa Rock 5C lite)</h3>
        <img src="{{ url_for('video_feed') }}" width="640" height="480">
    </body>
    </html>
    """
    return render_template_string(html_page)

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    # Returns the generator function as a multipart response
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print(f"Starting Flask server...")
    print(f"Access the stream in your browser at: http://<YOUR_ROCK_5C_IP>:{HOST_PORT}/")
    app.run(host=HOST_IP, port=HOST_PORT, debug=False, threaded=True)
