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
- The group can identify whether it is editing the laptop clone or `~/goose` on the ROCK 5C.
- VS Code Remote SSH opens the ROCK 5C repository and its remote terminal.
- The robot is tested on a stand before any floor test.

## Prerequisites and Materials

- Complete [Activity 03](../03_mounting_and_wiring/README.md).
- Install VS Code Remote - SSH and read [Work on GooseBot Code - Three Editing Methods](../00_set_up/REMOTE_DEVELOPMENT.md).
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

## Part 2 - Verify the Completed Activity 03 Wiring

Do not rebuild the wiring from memory. With every power source disconnected, reopen [Activity 03 Part 6](../03_mounting_and_wiring/README.md#part-6---complete-the-integrated-wiring) and its full-resolution diagram, then verify:

- ROCK 5C physical pin 1 -> PCA9685 `VCC` (3.3 V logic);
- physical pin 3 -> `SDA`, pin 5 -> `SCL`, and pin 9 -> `GND`;
- PCA9685 channel pairs CH0/1, CH2/3, CH4/5, and CH6/7 reach the four labeled L298N input pairs;
- both L298N grounds, PCA9685 ground, ROCK 5C ground, and motor-supply negative are common;
- PCA9685 `V+` is unused; and
- neither L298N 5 V terminal powers the ROCK 5C or PCA9685 logic;
- the ROCK 5C has exactly one power source connected; and
- the dedicated mobile converter is set to 5.0 V, is rated for at least 3 A continuous output, and is not paralleled with either L298N regulator.

For the first test, keep the XT60/battery path disconnected. Power the ROCK 5C from its approved adapter and leave the current-limited motor supply output off until I2C and software initialization pass. In the later mobile configuration, disconnect the adapter before connecting the verified 5.0 V converter. See [Activity 03 Part 6D](../03_mounting_and_wiring/README.md#6d---complete-power-and-ground-wiring) for the one-source power rule and its rationale.

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

For each key, record three things:

1. **Physical motor:** which wheel turns: front left (`FL`), front right (`FR`), rear left (`RL`), or rear right (`RR`).
2. **Observed direction:** whether that wheel drives the robot forward or backward. "Forward" means the robot would move camera-first if all four wheels turned that way.
3. **Channel order for forward:** the two channel numbers in the order that must be passed to `Motor(pca, in1_channel, in2_channel)`. The first number receives PWM when the program commands a positive speed.

Use this rule for the final column:

- If the motor moves **forward**, keep the displayed channel order. For channels `0, 1`, record `(0, 1)`.
- If the motor moves **backward**, reverse the displayed channel order. For channels `0, 1`, record `(1, 0)`.

Record your actual results:

| Key | Tested channels | Physical motor (`FL/FR/RL/RR`) | Direction with tested order | Channel order for forward `(in1, in2)` |
|---:|---|---|---|---|
| 1 | 0, 1 | | | |
| 2 | 2, 3 | | | |
| 3 | 4, 5 | | | |
| 4 | 6, 7 | | | |

For example, if key `1` turns the rear-right motor backward, that row should read:

| Key | Tested channels | Physical motor | Direction with tested order | Channel order for forward `(in1, in2)` |
|---:|---|---|---|---|
| 1 | 0, 1 | `RR` | Backward | `(1, 0)` |

This final tuple is the exact channel order to transfer into `keyboard_control.py`.

## Part 6 - Configure and Test Keyboard Control

Open `keyboard_control.py`. Match each physical-motor abbreviation from your Part 5 table to the corresponding variable:

| Table abbreviation | Python variable |
|---|---|
| `FL` | `motor_fl` |
| `FR` | `motor_fr` |
| `RL` | `motor_rl` |
| `RR` | `motor_rr` |

For each variable, copy the two numbers from that motor's **Channel order for forward** tuple. For example, a recorded tuple of `(1, 0)` becomes:

```python
motor_rr = Motor(pca, in1_channel=1, in2_channel=0)
```

The four assignments below illustrate one possible completed motor map:

```python
motor_fl = Motor(pca, in1_channel=7, in2_channel=6)
motor_fr = Motor(pca, in1_channel=5, in2_channel=4)
motor_rl = Motor(pca, in1_channel=2, in2_channel=3)
motor_rr = Motor(pca, in1_channel=0, in2_channel=1)
```

**Do not copy these example numbers unless all four rows match your observations.** Your physical wiring determines the correct motor names and channel order. After transferring all four tuples from your table, save the file, keep GooseBot lifted, and first run the program from a keyboard and terminal connected directly to the ROCK 5C:

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

Confirm forward, backward, left, right, and stop locally before continuing to SSH. Watch the [local keyboard-control demonstration](https://youtu.be/hll0T7G28eo) to see the expected lifted-wheel behavior. Use it as a motion reference; your channel assignments must still come from your own Part 5 motor map.

## Part 7 - Configure SSH and Test from the Laptop

Use the course guide [Work on GooseBot Code - Three Editing Methods](../00_set_up/REMOTE_DEVELOPMENT.md) for the complete direct, terminal SSH + `nano`, and VS Code Remote SSH workflows. Radxa's official [ROCK 5C Quick Setup - SSH](https://docs.radxa.com/en/rock5/rock5c/getting-started/basic-software-conf#ssh) page is the authoritative reference for finding the username/IP address and checking, installing, or enabling the SSH service.

The laptop and ROCK 5C must be able to reach each other through an approved local network or school VPN. If you are off the campus network or the instructor requires it, install [Florida Poly GlobalProtect](https://vpn.floridapoly.edu/global-protect/getsoftwarepage.esp), connect to `vpn.floridapoly.edu`, and sign in with your own university account. Obtain current network instructions privately from the instructor; never copy campus credentials into GitHub. First prove ordinary terminal SSH works; VS Code Remote SSH uses the same underlying connection.

From the laptop, replace the example address with the ROCK 5C IPv4 address:

```bash
ssh radxa@192.0.2.10
hostname
whoami
cd ~/goose
pwd
git status --short
source ~/goose-motor-venv/bin/activate
cd ~/goose/04_motor_test
python keyboard_control.py
```

Confirm that `hostname` identifies the ROCK 5C and `pwd` shows the GooseBot repository. Then complete one remote test with the wheels lifted.

Next, connect using VS Code Remote SSH, open the remote `/home/<username>/goose` folder, and repeat `hostname`, `whoami`, and `pwd` in the VS Code integrated terminal. Edit a file only after the lower-left status bar shows the SSH host. Opening the laptop clone in a normal VS Code window does not edit the code on GooseBot.

Record the lifted-wheel SSH test after all directions and stop behavior pass. Keep GooseBot on the stand until the mobile-power checks in Part 8 also pass.

### Optional - Enable Automatic Login for Headless Starts

Automatic login is optional; SSH itself does not require a desktop session. If the instructor wants GooseBot to reach its desktop automatically after power-up:

1. Follow Radxa's [Auto Login guide](https://docs.radxa.com/en/rock5/rock5b/radxa-os/autologin) for the installed Radxa OS version, or run `sudo rsetup` and select **User Settings** -> **Configure auto login** when that option is available.
2. Reboot and verify that the ROCK 5C reconnects to the approved network and still accepts SSH.
3. If a system update was required, return to Part 3 and confirm that `I2C8-M2` remains enabled before applying motor power.
4. Follow current university IT guidance for saving campus Wi-Fi credentials. Do not enable unencrypted credential storage unless the instructor or IT staff explicitly approves it.

## Part 8 - Test the Complete Power Cable and Move to Battery Power

Steps 2 and 3 use the same completed **power cable**. Only the source connected to the cable changes:

```text
Step 2: approved dual-channel bench supply --> power cable --> both L298N motor-supply inputs
                                                           --> DC-DC input --> 5.0 V --> ROCK 5C

Step 3: LiPo battery -----------------------> same power cable --> same downstream connections
```

The power cable distributes the source voltage to both L298N motor drivers and to the **input** of the DC-DC converter. The converter is the ROCK 5C's only source in Steps 2-4. Its verified 5.0 V output powers the ROCK 5C; the L298N 5 V terminals do not.

Keep every wheel off the table through Steps 1-3, and obtain instructor approval before each transition.

### Step 1 - Prove Control with Separate Supplies

1. Power the ROCK 5C from its approved CanaKit/USB-C adapter.
2. Power the two L298N motor drivers from the current-limited bench supply.
3. Leave the LiPo and the DC-DC converter output disconnected from the ROCK 5C.
4. Complete the local-keyboard and SSH tests. Verify forward, backward, left, right, and stop.

This arrangement separates computer power from motor power and must pass before testing the complete power cable.

### Step 2 - Test the Complete Robot from the Dual Bench Supply

1. Stop the program and switch all bench-supply outputs off.
2. Disconnect the CanaKit/USB-C adapter from the ROCK 5C. Do not leave it connected during this step.
3. Configure the two bench-supply channels using the instructor-approved parallel/current-sharing procedure for the exact laboratory supply. For the supply used in the course demonstration, set both channels to 12.0 V with a 1.5 A current limit before making the approved parallel connection. Do not copy these settings to a different supply without checking its manual. A single 1.5 A channel cannot power the complete robot reliably.
4. Connect the combined bench-supply output to the battery-input end of the completed power cable—the same connector that will receive the LiPo in Step 3.
5. Confirm the cable feeds both L298N motor-supply inputs and the DC-DC converter input. Before connecting the ROCK 5C, verify correct polarity and 5.0 V at the converter's ROCK 5C power connector.
6. Connect the converter output to the ROCK 5C, enable the bench supply, and repeat the lifted-wheel direction and stop tests locally and over SSH.
7. Stop immediately if the ROCK 5C resets, a supply current-limits, the 5.0 V rail sags, or any component becomes hot.

Watch the [dual-channel bench-supply demonstration](https://youtu.be/hSM6TArdIB8) for the intended test arrangement. The video does not replace the instructor's settings or the operating instructions for the exact supply.

### Step 3 - Replace the Bench Supply with the LiPo

1. Stop the program, switch off the bench supply, and disconnect it from the power cable.
2. Confirm the CanaKit/USB-C adapter remains disconnected.
3. Inspect and fully charge the LiPo. Verify its voltage and connector polarity with the instructor.
4. Connect the LiPo to the same power-cable input used by the dual bench supply in Step 2. Do not change the downstream L298N or DC-DC wiring.
5. Confirm that the DC-DC converter still provides 5.0 V to the ROCK 5C, then repeat the complete lifted-wheel direction and stop test.

Compare the setup and behavior with the [LiPo-powered demonstration](https://youtu.be/DrrYp6Q6y8U).

### Step 4 - Perform the Floor Test

After Step 3 passes, move GooseBot to a clear area, begin at low speed, use a spotter, and keep immediate access to the battery disconnect. Demonstrate forward, backward, left, right, and stop as shown in the [remote floor-driving demonstration](https://youtu.be/fNWs14iPDlg).

At every step, keep all control-system grounds common and keep the ROCK 5C on exactly one power source. Do not improvise by paralleling bench-supply channels: use parallel operation only when the exact supply documentation supports it and the instructor has approved the configuration. Never parallel the DC-DC converter with either L298N 5 V regulator; see [Activity 03 Part 6D](../03_mounting_and_wiring/README.md#6d---complete-power-and-ground-wiring).

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
| `hostname` / `whoami` / `pwd` | proves which computer, account, and folder are active |
| `nano file.py` | edits a file from either the local ROCK 5C terminal or an SSH terminal |
| `python mapping.py` | pulses one motor channel pair at a time for identification |
| `python keyboard_control.py` | converts WASD keypresses into left/right motor commands |

## What to Submit

Unless Canvas says otherwise, submit two narrated group videos:

1. **Bench video:** GooseBot lifted, all four wheels responding correctly to laptop keyboard commands over SSH. Narrate the power arrangement and demonstrate stop behavior.
2. **Floor video:** GooseBot moving forward, backward, left, and right in a clear area using the laptop keyboard. Narrate what is happening and demonstrate stop behavior.

Also provide the completed motor-map table, each group member's contribution, and one screenshot showing the VS Code SSH host indicator plus remote terminal output from `hostname`, `whoami`, and `pwd`. Do not expose a password, private key, or campus credential.

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
| edited file does not change robot behavior | run `hostname` and `pwd`; verify that you edited `~/goose` on the ROCK 5C rather than the laptop clone |
| VS Code opens a local folder | reconnect with **Remote-SSH: Connect to Host...**, confirm the SSH status indicator, and open the remote GooseBot folder |

## Next Activity

Continue in student order to [Activity 07 - Create and Label a Dataset](../07_dataset_creation/README.md).
