# Activity 04 - Configure the ROCK 5C and Drive with the Keyboard

## Mission

Install the ROCK 5C operating system and motor-control software, discover the channel and direction of each motor, then drive GooseBot with `W`, `A`, `S`, and `D` locally and from a laptop over SSH.

## Why It Matters

The autonomous controller ultimately sends the same left- and right-side motor commands used here. Mapping the physical wiring into software is therefore the bridge between the chassis and every later autonomy algorithm. Remote access also allows the robot to operate without a monitor, mouse, or keyboard attached.

## Success Criteria

- The ROCK 5C boots and joins an approved network.
- I2C8-M2 is enabled and Python can import the hardware libraries.
- `mapping.py` identifies all four channel pairs and directions.
- `keyboard_control.py` produces correct forward, reverse, left, right, and stop behavior.
- Keyboard control works through SSH from the development laptop.
- The robot is tested on a stand before any floor test.

## Prerequisites and Materials

- Complete [Activity 03](../03_mounting_and_wiring/README.md).
- ROCK 5C Lite, microSD card, approved power adapter, PCA9685, two wired L298N boards, display/keyboard for initial setup, and laptop.
- Obtain current school-network and VPN instructions privately from the instructor. No private credential belongs in this repository.

## Safety Gate

For every new wiring or software configuration:

1. disconnect power before changing wires;
2. place GooseBot on a stable stand with every wheel clear;
3. use the approved ROCK 5C adapter and bench motor supply first;
4. verify ROCK 5C ground, PCA9685 ground, and L298N grounds are common; and
5. keep the DC-DC converter and LiPo disconnected until the bench configuration passes.

## Part 1 - Install the ROCK 5C Operating System

