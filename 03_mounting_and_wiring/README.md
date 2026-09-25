# Activity 03 - Mount, Wire, and Test the Drive Hardware

## Mission

Mount the two L298N motor drivers, connect all four motors, verify direction and PWM response, prepare the regulated power harness, and complete the unpowered ROCK 5C-PCA9685-L298N wiring needed for Activity 04.

## Why It Matters

This activity separates electrical and mechanical problems from software problems. If every motor responds correctly to a known benchtop signal, later PCA9685 and Python tests start from verified hardware. It also establishes the common-ground and voltage-regulation practices needed to protect the computer.

## Success Criteria

- Left motors connect to one L298N and right motors to the other.
- Each motor can turn in both directions using the appropriate input pair.
- PWM duty cycle changes motor speed.
- All signal sources share a reference ground.
- The DC-DC converter is adjusted to approximately 5 V before it is allowed near the ROCK 5C.
- ROCK 5C physical pins 1, 3, 5, and 9 connect to the correct PCA9685 logic pins.
- PCA9685 channels 0-7 connect to the four matching L298N direction-input pairs.
- The completed wiring passes an unpowered inspection before Activity 04 begins.

## Prerequisites and Materials

- Completed [Activity 02 chassis](../02_chassis_design/README.md).
- Two L298N boards, PCA9685 board, wiring diagram, multimeter, current-limited bench supply, and function generator.
- Instructor-supervised soldering tools and power-harness components if the battery harness will be assembled.

## Safety Gate

1. Place the robot on a stand so all wheels are clear.
2. Set the bench supply output **off** before wiring.
3. Start with a conservative current limit and raise it only as directed by the instructor.
4. Never change motor or driver wiring while energized.
5. Connect function-generator ground to driver ground before applying its signal.
6. Leave the L298N `ENA` and `ENB` jumpers installed for the input-PWM test described here.
7. Do not energize the integrated ROCK 5C/motor system or run motor software in this activity. Part 6 is wired with every power source disconnected; Activity 04 performs the staged power-up.

## Part 1 - Mount and Wire the Motor Drivers

1. Install the required chassis inserts and mount one L298N on the left and one on the right.
2. Connect the front-left and rear-left motors to the two output pairs of the left driver.
3. Connect the front-right and rear-right motors to the two output pairs of the right driver.
4. Route and secure wires so they cannot enter a wheel.
5. Connect both driver grounds together. All future control boards must share this signal reference.

![Four motors connected to two drivers](assets/build_steps/02_motor_drivers_connected.jpg)

## Part 2 - Verify Each Bare Motor

With instructor approval, briefly apply the rated motor-test voltage directly to one motor at a time. Reverse the two leads and confirm the direction reverses. Do not stall a wheel or hold power on longer than needed for identification.

![Direct motor test](assets/build_steps/01_direct_motor_test.jpg)

Record the result:

| Motor | Lead polarity that turns the wheel forward | Pass? |
|---|---|---|
| Front left | | |
| Rear left | | |
| Front right | | |
| Rear right | | |

"Forward" means the robot would move camera-first if all four wheels used that direction.

## Part 3 - Test Direction Through the L298N

For each motor input pair, keep one input low and set the other high. Then swap the levels.

| Input 1 | Input 2 | Expected motor state |
|---:|---:|---|
| 0 | 0 | coast/stop |
| 1 | 0 | one direction |
| 0 | 1 | opposite direction |
| 1 | 1 | brake/stop behavior depends on the board |

Use logic levels appropriate for the board. Do not connect an unknown voltage to a signal input.

![Static logic-level motor test](assets/build_steps/03_logic_level_test.jpg)

## Part 4 - Test PWM Speed Control

1. Keep one input of a motor pair at ground.
2. Connect the function-generator signal to the other input and its ground to L298N ground.
3. Use a logic-level square wave. Begin at 0% duty cycle and a moderate frequency approved by the instructor.
4. Increase duty cycle gradually and observe speed.
5. Repeat for all four motors, switching power off before moving the probe.
6. Confirm that reversing which input receives PWM reverses the motor direction.

![Function-generator PWM test](assets/build_steps/04_pwm_test.jpg)

