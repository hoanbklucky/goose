# Activity 01 - Understand the GooseBot Hardware

## Mission

Identify the major GooseBot subsystems, confirm that your group has the required parts, and explain how power, computation, sensing, and actuation work together.

## Why It Matters

An autonomous robot is a system, not just a computer attached to motors. A wiring error, undersized power source, unsuitable camera, or missing interface board can stop every later software activity. Understanding the architecture makes troubleshooting faster and safer.

## Success Criteria

- Every physical part is matched to an entry in the bill of materials.
- You can point out the high-voltage motor-power path and the regulated 5 V computer-power path.
- You can explain the roles of the ROCK 5C, PCA9685, L298N drivers, motors, camera, and battery.
- Any missing, substituted, or damaged part is recorded before assembly begins.

## System Architecture

| Subsystem | GooseBot component | Engineering role |
|---|---|---|
| Compute | Radxa ROCK 5C Lite | runs Linux, Python, computer vision, and the autonomy program |
| Perception | USB wide-angle webcam | supplies road and object images |
| Low-level command interface | PCA9685 I2C-to-PWM board | produces repeatable PWM signals without software timing loops |
| Motor power stage | two L298N H-bridge boards | switches motor voltage and direction from low-power control signals |
| Actuation | four geared DC motors and wheels | produces forward motion and skid-steer turning |
| Energy | 3S LiPo battery or current-limited bench supply | powers the drive system |
| Regulation | adjustable DC-DC buck converter | reduces battery voltage to approximately 5 V for the ROCK 5C |
| Structure | 3D-printed chassis and camera mount | locates and protects the hardware |
| Optional ranging | time-of-flight sensors | supports future proximity and obstacle experiments |

## Design Requirements

The selected platform should be inexpensive, reproducible on an ordinary 3D printer, repairable, and capable of real-time vision. The ROCK 5C Lite provides Wi-Fi, USB, GPIO/I2C, expandable storage, and a Rockchip NPU. The NPU is important because later activities move YOLO inference away from the CPU.

## Bill of Materials

Prices change; treat the values below as historical planning estimates rather than current quotations.

| Category | Item | Notes | Reference source |
|---|---|---|---|
| Compute | Radxa ROCK 5C Lite | 4 GB model used in the reference build | [Example](https://www.amazon.com/dp/B0CYY1R9ZH) |
| Storage | compatible microSD card | capacity sufficient for the OS, packages, and model files | obtain locally |
| Drive | four geared DC motors and wheels | often sold as a kit with basic driver boards | [Example](https://www.amazon.com/dp/B08JLYY77W) |
| Motor drivers | two L298N modules | one board controls two motors | included in some kits |
| Camera | USB webcam | wide field of view is preferred | [Example](https://www.amazon.com/dp/B0F2Z2DXW3) |
| PWM interface | PCA9685 board | I2C, 16-channel, 12-bit PWM | [Example](https://www.amazon.com/dp/B0CNVBWX2M) |
| Battery | 3S LiPo | use only with a compatible balance charger and instructor approval | [Example](https://www.amazon.com/dp/B07MQT6YJN) |
| Regulator | adjustable DC-DC buck converter | must be adjusted and measured before connecting the SBC | [Example](https://www.amazon.com/dp/B01MQGMOKI) |
| Fasteners | M2 screws and heat-set inserts | use lengths appropriate to the printed parts | [Inserts](https://www.amazon.com/dp/B088QJG676) |
| Fabrication | printed chassis and camera mount | CAD files are in Activity 02 | supplied in this repository |
| Wiring | stranded wire, jumpers, XT60 connector, heat-shrink | color-code power and ground consistently | obtain locally |

Your instructor may provide equivalent components. Do not substitute a power component based only on connector shape; verify voltage, polarity, and current capability.

## Guided Activity

1. Lay out all components with power disconnected and the LiPo stored safely.
2. Match each item to the table above.
3. Inspect boards for cracks, bent pins, loose terminals, or exposed conductors.
4. Trace the intended signal flow:

   ```text
   camera -> ROCK 5C -> I2C -> PCA9685 -> L298N inputs -> motors
   ```

5. Trace the two power paths:

   ```text
   battery/bench supply -> L298N motor supply
   battery/bench supply -> DC-DC converter -> approximately 5 V -> ROCK 5C
   ```

6. Confirm that all controller and driver grounds will be common while their required supply voltages remain distinct.
7. Record substitutions and ask the instructor to approve uncertain power or driver parts before assembly.

## Command Breakdown

This is a planning and inspection activity; no terminal command is required. The important "language" here is the block diagram: arrows describe the direction of information or power, not a physical instruction to connect every listed terminal directly.

## What to Submit

Unless Canvas says otherwise, submit:

- one labeled photograph of the group's parts;
- a short table identifying missing or substituted components; and
- a short explanation of why the ROCK 5C cannot be connected directly to the 3S battery output.

## Troubleshooting

| Question | Action |
|---|---|
| a component does not match the photo | compare its datasheet pinout and ratings; do not assume clone boards are identical |
| a connector fits but voltage is unknown | leave it disconnected and measure or consult the datasheet |
| the exact linked product is unavailable | select an equivalent only after checking voltage, current, interfaces, dimensions, and pinout |
| a LiPo looks swollen or damaged | do not use or charge it; notify the instructor immediately |

## Next Activity

Continue to [Activity 02 - Chassis Assembly](../02_chassis_design/README.md).
