import time
import sys
import board
import busio
from adafruit_pca9685 import PCA9685
import tty
import termios
import select

# --- Motor and Robot Configuration ---
SPEED = 0.7
# Grace period in seconds to wait for another keypress before stopping
GRACE_PERIOD = 0.3

class Motor:
    """A class to control one motor via a PCA9685 PWM driver."""
    def __init__(self, pca, in1_channel, in2_channel):
        self.pca = pca
        self.in1 = pca.channels[in1_channel]
        self.in2 = pca.channels[in2_channel]

    def set_speed(self, speed):
        """Sets the motor speed and direction from -1.0 to 1.0."""
        pwm_value = int(abs(speed) * 65535)
        if pwm_value > 65535: pwm_value = 65535
        
        if speed > 0:
            self.in1.duty_cycle = pwm_value
            self.in2.duty_cycle = 0
        elif speed < 0:
            self.in1.duty_cycle = 0
            self.in2.duty_cycle = pwm_value
        else:
            self.stop()
            
    def stop(self):
        self.in1.duty_cycle = 0
        self.in2.duty_cycle = 0

# --- Robot Movement Functions ---
def move_forward():
    print("Forward ", end="\r")
    for motor in right_motors: motor.set_speed(SPEED)
    for motor in left_motors: motor.set_speed(SPEED)

def move_backward():
    print("Backward", end="\r")
    for motor in right_motors: motor.set_speed(-SPEED)
    for motor in left_motors: motor.set_speed(-SPEED)

def turn_left():
    print("Left    ", end="\r")
    for motor in right_motors: motor.set_speed(SPEED)
    for motor in left_motors: motor.set_speed(-SPEED)

def turn_right():
    print("Right   ", end="\r")
    for motor in right_motors: motor.set_speed(-SPEED)
    for motor in left_motors: motor.set_speed(SPEED)

def stop_all():
    print("Stopped ", end="\r")
    for motor in all_motors: motor.stop()

# --- Main Program ---
if __name__ == "__main__":
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pca = PCA9685(i2c)
        pca.frequency = 100
        
        motor_fl = Motor(pca, in1_channel=7, in2_channel=6)
        motor_fr = Motor(pca, in1_channel=5, in2_channel=4)
        motor_rl = Motor(pca, in1_channel=2, in2_channel=3)
        motor_rr = Motor(pca, in1_channel=0, in2_channel=1)
        
        all_motors = [motor_fl, motor_rl, motor_fr, motor_rr]
        right_motors = [motor_fr, motor_rr]
        left_motors = [motor_fl, motor_rl]
        
        print("All motors initialized.")
        
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)

    old_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin.fileno())
        
        print("Ready for input. Press WASD to move. Press x to exit.")
        
        # Start in a known state
        current_action = stop_all
        current_action()
        last_key_time = 0

        # Main control loop
        while True:
            # Default to the current action if nothing changes
            action = current_action

            # Check if a key is pressed
            if select.select([sys.stdin], [], [], 0.05)[0]:
                key = sys.stdin.read(1)
                last_key_time = time.time()
                
                if key == 'w':
                    action = move_forward
                elif key == 's':
                    action = move_backward
                elif key == 'a':
                    action = turn_left
                elif key == 'd':
                    action = turn_right
                elif key == 'x':
                    print("\nExiting...")
                    break
                else:
                    action = stop_all
            
            # If no key has been pressed for the duration of the grace period, stop.
            elif time.time() - last_key_time > GRACE_PERIOD:
                action = stop_all
            
            # Only send a new command to the motors if the state has changed.
            if action is not current_action:
                action()
                current_action = action
        

    except KeyboardInterrupt:
        print("\nExiting...")
        
    finally:
        stop_all()
        termios.tcgetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\nProgram finished.")
