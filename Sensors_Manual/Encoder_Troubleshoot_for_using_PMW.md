# PCA9685 Motor Controller Setup (Rock 5C)

This guide explains how to connect and test the PCA9685 PWM controller on the Radxa ROCK 5C.

The PCA9685 communicates using I2C.

---

# 1. Wiring

## ROCK 5C → PCA9685

| ROCK 5C Pin | Function | PCA9685 Pin |
|---|---|---|
| Pin 1 | 3.3V | VCC |
| Pin 9 | GND | GND |
| Pin 3 | I2C SDA | SDA |
| Pin 5 | I2C SCL | SCL |

Example:

```
ROCK 5C              PCA9685

Pin 3  SDA  -------> SDA

Pin 5  SCL  -------> SCL

Pin 1  3.3V -------> VCC

Pin 9  GND  -------> GND
```

---

# 2. Enable I2C

Install I2C tools:

```bash
sudo apt update
sudo apt install i2c-tools
```

Check available I2C buses:

```bash
ls /dev/i2c*
```

Example:

```
/dev/i2c-0
/dev/i2c-2
/dev/i2c-6
/dev/i2c-7
```

---

# 3. Find PCA9685 Address

The default PCA9685 address is:

```
0x40
```

Run:

```bash
sudo i2cdetect -y 6
```

If nothing appears, try:

```bash
sudo i2cdetect -y 0
sudo i2cdetect -y 2
sudo i2cdetect -y 7
sudo i2cdetect -y 8
sudo i2cdetect -y 9
```

Successful output:

```
     0 1 2 3 4 5 6 7 8 9 a b c d e f

40: 40
```

This confirms the PCA9685 is connected.

If for any reason you cannot find this 40, it means that it's hiding at another I2C port and you need to preform sudo rsetup --> Overlays --> Manage overlay --> and enable a different I2C (space key, dont enable all just one that you need). By my test its ENABLE I2C8-M2. It can be different so find the one that has the 40, then refer to that.
---

# 4. Install Python Libraries

Activate your environment:

```bash
cd ~/goose
source venv/bin/activate
```

Install libraries:

```bash
pip install adafruit-circuitpython-pca9685
pip install adafruit-blinka
```

---

# 5. Test PCA9685

Create:

```bash
nano pca_test.py
```

Paste:

```python
import board
import busio
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(board.SCL, board.SDA)

pca = PCA9685(i2c)

pca.frequency = 100

print("PCA9685 detected!")

pca.deinit()
```

Run:

```bash
python pca_test.py
```

Expected:

```
PCA9685 detected!
```

---

# Troubleshooting

## PCA9685 not detected

Check:

1. SDA and SCL are not swapped.

Correct:

```
Pin 3 → SDA
Pin 5 → SCL
```

2. Check ground connection.

Both devices must share GND.

3. Check I2C address:

```bash
sudo i2cdetect -y <bus>
```

Expected:

```
40
```

---

## Motors do not move

Check:

- PCA9685 is detected
- Motor driver has external motor power
- Motor driver GND connects to ROCK 5C GND
- PWM channels match the code

---

## Current Motor Setup

PCA9685 Channels:

| Motor | IN1 | IN2 |
|-|-|-|
| Front Left | 0 | 1 |
| Rear Left | 2 | 3 |
| Rear Right | 4 | 5 |
| Front Right | 6 | 7 |

---

# Final System

```
ROCK 5C

I2C
 |
 |
PCA9685
 |
 |
PWM
 |
 |
Motor Driver
 |
 |
DC Encoder Motors


GPIO
 |
 |
Wheel Encoders
```

The encoder signals are separate from I2C.
