# HC-SR04 Ultrasonic Sensor (Rock 5C)

## Hardware

**Sensor:** HC-SR04

### Wiring

| HC-SR04 | Rock 5C Physical Pin |
|----------|----------------------|
| VCC | 5V |
| GND | GND |
| TRIG | Pin 36 |
| ECHO | Pin 38 (through a voltage divider) |

### GPIO Mapping

| Physical Pin | gpiochip | Line | Direction |
|--------------|----------|------|-----------|
| Pin 36 | gpiochip4 | 2 | Output (TRIG) |
| Pin 38 | gpiochip4 | 5 | Input (ECHO) |

> **Warning**
>
> The HC-SR04 ECHO pin outputs **5 V**. The Rock 5C GPIO pins are **3.3 V only**.
>
> Use a voltage divider (for example, 1 kΩ and 2 kΩ resistors) or a 3.3 V logic level shifter before connecting ECHO to the Rock 5C.

---

## Verify GPIO

```bash
gpioinfo | grep -B5 -A5 "PIN_36"
gpioinfo | grep -B5 -A5 "PIN_38"
```

Expected output:

```text
gpiochip4 - 32 lines:
    line 2: "PIN_36"
    line 5: "PIN_38"
```

---

## Python Test Program

```python
import time
import gpiod

GPIO_CHIP = "/dev/gpiochip4"

TRIG_LINE = 2
ECHO_LINE = 5

chip = gpiod.Chip(GPIO_CHIP)

trig = chip.get_line(TRIG_LINE)
echo = chip.get_line(ECHO_LINE)

trig.request(
    consumer="ultrasonic_trig",
    type=gpiod.LINE_REQ_DIR_OUT,
    default_vals=[0]
)

echo.request(
    consumer="ultrasonic_echo",
    type=gpiod.LINE_REQ_DIR_IN
)

def measure_distance():

    trig.set_value(0)
    time.sleep(0.000005)

    trig.set_value(1)
    time.sleep(0.00001)
    trig.set_value(0)

    timeout = time.time() + 0.05

    while echo.get_value() == 0:
        pulse_start = time.time()
        if pulse_start > timeout:
            return None

    while echo.get_value() == 1:
        pulse_end = time.time()
        if pulse_end > timeout:
            return None

    pulse_duration = pulse_end - pulse_start

    distance_cm = pulse_duration * 34300 / 2

    return distance_cm

print("HC-SR04 Test")
print("Press Ctrl+C to quit.\n")

try:
    while True:

        distance = measure_distance()

        if distance is None:
            print("No echo")
        else:
            print(f"Distance: {distance:.2f} cm")

        time.sleep(0.2)

except KeyboardInterrupt:
    pass

finally:
    trig.release()
    echo.release()
```

---

## Run

```bash
sudo python3 ultrasonic_test.py
```

---

## Expected Output

```text
HC-SR04 Test

Distance: 152.31 cm
Distance: 151.98 cm
Distance: 152.12 cm
```

---

## Troubleshooting

### Always prints "No echo"

- Verify VCC is connected to **5 V**.
- Verify GND is connected.
- Verify TRIG is connected to **Physical Pin 36**.
- Verify ECHO is connected to **Physical Pin 38**.
- Verify a voltage divider is installed on the ECHO line.
- Verify the sensor is an HC-SR04.
- Ensure no other program is using gpiochip4 lines 2 or 5.

### Permission denied

Run the script with:

```bash
sudo python3 ultrasonic_test.py
```

### Incorrect readings

- Make sure the sensor has a clear view of an object.
- Keep the target between approximately 2 cm and 400 cm away.
- Avoid soft or angled surfaces, which may not reflect sound back to the sensor.
