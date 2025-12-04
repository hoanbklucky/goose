import cv2
import time
import board
import busio
import threading
from flask import Flask, Response, render_template_string
from adafruit_pca9685 import PCA9685
from ultralytics import YOLO

# --- CONFIGURATION ---
MODEL_PATH = '~/yolodetect/goose_yolo11_v1_rknn_model'
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CENTER_X = CAMERA_WIDTH / 2

# FLASK CONFIG
HOST_IP = '0.0.0.0'
HOST_PORT = 5000

# --- TUNING ---
ROI_VERTICAL_CUTOFF = 0.65 
Kp = 0.0007                
Kd = 0.0009 
BASE_SPEED = 0.12       
LANE_WIDTH_PIXELS = 450 

# STOP SIGN LOGIC
STOP_DURATION = 2.0        
STOP_COOLDOWN = 5.0        
STOP_THRESHOLD_Y = CAMERA_HEIGHT * 0.8 

# MOTOR PHYSICS
MIN_MOTOR_POWER = 0.07   
MAX_STEER = 0.6          

# --- GLOBAL VARIABLES FOR STREAMING ---
output_frame = None
lock = threading.Lock()

# --- FLASK APP ---
app = Flask(__name__)

# --- Motor Class ---
class Motor:
    def __init__(self, pca, in1, in2):
        self.pca = pca
        self.in1 = pca.channels[in1]
        self.in2 = pca.channels[in2]

    def set_speed(self, speed):
        if abs(speed) < 0.01:
            pwm = 0
        else:
            abs_s = abs(speed)
            mapped_speed = MIN_MOTOR_POWER + (abs_s * (1.0 - MIN_MOTOR_POWER))
            pwm = int(min(mapped_speed, 1.0) * 65535)

        if speed > 0:
            self.in1.duty_cycle = pwm
            self.in2.duty_cycle = 0
        elif speed < 0:
            self.in1.duty_cycle = 0
            self.in2.duty_cycle = pwm
        else:
            self.stop()
            
    def stop(self):
        self.in1.duty_cycle = 0
        self.in2.duty_cycle = 0

# --- ROBOT LOGIC THREAD ---
def robot_control_loop():
    global output_frame, lock
    
    # 1. Init Hardware
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pca = PCA9685(i2c)
        pca.frequency = 100
        left_motors = [Motor(pca, 7, 6), Motor(pca, 2, 3)]
        right_motors = [Motor(pca, 5, 4), Motor(pca, 0, 1)]
    except Exception as e:
        print(f"Hardware Init Error: {e}")
        return

    def set_drive(fwd, steer):
        steer = max(min(steer, MAX_STEER), -MAX_STEER)
        left = fwd + steer
        right = fwd - steer
        max_val = max(abs(left), abs(right))
        if max_val > 1.0:
            left /= max_val
            right /= max_val
        for m in left_motors: m.set_speed(left)
        for m in right_motors: m.set_speed(right)

    def stop_all():
        for m in left_motors + right_motors: m.stop()

    # 2. Load Model
    print("Loading YOLO Model...")
    model = YOLO(MODEL_PATH)
    
    prev_error = 0
    last_stop_time = 0
    
    print("\n--- ROBOT STARTED ---")

    try:
        # Run inference
        results = model(source=0, stream=True, show=False, conf=0.5, imgsz=640, verbose=False)
        
        for result in results:
            boxes = result.boxes
            
            # --- VISION PROCESSING ---
            best_y_x = None
            best_w_x = None
            max_y_area = 0
            max_w_area = 0
            stop_requested = False
            
            current_time = time.time()
            
            for box in boxes:
                cls = model.names[int(box.cls[0])]
                x, y, w, h = box.xywh[0].tolist()
                
                # Red Line Check
                if cls == 'redline':
                    if y > STOP_THRESHOLD_Y:
                        if (current_time - last_stop_time) > STOP_COOLDOWN:
                            stop_requested = True
                
                # Lane Check (Turn Later Logic)
                cutoff_pixel = CAMERA_HEIGHT * ROI_VERTICAL_CUTOFF
                if y < cutoff_pixel: 
                    continue
                
                area = w * h
                if cls == 'yellowline' and area > max_y_area:
                    max_y_area = area
                    best_y_x = x
                elif cls == 'whiteline' and area > max_w_area:
                    max_w_area = area
                    best_w_x = x

            # --- VIDEO FRAME UPDATE ---
            # Generate the annotated frame for the web browser
            annotated_frame = result.plot()
            
            # --- CONTROL LOGIC ---
            
            # 1. Execute Stop?
            if stop_requested:
                print("!!! STOPPING !!!")
                stop_all()
                
                # Draw STOP text on frame
                cv2.putText(annotated_frame, "STOPPING FOR LINE", (50, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                
                # Update global frame before sleeping so browser sees the message
                with lock:
                    output_frame = annotated_frame.copy()
                
                time.sleep(STOP_DURATION)
                last_stop_time = time.time()
                continue 

            # 2. Calculate Target
            if best_y_x is not None and best_w_x is not None:
                target_x = (best_y_x + best_w_x) / 2
            elif best_y_x is not None:
                target_x = best_y_x + (LANE_WIDTH_PIXELS / 2)
            elif best_w_x is not None:
                target_x = best_w_x - (LANE_WIDTH_PIXELS / 2)
            else:
                target_x = CENTER_X 
            
            # 3. PID
            error = target_x - CENTER_X
            derivative = error - prev_error
            prev_error = error
            steering = (error * Kp) + (derivative * Kd)
            
            set_drive(BASE_SPEED, steering)

            # --- VISUAL DEBUGGING ON VIDEO ---
            # Draw a Green Circle at the calculated Target X
            # Y is set to ROI Cutoff line to visually match detection area
            debug_y = int(CAMERA_HEIGHT * ROI_VERTICAL_CUTOFF) + 20
            cv2.circle(annotated_frame, (int(target_x), debug_y), 10, (0, 255, 0), -1)
            
            # Draw Center Line
            cv2.line(annotated_frame, (int(CENTER_X), 0), (int(CENTER_X), CAMERA_HEIGHT), (255, 255, 255), 1)

            # Update global frame
            with lock:
                output_frame = annotated_frame.copy()

    except Exception as e:
        print(f"Robot Loop Error: {e}")
    finally:
        stop_all()
        print("Robot Loop Ended")

# --- FLASK STREAMING FUNCTIONS ---

def generate_frames():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            
            # Encode frame
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
        
        # Yield the output frame in byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')
        
        # Limit stream framerate slightly to save bandwidth/CPU
        time.sleep(0.03) 

@app.route('/')
def index():
    return render_template_string("""
    <html>
    <head>
        <title>Robot Vision</title>
        <style>
            body { background: #111; color: #eee; text-align: center; font-family: monospace; }
            img { border: 2px solid #555; margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>RADXA ROBOT V11</h1>
        <p>Running: Stop Line + Late Turn Logic</p>
        <img src="{{ url_for('video_feed') }}" width="640" height="480">
    </body>
    </html>
    """)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- MAIN ENTRY POINT ---
if __name__ == "__main__":
    # 1. Start Robot Logic in a Background Thread
    # daemon=True means this thread dies automatically if the main program quits
    t = threading.Thread(target=robot_control_loop, daemon=True)
    t.start()
    
    # 2. Start Flask Server in Main Thread
    print(f"Starting Web Server at http://{HOST_IP}:{HOST_PORT}")
    try:
        app.run(host=HOST_IP, port=HOST_PORT, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Stopping...")