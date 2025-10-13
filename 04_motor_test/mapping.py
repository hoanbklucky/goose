import time
import sys
import board
import busio
from adafruit_pca9685 import PCA9685
import tty
import termios
import select

# --- Motor and Robot Configuration ---
SPEED = 0.8 # Use a moderate speed for testing

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

def move_motor(motor_index_to_move):
    """Activates one motor and stops all others."""
    print(f"Moving Motor {motor_index_to_move + 1}      ", end="\r")
    for i, motor in enumerate(all_motors):
        if i == motor_index_to_move:
            motor.set_speed(SPEED)
        else:
            motor.stop()

def stop_all():
    """Stops all motors."""
    print("All Motors Stopped ", end="\r")
    for motor in all_motors:
        motor.stop()

# Function to check if a key has been pressed
def is_key_pressed():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

# --- Main Program ---
if __name__ == "__main__":
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pca = PCA9685(i2c)
        pca.frequency = 100
        
        # Initialize motors and put them in a list for easy access
        motor1 = Motor(pca, in1_channel=0, in2_channel=1) # Controlled by key '1'
        motor2 = Motor(pca, in1_channel=2, in2_channel=3) # Controlled by key '2'
        motor3 = Motor(pca, in1_channel=4, in2_channel=5) # Controlled by key '3'
        motor4 = Motor(pca, in1_channel=6, in2_channel=7) # Controlled by key '4'
        
        all_motors = [motor1, motor2, motor3, motor4]
        
        print("All motors initialized.")
        
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)

    # Get the original terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Put the terminal in cbreak mode (reads keys instantly)
        tty.setcbreak(sys.stdin.fileno())
        
        print("Ready for input. Press 1, 2, 3, or 4 to move a motor. Press x to exit.")
        
        while True:
            if is_key_pressed():
                key = sys.stdin.read(1)
                if key == '1':
                    move_motor(0)
                elif key == '2':
                    move_motor(1)
                elif key == '3':
                    move_motor(2)
                elif key == '4':
                    move_motor(3)
                elif key == 'x':
                    print("\nExiting...")
                    break
            else:
                # If no key is pressed, stop all motors
                stop_all()
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting...")
        
    finally:
        stop_all()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\nProgram finished.")