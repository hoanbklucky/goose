import time
import sys
import math
import board
import busio
import tty
import termios
import select
import threading
import gpiod

from adafruit_pca9685 import PCA9685

# ==========================================================
# Robot Configuration
# ==========================================================

SPEED = 0.40
GRACE_PERIOD = 0.30

WHEEL_DIAMETER_IN = 2.5
COUNTS_PER_REV = 1092

WHEEL_CIRCUMFERENCE = math.pi * WHEEL_DIAMETER_IN

# ==========================================================
# GPIO Pin Mapping
# ==========================================================

# Left encoder
LEFT_A_CHIP = "gpiochip4"
LEFT_A_LINE = 11      # PIN11

LEFT_B_CHIP = "gpiochip4"
LEFT_B_LINE = 10      # PIN13

# Right encoder
RIGHT_A_CHIP = "gpiochip4"
RIGHT_A_LINE = 12     # PIN15

RIGHT_B_CHIP = "gpiochip1"
RIGHT_B_LINE = 5      # PIN16

# ==========================================================
# Motor Class
# ==========================================================

class Motor:

    def __init__(self, pca, in1_channel, in2_channel):

        self.in1 = pca.channels[in1_channel]
        self.in2 = pca.channels[in2_channel]

    def set_speed(self, speed):

        pwm = int(abs(speed) * 65535)

        if pwm > 65535:
            pwm = 65535

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

# ==========================================================
# Encoder Class
# ==========================================================

class Encoder:

    def __init__(self,
                 chipA,
                 lineA,
                 chipB,
                 lineB):

        chip1 = gpiod.Chip(chipA)
        chip2 = gpiod.Chip(chipB)

        self.a = chip1.get_line(lineA)
        self.b = chip2.get_line(lineB)

        self.a.request(
            consumer="encoder",
            type=gpiod.LINE_REQ_DIR_IN
        )

        self.b.request(
            consumer="encoder",
            type=gpiod.LINE_REQ_DIR_IN
        )

        self.count = 0

        self.last_state = (
            self.a.get_value() << 1
        ) | self.b.get_value()

    def update(self):

        state = (
            self.a.get_value() << 1
        ) | self.b.get_value()

        transition = (
            self.last_state,
            state
        )

        if transition in [

            (0,1),
            (1,3),
            (3,2),
            (2,0)

        ]:

            self.count += 1

        elif transition in [

            (0,2),
            (2,3),
            (3,1),
            (1,0)

        ]:

            self.count -= 1

        self.last_state = state

# ==========================================================
# Create Encoders
# ==========================================================

left_encoder = Encoder(

    LEFT_A_CHIP,
    LEFT_A_LINE,
    LEFT_B_CHIP,
    LEFT_B_LINE

)

right_encoder = Encoder(

    RIGHT_A_CHIP,
    RIGHT_A_LINE,
    RIGHT_B_CHIP,
    RIGHT_B_LINE

)

# ==========================================================
# Encoder Thread
# ==========================================================

running = True

def encoder_thread():

    global running

    while running:

        left_encoder.update()
        right_encoder.update()

        time.sleep(0.0005)

thread = threading.Thread(
    target=encoder_thread,
    daemon=True
)

thread.start()

# ==========================================================
# Distance Calculation
# ==========================================================

def get_distance_inches():

    average_counts = (

        left_encoder.count +
        right_encoder.count

    ) / 2.0

    revolutions = (

        average_counts /
        COUNTS_PER_REV

    )

    return revolutions * WHEEL_CIRCUMFERENCE

# ==========================================================
# Robot Movement
# ==========================================================

def move_forward():

    print("Forward", end="\r")

    for m in left_motors:
        m.set_speed(SPEED)

    for m in right_motors:
        m.set_speed(SPEED)

def move_backward():

    print("Backward", end="\r")

    for m in left_motors:
        m.set_speed(-SPEED)

    for m in right_motors:
        m.set_speed(-SPEED)

def turn_left():

    print("Left", end="\r")

    for m in left_motors:
        m.set_speed(-SPEED)

    for m in right_motors:
        m.set_speed(SPEED)

def turn_right():

    print("Right", end="\r")

    for m in left_motors:
        m.set_speed(SPEED)

    for m in right_motors:
        m.set_speed(-SPEED)

def stop_all():

    for m in all_motors:
        m.stop()

    print("Stopped", end="\r")

# ==========================================================
# Main Program
# ==========================================================

if __name__ == "__main__":

    # ------------------------------------------------------
    # Initialize PCA9685
    # ------------------------------------------------------

    try:

        i2c = busio.I2C(board.SCL, board.SDA)

        pca = PCA9685(i2c)
        pca.frequency = 100

        # Motor assignments
        motor_fl = Motor(pca, 0, 1)
        motor_rl = Motor(pca, 2, 3)
        motor_rr = Motor(pca, 4, 5)
        motor_fr = Motor(pca, 6, 7)

        left_motors = [
            motor_fl,
            motor_rl
        ]

        right_motors = [
            motor_fr,
            motor_rr
        ]

        all_motors = (
            left_motors +
            right_motors
        )

        print("PCA9685 initialized.")
        print("Encoders initialized.")

    except Exception as e:

        print(f"Initialization Error: {e}")
        running = False
        sys.exit(1)

    # ------------------------------------------------------
    # Keyboard Setup
    # ------------------------------------------------------

    old_settings = termios.tcgetattr(sys.stdin)

    tty.setcbreak(sys.stdin.fileno())

    current_action = stop_all
    current_action()

    last_key_time = time.time()

    print()
    print("===================================")
    print("Motor + Encoder Test")
    print("-----------------------------------")
    print("W = Forward")
    print("S = Backward")
    print("A = Left")
    print("D = Right")
    print("X = Exit")
    print("===================================")

    try:

        while True:

            action = current_action

            # ------------------------------
            # Read Keyboard
            # ------------------------------

            if select.select(
                [sys.stdin],
                [],
                [],
                0.05

            )[0]:

                key = sys.stdin.read(1)

                last_key_time = time.time()

                if key == "w":
                    action = move_forward

                elif key == "s":
                    action = move_backward

                elif key == "a":
                    action = turn_left

                elif key == "d":
                    action = turn_right

                elif key == "x":

                    print("\nExiting...")
                    break

                else:
                    action = stop_all

            elif time.time() - last_key_time > GRACE_PERIOD:

                action = stop_all

            # ------------------------------
            # Update Motors
            # ------------------------------

            if action is not current_action:

                action()

                current_action = action

            # ------------------------------
            # Encoder Data
            # ------------------------------

            left = left_encoder.count
            right = right_encoder.count

            average = (left + right) / 2.0

            distance = get_distance_inches()

            print(
                f"L:{left:6d} "
                f"R:{right:6d} "
                f"AVG:{average:8.1f} "
                f"DIST:{distance:8.2f} in",
                end="\r"
            )

    except KeyboardInterrupt:

        print("\nInterrupted.")

    finally:

        running = False

        stop_all()

        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            old_settings
        )

        pca.deinit()

        print("\n")
        print("Final Results")
        print("----------------------")
        print(f"Left Encoder : {left_encoder.count}")
        print(f"Right Encoder: {right_encoder.count}")
        print(f"Average      : {(left_encoder.count + right_encoder.count)/2:.1f}")
        print(f"Distance     : {get_distance_inches():.2f} inches")
        print("Program finished.")