1. Follow Radxa's [ROCK 5C microSD installation guide](https://docs.radxa.com/en/rock5/rock5c/getting-started/install-os/boot-from-sd-card) and use the instructor-approved desktop image.
2. Write the image with balenaEtcher or the tool identified by Radxa.
3. Insert the microSD card and follow the [ROCK 5C quick-start guide](https://docs.radxa.com/en/rock5/rock5c/getting-started/quick-start).
4. Sign in with the credentials supplied for the selected image. Change default passwords when instructed.
5. Connect to an approved network and record the ROCK 5C IPv4 address. Do not place network passwords in code, screenshots, or GitHub.

## Part 2 - Connect the PCA9685

With all power disconnected, follow the [Activity 03 wiring diagram](../03_mounting_and_wiring/assets/goose_wiring.png):

- ROCK 5C I2C SDA/SCL connect to PCA9685 SDA/SCL;
- ROCK 5C and PCA9685 share the required logic supply and ground;
- PCA9685 channels 0-7 connect to the eight L298N direction inputs; and
- ROCK 5C, PCA9685, and both L298N boards share ground.

Recheck the exact ROCK 5C pinout before energizing. A header position is not automatically a safe 5 V, 3.3 V, ground, SDA, or SCL connection.

## Part 3 - Enable I2C8-M2

Open a ROCK 5C terminal:

```bash
sudo rsetup
```

Use the menus to select **Overlays** -> **Manage overlays** -> **Enable I2C8-M2**. Use Space to select it, Enter to apply it, and Esc to leave the utility. Reboot:

```bash
sudo reboot
```

System updates may disable or replace an overlay configuration. If I2C later disappears, check this setting again.

## Part 4 - Clone the Repository and Install Packages

On the ROCK 5C:

```bash
sudo apt update
sudo apt install git python3-libgpiod python3-venv
git clone https://github.com/hoanbklucky/goose.git
python3 -m venv ~/goose-motor-venv --system-site-packages
source ~/goose-motor-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install adafruit-blinka adafruit-circuitpython-pca9685
python -c "import board, busio; from adafruit_pca9685 import PCA9685; print('Motor libraries ready')"
```

If the repository already exists, do not clone it again:

```bash
cd ~/goose
git status --short
git pull --rebase
```

Do not pull over uncommitted student changes without backing them up.

## Part 5 - Map the Motors

Keep the wheels off the table:

```bash
source ~/goose-motor-venv/bin/activate
cd ~/goose/04_motor_test
python mapping.py
```

Press `1`, `2`, `3`, and `4` one at a time. Each key activates one PCA9685 channel pair while the key is held. Press `x` to exit.

Record the result:

| Key | Channels | Physical motor | Observed direction | Correct `(in1, in2)` for forward |
|---:|---|---|---|---|
| 1 | 0, 1 | | | |
| 2 | 2, 3 | | | |
| 3 | 4, 5 | | | |
| 4 | 6, 7 | | | |

If a channel pair turns the correct motor backward, reverse the two channel numbers when you construct that `Motor` in `keyboard_control.py`.

## Part 6 - Configure and Test Keyboard Control

Open `keyboard_control.py` and edit the four named motor assignments:

```python
motor_fl = Motor(pca, in1_channel=7, in2_channel=6)
motor_fr = Motor(pca, in1_channel=5, in2_channel=4)
motor_rl = Motor(pca, in1_channel=2, in2_channel=3)
motor_rr = Motor(pca, in1_channel=0, in2_channel=1)
```

The values above are an example, not a universal wiring map. Use your table from Part 5. Save the file, keep GooseBot lifted, and run:

```bash
python keyboard_control.py
```

| Key | Expected action |
|---|---|
| `W` | all wheels drive forward |
| `S` | all wheels drive backward |
| `A` | left side reverses and right side advances |
| `D` | right side reverses and left side advances |
| `X` | exit and stop all motors |

Press Ctrl+C if an unexpected motion occurs. Disconnect motor power before changing channel assignments.

## Part 7 - Configure SSH and Test from the Laptop

Use Radxa's [network and remote-access guide](https://docs.radxa.com/en/rock5/rock5c/getting-started/basic-software-conf) to enable SSH. The laptop and ROCK 5C must be able to reach each other through an approved local network or school VPN.

From the laptop, replace the example address with the ROCK 5C IPv4 address:

```bash
ssh radxa@192.0.2.10
source ~/goose-motor-venv/bin/activate
cd ~/goose/04_motor_test
python keyboard_control.py
```

Complete one remote test with the wheels lifted. Only after all directions and stop behavior pass may you place GooseBot in a clear floor area for a slow driving test.

## Part 8 - Progress to Mobile Power

Use this order and obtain instructor approval at each gate:

1. ROCK 5C adapter + current-limited bench supply for motors.
2. Instructor-approved bench supply arrangement for the complete robot.
3. Fully charged, inspected LiPo + previously measured DC-DC converter.
4. Floor test with a spotter and immediate power-disconnect access.

Do not improvise by paralleling bench-supply channels. Use that mode only when the exact supply documentation supports it and the instructor has approved the connections.

## Command Breakdown

| Command | Meaning |
|---|---|
| `sudo apt update` | refreshes the operating system's package index |
| `sudo apt install ...` | installs system packages, including GPIO support and virtual environments |
| `python3 -m venv ... --system-site-packages` | creates an isolated environment that can also see system-installed GPIO packages |
| `source .../bin/activate` | selects that environment for the current shell |
| `python -m pip ...` | installs into the same Python interpreter used to run the scripts |
| `sudo rsetup` | opens Radxa's configuration utility for overlays such as I2C8-M2 |
| `ssh user@address` | opens a terminal session on the ROCK 5C over the network |
| `python mapping.py` | pulses one motor channel pair at a time for identification |
| `python keyboard_control.py` | converts WASD keypresses into left/right motor commands |

## What to Submit

Unless Canvas says otherwise, submit two narrated group videos:

1. **Bench video:** GooseBot lifted, all four wheels responding correctly to laptop keyboard commands over SSH.
2. **Floor video:** GooseBot moving forward, backward, left, and right in a clear area using the laptop keyboard.

Also provide the completed motor-map table and each group member's contribution.

## Troubleshooting

| Problem | Check |
|---|---|
| `Make sure I2C is enabled` or no I2C device | re-enable I2C8-M2 in `rsetup`, reboot, and recheck wiring |
| `import board` fails | activate `~/goose-motor-venv` and reinstall Adafruit Blinka in that environment |
| one motor is reversed | swap only that motor's two channel numbers in the Python configuration |
| forward command spins the robot | verify FL/FR/RL/RR assignments and retest one motor at a time |
| keys do nothing over SSH | click the terminal, use lowercase keys, and confirm the program still owns the terminal |
| ROCK 5C resets when motors start | stop; the supply is sagging or current-limiting, or grounds/power paths are incorrect |
| network address changes | check the ROCK 5C network details again or ask about an approved address reservation |

## Next Activity

Continue in student order to [Activity 07 - Create and Label a Dataset](../07_dataset_creation/README.md).
