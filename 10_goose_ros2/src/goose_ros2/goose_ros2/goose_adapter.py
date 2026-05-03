# goose_adapter.py

import board
import busio
from adafruit_pca9685 import PCA9685

MIN_MOTOR_POWER = 0.07


class Motor:
    def __init__(self, pca, in1, in2):
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


i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 100

left_motors = [Motor(pca, 7, 6), Motor(pca, 2, 3)]
right_motors = [Motor(pca, 5, 4), Motor(pca, 0, 1)]


def set_drive(forward, steer):
    left = forward + steer
    right = forward - steer

    for motor in left_motors:
        motor.set_speed(left)

    for motor in right_motors:
        motor.set_speed(right)
