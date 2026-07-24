#!/usr/bin/env python3

import math
import threading
import time
import tty
import termios
import select
import sys

import gpiod

import board
import busio
from adafruit_pca9685 import PCA9685


# ==========================================================
# PCA9685 CONFIGURATION
# ==========================================================

PWM_FREQUENCY = 1000

LEFT_PWM_CHANNEL = 0
RIGHT_PWM_CHANNEL = 1

MAX_PWM = 4095
DRIVE_SPEED = 2500


# ==========================================================
# MOTOR GPIO
# ==========================================================

MOTOR_CHIP = "/dev/gpiochip1"

IN1 = 7
IN2 = 6
IN3 = 5
IN4 = 4


# ==========================================================
# ENCODER GPIO
# ==========================================================

# Left encoder
LEFT_A_CHIP = "/dev/gpiochip4"
LEFT_A_LINE = 11      # Physical Pin 11

LEFT_B_CHIP = "/dev/gpiochip4"
LEFT_B_LINE = 10      # Physical Pin 13

# Right encoder
RIGHT_A_CHIP = "/dev/gpiochip4"
RIGHT_A_LINE = 12     # Physical Pin 15

RIGHT_B_CHIP = "/dev/gpiochip1"
RIGHT_B_LINE = 5      # Physical Pin 16


# ==========================================================
# ENCODER CALIBRATION
# ==========================================================

COUNTS_PER_REV = 1092

WHEEL_DIAMETER_IN = 2.5

WHEEL_CIRCUMFERENCE = math.pi * WHEEL_DIAMETER_IN

INCHES_PER_COUNT = (
    WHEEL_CIRCUMFERENCE /
    COUNTS_PER_REV
)


# ==========================================================
# INITIALIZE PCA9685
# ==========================================================

i2c = busio.I2C(
    board.SCL,
    board.SDA
)

pca = PCA9685(i2c)

pca.frequency = PWM_FREQUENCY


def set_pwm(channel, value):

    value = max(0, min(MAX_PWM, value))

    pca.channels[channel].duty_cycle = value


# ==========================================================
# MOTOR GPIO REQUEST
# ==========================================================

motor_request = gpiod.request_lines(

    MOTOR_CHIP,

    consumer="motor",

    config={

        IN1: gpiod.LineSettings(
            direction=gpiod.line.Direction.OUTPUT,
            output_value=gpiod.line.Value.INACTIVE
        ),

        IN2: gpiod.LineSettings(
            direction=gpiod.line.Direction.OUTPUT,
            output_value=gpiod.line.Value.INACTIVE
        ),

        IN3: gpiod.LineSettings(
            direction=gpiod.line.Direction.OUTPUT,
            output_value=gpiod.line.Value.INACTIVE
        ),

        IN4: gpiod.LineSettings(
            direction=gpiod.line.Direction.OUTPUT,
            output_value=gpiod.line.Value.INACTIVE
        )
    }

)


def gpio_write(pin, state):

    motor_request.set_value(

        pin,

        gpiod.line.Value.ACTIVE
        if state
        else
        gpiod.line.Value.INACTIVE

    )


# ==========================================================
# MOTOR FUNCTIONS
# ==========================================================

def stop_motor():

    gpio_write(IN1, False)
    gpio_write(IN2, False)
    gpio_write(IN3, False)
    gpio_write(IN4, False)

    set_pwm(LEFT_PWM_CHANNEL, 0)
    set_pwm(RIGHT_PWM_CHANNEL, 0)


def forward(speed=DRIVE_SPEED):

    gpio_write(IN1, True)
    gpio_write(IN2, False)

    gpio_write(IN3, True)
    gpio_write(IN4, False)

    set_pwm(LEFT_PWM_CHANNEL, speed)
    set_pwm(RIGHT_PWM_CHANNEL, speed)


def backward(speed=DRIVE_SPEED):

    gpio_write(IN1, False)
    gpio_write(IN2, True)

    gpio_write(IN3, False)
    gpio_write(IN4, True)

    set_pwm(LEFT_PWM_CHANNEL, speed)
    set_pwm(RIGHT_PWM_CHANNEL, speed)


def turn_left(speed=DRIVE_SPEED):

    gpio_write(IN1, False)
    gpio_write(IN2, True)

    gpio_write(IN3, True)
    gpio_write(IN4, False)

    set_pwm(LEFT_PWM_CHANNEL, speed)
    set_pwm(RIGHT_PWM_CHANNEL, speed)


