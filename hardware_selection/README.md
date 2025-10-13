# Parameters
The hardware for GooseBot is selected to meet the following parameters.

- Low cost - As this kit is to be used by students and educators, the complete bill of materials should not exceed $100 USD at the time of writing this document. As some components will be slightly lower-cost in bulk, I will allow the limit to be exceeded whenever bulk orders are cheaper or there are lower-cost alternatives available.
- Comparable performance to DuckieBot - The DuckieBot is centered around the Nvidia Jetson Nano 4GB. The Nano *was* a capable device in its prime due to its onboard GPU, allowing for acceleration of computer vision processing using CUDA libraries. Today, many more affordable alternatives exist, utlizing Neural Processing Units (NPUs). Likewise, devices with faster processors, more memory, and wider arrays of peripherals are available. At the very least, GooseBot should be able to perform as well as DuckieBot; at best, it will perform far better.
- Up-to-date software - My greatest gripe with the DuckieBot, and with Jetson Nano's in general, is the use of completely obsolete software. Nvidia requires the use of its own customized version of Ubuntu 18.04 on the Jetson Nano as it has not updated the Linux kernel to allow hardware acceleration on its custom Tegra CPU architecture. This makes the development and modification of software on the DuckieBot a collossal pain; my Embedded Control class has spent *weeks* debugging and troubleshooting software that should be nearly plug-and-play.
- Widespread availability - The components selected should be easily purchaseable from reliable distributors such as Mouser and DigiKey. Where this is impractical, the components must be easily substitutable.

# Single-board Computer (SBC)
To meet the *comparable-performance* parameter, the single-board computer selected as the core component of GooseBot should have 
- at least 4GB of RAM (preferably the faster, higher-bandwidth LPDDR5)
- NPU with operating speed of at least 3TOPs
- WiFi to take the place of the external USB WiFi dongle used on the Jetson Nano
- USB ports for peripherals
- MicroSD expandable storage
- Common communication interfaces on GPIOs (I2C, SPI, PWM, Analog, etc.)
- Up-to-date software support (Ubuntu LTS for next two years minimum)

The SBC selected to meet these criteria is the Radxa Rock5c Lite. Its characteristics are given:
- Rockchip RK3582 hexa-core CPU
- Anywhere between 2 and 32GB of LPDDR4x RAM
- MicroSD expandable storage
- 5TOPS NPU
- Identical GPIO as the Raspberry Pi and Jetson Nano
- WiFi and Bluetooth in-built
- USB2 and USB3
- Native support for Ubuntu 20 and 22

The specific model I am using can be found here for $65, with 4GB of RAM.
https://www.amazon.com/Radxa-ROCK-5C-RK3588S2-4GB/dp/B0CYY1R9ZH

# Motors and Wheels
We want a DC motor setup for simple, effective control. Motor+gearbox assemblies almost identical to those onboard the DuckieBot are available in entire kits for <$20. This is the kit I will be using:
https://www.amazon.com/dp/B08JLYY77W

This comes with wheels, motors, gearboxes, and H-bridge motor driver modules.

# Sensors
## Camera
The foremost sensor on the platform is the camera module. Rather than a typical CSI camera module which ranges in cost from $20 to $100, a simple USB webcam with a wide field-of-view can be used, with the same or better optical performance. Furthermore, many USB webcams are coupled with onboard microphones, which enables development of audio processing features. The component selected is this:
https://www.amazon.com/dp/B0F7Y6JLM7

## Time-of-Flight
In addition to the computationally-expensive visual processing system that the robot will use, time-of-flight sensors can be employed at the front and sides of the robot for compact, resource-constrained proximity sensing and obstacle avoidance. Again, these can be found at extremely low costs. This set of three units can be had for just $10.
https://www.amazon.com/dp/B0B6ZT7NRW

# Middleware
For simplified integration of sensors and drive components, it is useful to have a PWM-I2C interface. This way, we can offload the PWM signal generation that will be used to vary speeds of the motors to a designated component, rather than having to consume valuable CPU cycles of the SBC on such a tedious, repetitive tasks. Furthermore, servos and additional PWM-driven robotic components can easily be added without regard for the limited number of PWM pins on the SBC. I'm using this board, which has numerous alternatives available from various sellers on Amazon and DigiKey. The set I purchased includes two modules, and is $10.
https://www.amazon.com/dp/B0CNVBWX2M

# Power System
We need to be able to provide adequate power to all drive components while also maintaining a continuous 5V at 2.5A for the SBC. 

## Batteries
Lithium-ion batteries are the status-quo for robotics projects like these. A 3S (11.1V nominal) LiPo will be perfect. This instance is a bit more costly than I'd like for this project, but suitable alternatives can be found at hobby shops and RC drone suppliers for even cheaper.
https://www.amazon.com/dp/B07DNQMRWW

## 5V Converter
As the 3S battery will output just under 13V at full charge, we need to drop this down to 5V for the SBC and sensors, and regulate that voltage to prevent brown-outs. There are tons of suitable DC/DC converters available, and I happened to have a few that would do on hand. Here's a set of six such DC/DC converters for around $14, that we can adjust to output the 5V that we'll need.
https://www.amazon.com/MP1584EN-DC-DC-Converter-Adjustable-Module/dp/B01MQGMOKI


