#!/usr/bin/env python3

import time
import math
import sys
import threading
import select
import tty
import termios

import gpiod

import board
import busio

from adafruit_pca9685 import PCA9685



# ==========================================================
# ROBOT CONFIGURATION
# ==========================================================


# ----------------------------
# GPIO CHIP
# ----------------------------

GPIO_CHIP = "/dev/gpiochip1"



# ----------------------------
# L298N MOTOR DRIVER GPIO
# ----------------------------
#
# These are GPIO offsets
# NOT physical header pin numbers
#
# Verify with:
# gpioinfo gpiochip1
#

IN1 = 7
IN2 = 6
IN3 = 5
IN4 = 4



# ----------------------------
# PCA9685
# ----------------------------

PWM_FREQUENCY = 1000


LEFT_PWM_CHANNEL = 0
RIGHT_PWM_CHANNEL = 1


MAX_PWM = 4095

DRIVE_SPEED = 2500



# ==========================================================
# PCA9685 INITIALIZATION
# ==========================================================


i2c = busio.I2C(
    board.SCL,
    board.SDA
)


pca = PCA9685(i2c)


pca.frequency = PWM_FREQUENCY



def set_pwm(channel, value):

    if value < 0:
        value = 0

    if value > MAX_PWM:
        value = MAX_PWM


    pca.channels[channel].duty_cycle = value



# ==========================================================
# LIBGPIOD 2.x MOTOR SETUP
# ==========================================================


motor_request = gpiod.request_lines(

    GPIO_CHIP,

    consumer="RC_Car_Motor",

    config={

        IN1:
        gpiod.LineSettings(
            direction=
            gpiod.line.Direction.OUTPUT,

            output_value=
            gpiod.line.Value.INACTIVE
        ),


        IN2:
        gpiod.LineSettings(
            direction=
            gpiod.line.Direction.OUTPUT,

            output_value=
            gpiod.line.Value.INACTIVE
        ),


        IN3:
        gpiod.LineSettings(
            direction=
            gpiod.line.Direction.OUTPUT,

            output_value=
            gpiod.line.Value.INACTIVE
        ),


        IN4:
        gpiod.LineSettings(
            direction=
            gpiod.line.Direction.OUTPUT,

            output_value=
            gpiod.line.Value.INACTIVE
        )

    }
)



def gpio_write(pin, state):

    if state:

        motor_request.set_value(

            pin,

            gpiod.line.Value.ACTIVE

        )

    else:

        motor_request.set_value(

            pin,

            gpiod.line.Value.INACTIVE

        )



# ==========================================================
# BASIC MOTOR FUNCTIONS
# ==========================================================


def stop_motor():

    gpio_write(IN1, False)
    gpio_write(IN2, False)

    gpio_write(IN3, False)
    gpio_write(IN4, False)


    set_pwm(
        LEFT_PWM_CHANNEL,
        0
    )

    set_pwm(
        RIGHT_PWM_CHANNEL,
        0
    )



def forward(speed=DRIVE_SPEED):

    gpio_write(IN1, True)
    gpio_write(IN2, False)

    gpio_write(IN3, True)
    gpio_write(IN4, False)


    set_pwm(
        LEFT_PWM_CHANNEL,
        speed
    )

    set_pwm(
        RIGHT_PWM_CHANNEL,
        speed
    )



def backward(speed=DRIVE_SPEED):

    gpio_write(IN1, False)
    gpio_write(IN2, True)

    gpio_write(IN3, False)
    gpio_write(IN4, True)


    set_pwm(
        LEFT_PWM_CHANNEL,
        speed
    )

    set_pwm(
        RIGHT_PWM_CHANNEL,
        speed
    )



def turn_left(speed=DRIVE_SPEED):

    gpio_write(IN1, False)
    gpio_write(IN2, True)

    gpio_write(IN3, True)
    gpio_write(IN4, False)


    set_pwm(
        LEFT_PWM_CHANNEL,
        speed
    )

    set_pwm(
        RIGHT_PWM_CHANNEL,
        speed
    )



def turn_right(speed=DRIVE_SPEED):

    gpio_write(IN1, True)
    gpio_write(IN2, False)

    gpio_write(IN3, False)
    gpio_write(IN4, True)


    set_pwm(
        LEFT_PWM_CHANNEL,
        speed
    )

    set_pwm(
        RIGHT_PWM_CHANNEL,
        speed
    )



# ==========================================================
# PART 2
# ENCODER SYSTEM (LIBGPIOD 2.x)
# ==========================================================


# ==========================================================
# ENCODER CONFIGURATION
# ==========================================================


LEFT_ENCODER_A = 21
LEFT_ENCODER_B = 22


RIGHT_ENCODER_A = 23
RIGHT_ENCODER_B = 24



# Encoder calibration
# From your previous test

COUNTS_PER_REV = 1092


WHEEL_DIAMETER_IN = 2.5


WHEEL_CIRCUMFERENCE = (
    math.pi *
    WHEEL_DIAMETER_IN
)


INCHES_PER_COUNT = (
    WHEEL_CIRCUMFERENCE /
    COUNTS_PER_REV
)



# ==========================================================
# ENCODER CLASS
# ==========================================================


class Encoder:


    def __init__(
        self,
        pin_a,
        pin_b
    ):


        self.pin_a = pin_a
        self.pin_b = pin_b


        self.count = 0


        self.last_a = 0



        # Request GPIO inputs

        self.request = gpiod.request_lines(

            GPIO_CHIP,

            consumer="RC_Car_Encoder",

            config={


                pin_a:

                gpiod.LineSettings(

                    direction=
                    gpiod.line.Direction.INPUT

                ),



                pin_b:

                gpiod.LineSettings(

                    direction=
                    gpiod.line.Direction.INPUT

                )

            }

        )



        # Initial state

        self.last_a = self.request.get_value(
            self.pin_a
        )




    def update(self):


        a = self.request.get_value(
            self.pin_a
        )


        b = self.request.get_value(
            self.pin_b
        )



        # Quadrature decoding

        if a != self.last_a:


            if b != a:

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

    LEFT_ENCODER_A,

    LEFT_ENCODER_B

)



right_encoder = Encoder(

    RIGHT_ENCODER_A,

    RIGHT_ENCODER_B

)




# ==========================================================
# ENCODER UPDATE THREAD
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

        left_distance()

        +

        right_distance()

    ) / 2




def reset_encoders():


    left_encoder.reset()

    right_encoder.reset()