def turn_right(speed=DRIVE_SPEED):

    gpio_write(IN1, True)
    gpio_write(IN2, False)

    gpio_write(IN3, False)
    gpio_write(IN4, True)

    set_pwm(LEFT_PWM_CHANNEL, speed)
    set_pwm(RIGHT_PWM_CHANNEL, speed)


# ==========================================================
# ENCODER CLASS
# ==========================================================

class Encoder:

    def __init__(
        self,
        chip_a,
        line_a,
        chip_b,
        line_b
    ):

        self.count = 0

        self.line_a = line_a
        self.line_b = line_b

        self.request_a = gpiod.request_lines(

            chip_a,

            consumer="encoder_a",

            config={
                line_a: gpiod.LineSettings(
                    direction=gpiod.line.Direction.INPUT
                )
            }

        )

        self.request_b = gpiod.request_lines(

            chip_b,

            consumer="encoder_b",

            config={
                line_b: gpiod.LineSettings(
                    direction=gpiod.line.Direction.INPUT
                )
            }

        )

        self.last_a = self.request_a.get_value(
            self.line_a
        )

    def update(self):

        a = self.request_a.get_value(
            self.line_a
        )

        b = self.request_b.get_value(
            self.line_b
        )

        if a != self.last_a:

            if a != b:
                self.count += 1
            else:
                self.count -= 1

        self.last_a = a

    def reset(self):

        self.count = 0


# ==========================================================
# CREATE ENCODERS
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
# ENCODER THREAD
# ==========================================================

encoder_running = True


def encoder_loop():

    global encoder_running

    while encoder_running:

        left_encoder.update()
        right_encoder.update()

        time.sleep(0.001)


encoder_thread = threading.Thread(
    target=encoder_loop,
    daemon=True
)


# ==========================================================
# DISTANCE FUNCTIONS
# ==========================================================

def left_distance():

    return (
        left_encoder.count *
        INCHES_PER_COUNT
    )


def right_distance():

    return (
        right_encoder.count *
        INCHES_PER_COUNT
    )


def average_distance():

    return (
        left_distance() +
        right_distance()
    ) / 2


def reset_encoders():

    left_encoder.reset()
    right_encoder.reset()


# ==========================================================
# KEYBOARD SETUP
# ==========================================================

old_terminal = termios.tcgetattr(
    sys.stdin
)


def keyboard_setup():

    tty.setcbreak(
        sys.stdin.fileno()
    )


def keyboard_restore():

    termios.tcsetattr(
        sys.stdin,
        termios.TCSADRAIN,
        old_terminal
    )


def key_pressed():

    ready, _, _ = select.select(
        [sys.stdin],
        [],
        [],
        0
    )

    if ready:

        return sys.stdin.read(1)

    return None


# ==========================================================
# STATUS DISPLAY
# ==========================================================

def print_status():

    print(
        "\033[2J\033[H",
        end=""
    )

    print("==============================")
    print(" GOOSE RC CAR ")
    print("==============================")
    print()

    print(
        f"Left Encoder : {left_encoder.count}"
    )

    print(
        f"Right Encoder: {right_encoder.count}"
    )

    print()

    print(
        f"Left Distance : {left_distance():.2f} in"
    )

    print(
        f"Right Distance: {right_distance():.2f} in"
    )

    print(
        f"Average Distance: {average_distance():.2f} in"
    )

    print()
    print("Controls")
    print(" W - Forward")
    print(" S - Reverse")
    print(" A - Left")
    print(" D - Right")
    print(" SPACE - Stop")
    print(" R - Reset Encoders")
    print(" Q - Quit")


# ==========================================================
# SHUTDOWN
# ==========================================================

def shutdown():

    global encoder_running

    encoder_running = False

    stop_motor()

    try:
        keyboard_restore()
    except:
        pass

    try:
        pca.deinit()
    except:
        pass

    print("\nProgram stopped.")


# ==========================================================
# MAIN
# ==========================================================

def main():

    global encoder_running

    print("Starting Goose RC Car...")

    stop_motor()

    encoder_thread.start()

    keyboard_setup()

    try:

        while True:

            key = key_pressed()

            if key:

                key = key.lower()

                if key == "w":
                    forward()

                elif key == "s":
                    backward()

                elif key == "a":
                    turn_left()

                elif key == "d":
                    turn_right()

                elif key == " ":
                    stop_motor()

                elif key == "r":
                    reset_encoders()

                elif key == "q":
                    break

            print_status()

            time.sleep(0.05)

    except KeyboardInterrupt:

        pass

    finally:

        shutdown()


# ==========================================================
# RUN PROGRAM
# ==========================================================

if __name__ == "__main__":

    main()