A reference demonstration is available at [YouTube](https://youtu.be/gxDH4S-0ozU).

## Part 5 - Prepare the Power Harness

Complete this part only under instructor supervision.

1. Solder the required branch wires to the male XT60 connector and protect every joint with heat-shrink.
2. Connect battery/motor voltage only to the **input** side of the buck converter. Observe polarity.
3. With the converter output disconnected from the ROCK 5C, energize the input and measure the output with a multimeter.
4. Adjust the potentiometer until the output is approximately 5 V.
5. Switch power off, verify the reading falls, re-energize, and verify the 5 V setting again.
6. Insulate the converter without creating an electrical short or blocking necessary heat dissipation.
7. Label the input, output, positive, and ground conductors.

![Preparing the XT60 harness](assets/build_steps/05_xt60_harness.jpg)

![Wiring the buck converter](assets/build_steps/06_buck_converter_wiring.jpg)

![Adjusting and measuring the output](assets/build_steps/07_adjust_buck_converter.jpg)

![Insulated converter](assets/build_steps/08_insulate_buck_converter.jpg)

**Critical:** never connect the ROCK 5C until the output polarity and approximately 5 V level have been measured at the actual USB-C/power connector.

## Part 6 - Complete the Integrated Wiring

Do this part only after Parts 1-5 pass. Disconnect the bench supply, function generator, battery, ROCK 5C adapter, and XT60 connector before touching any wire. Use the full-resolution diagram as the wiring overview; use the tables below for the exact checked connections.

[Open the full-resolution GooseBot wiring diagram](assets/goose_wiring.png)

![Complete GooseBot wiring diagram](assets/goose_wiring.png)

> **Power-stage warning:** The diagram includes the final battery and DC-DC-converter path. Do not use that mobile-power path for the first Activity 04 test. Initially power the ROCK 5C from its approved adapter and the two L298N motor drivers from a current-limited bench supply. The signal wiring and common ground remain the same.

> **About the diagram's 5.2 V label:** It records a prototype setting intended to compensate for cable drop. Radxa specifies a 5 V input for the ROCK 5C. Use approximately 5.0 V measured at the actual USB-C connector unless the instructor explicitly approves a measured 5.2 V setting for the exact converter and cable. Never adjust the converter while it is connected to the ROCK 5C.

### 6A - Return the Drivers to Their Final Input Configuration

1. Remove every function-generator lead and temporary logic-level jumper.
2. Keep the L298N `ENA` and `ENB` enable jumpers installed. The course code applies PWM to the direction inputs through the PCA9685.
3. Confirm each motor remains on the L298N output pair that passed Parts 2-4.
4. Use the L298N silkscreen to identify which input pair controls each output pair. On the common module, `IN1/IN2` control one motor output and `IN3/IN4` control the other; follow the labels on the actual board.

### 6B - Connect ROCK 5C I2C to the PCA9685

Orient the ROCK 5C header from its pin-1 marking; do not count pins from the photograph. Make these four logic-side connections:

| ROCK 5C physical pin | Function | PCA9685 logic pin |
|---:|---|---|
| 1 | 3.3 V | `VCC` |
| 3 | I2C8 SDA | `SDA` |
| 5 | I2C8 SCL | `SCL` |
| 9 | ground | `GND` |

The PCA9685 `VCC` pin is the 3.3 V logic supply. Leave the PCA9685 `V+` screw terminal/servo-power rail disconnected; it is not needed for the L298N input signals. Never connect a ROCK 5C GPIO or I2C pin to 5 V.

Radxa's official [ROCK 5C 40-pin I2C test](https://docs.radxa.com/en/rock5/rock5c/getting-started/interface-usage/pin-40-test#i2c) shows the same physical-pin mapping and the `I2C8-M2` overlay used in Activity 04.

### 6C - Connect PCA9685 Channels to the L298N Inputs

For each PCA9685 channel, use only its PWM/signal pin. Do not connect the channel's adjacent `V+` pin to an L298N input.

| Motor | PCA9685 signal channels | L298N destination |
|---|---:|---|
| Front left | CH0 and CH1 | the two direction inputs controlling the front-left motor output |
| Rear left | CH2 and CH3 | the two direction inputs controlling the rear-left motor output |
| Rear right | CH4 and CH5 | the two direction inputs controlling the rear-right motor output |
| Front right | CH6 and CH7 | the two direction inputs controlling the front-right motor output |

The order within a pair determines the sign of positive speed. Do not rewire a pair merely because a wheel initially turns backward; Activity 04 records the mapping and corrects direction in software after one-motor-at-a-time testing.

### 6D - Complete Power and Ground Wiring

1. Connect the positive motor-supply branch to the motor-voltage input on both L298N boards.
2. Connect the motor-supply negative terminal to both L298N grounds.
3. Join ROCK 5C ground, PCA9685 ground, both L298N grounds, and motor-supply negative into one common reference.
4. Leave each L298N module's 5 V terminal in the instructor-approved board configuration. **Do not use an L298N 5 V terminal to power the ROCK 5C or PCA9685 `VCC`.**
5. For the later mobile configuration only, the XT60 positive and negative branches feed the motor drivers and the input of the DC-DC converter. The converter's verified output feeds the dedicated ROCK 5C power lead.
6. Leave the XT60 connector unplugged and the ROCK 5C power lead disconnected until the instructor inspection in Part 7 and the staged power-up in Activity 04.

Route signal wires separately from wheel paths and exposed motor terminals. Add strain relief so a cable cannot pull a jumper off the ROCK 5C or PCA9685 header.

## Part 7 - Inspect the Completed Wiring Before Power-Up

With every power source still disconnected, have a second group member trace each connection aloud from source to destination while another member checks the diagram and tables.

Complete this handoff checklist:

- [ ] front-left, rear-left, rear-right, and front-right motor output pairs are labeled;
- [ ] PCA9685 pairs are CH0/1, CH2/3, CH4/5, and CH6/7 in that order;
- [ ] ROCK 5C pin 1 goes to PCA9685 `VCC`, pin 3 to `SDA`, pin 5 to `SCL`, and pin 9 to `GND`;
- [ ] PCA9685 `V+` is not connected to a ROCK 5C GPIO or L298N input;
- [ ] both L298N grounds, PCA9685 ground, ROCK 5C ground, and motor-supply negative are common;
- [ ] no L298N 5 V terminal powers the ROCK 5C or PCA9685 logic;
- [ ] the DC-DC output polarity and approximately 5 V setting were measured while disconnected from the ROCK 5C;
- [ ] no bare conductor, loose screw-terminal strand, or wire can contact a wheel or neighboring terminal;
- [ ] `ENA` and `ENB` jumpers are installed on both L298N modules; and
- [ ] the instructor has approved the unpowered wiring for staged power-up.

Do not continue to Activity 04 until every box passes. Activity 04 first boots the ROCK 5C from its approved adapter with motor power off, verifies I2C, and only then enables current-limited motor power.

## Command Breakdown

No shell command is required. In this activity, the important control terms are:

| Term | Meaning |
|---|---|
| PWM frequency | number of square-wave cycles per second |
| duty cycle | fraction of each cycle for which the signal is high |
| common ground | shared zero-volt reference used to interpret control signals |
| H-bridge | switching circuit that applies either polarity across a DC motor |
| current limit | maximum current the bench supply will deliver before reducing voltage |
| `VCC` | PCA9685 3.3 V logic supply from ROCK 5C physical pin 1 |
| `V+` | separate PCA9685 servo-power rail; unused in this motor-driver configuration |
| SDA / SCL | I2C data and clock signals on ROCK 5C physical pins 3 and 5 |

## What to Submit

Unless Canvas says otherwise, submit one narrated group video that shows:

- the robot safely lifted with all four wheels clear;
- the wiring and shared ground;
- each of the four motors responding;
- at least two PWM duty cycles that visibly produce different speeds; and
- a clear, powered-off view of the completed ROCK 5C-PCA9685-L298N wiring compared with the full diagram;
- the completed Part 7 inspection checklist; and
- each group member's contribution.

Do not demonstrate by holding a powered robot in your hands.

## Troubleshooting

| Problem | Check |
|---|---|
| motor never turns | output power off, current limit too low, enable jumper missing, loose terminal, wrong output pair, or damaged motor |
| motor turns only one direction | inspect both input wires and test each input independently |
| PWM has no effect | verify square-wave output, amplitude, duty cycle, probe ground, and selected input |
| bench supply immediately current-limits | power off and inspect for shorts or reversed wiring |
| left/right direction differs | record it now; Activity 04 maps software direction per motor |
| converter cannot reach 5 V | confirm input/output sides and adjustment direction; disconnect it and ask the instructor |
| unsure which PCA9685 pin is signal | stop and read the board labels; use the PWM/signal row, not the adjacent `V+` row |
| I2C wires do not match the table | disconnect all power and correct the physical-pin mapping before Activity 04 |
| continuity test suggests motor positive is shorted to ground | do not apply power; inspect terminal strands, converter polarity, and both driver boards |

## Next Activity

After the Part 7 inspection passes, continue to [Activity 04 - ROCK 5C Motor Mapping and Keyboard Control](../04_motor_test/README.md).
