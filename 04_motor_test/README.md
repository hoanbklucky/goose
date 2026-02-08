# Objective
To ensure that the motors can be used effectively, we'll make a basic script that allows us to drive the robot around using keyboard controls.

# Installation of Operating System
Follow this link to download ROCK 5C Desktop System Image https://docs.radxa.com/en/rock5/rock5c/getting-started/install-os/boot_from_sd_card and burn the image onto MicroSD card using balenaEtcher as shown in the link.

After successfully burning the image onto MicroSD card, insert the card into ROCK 5C.

Wiring and power ROCK 5C up by following instructions in this link https://docs.radxa.com/en/rock5/rock5c/getting-started/quick-start

Login using "radxa" account with the password "radxa".

# Install packages 
To control GPIOs and thus motors connected to ROCK 5C, you need to install some packages. One of them is libgpiod. More info about this package https://docs.radxa.com/en/rock5/rock5c/app-development/gpiod?lang=Python

To install libgpiod, in ROCK 5C terminal, type:

    sudo apt-get update
    sudo apt-get install python3-libgpiod

You will also need to install two other packages named Adafruit-Blinka and adafruit-circuitpython-pca9685. To install them, we will first create a virtual environment and install the packages inside the virtual environment. In ROCK 5C terminal, type:

    python3 -m venv venv --system-site-packages
    source venv/bin/activate
    pip install --upgrade pip
    pip install adafruit-blinka
    pip install adafruit-circuitpython-pca9685

Once the packages have been installed (you can test by typing python in the terminal, hit Enter, then type import board and hit Enter again. If there is no error, you are good and can type exit()). For safe testing, it is good to lift the Goosebot up (using a box or anything) so that the four wheels don't touch anything including table surface, wires, cables, etc.Now you can run mapping.py and keyboard_control.py by cd to folder 04_motor_test and type:

    python mapping.py
    

When you run mapping.py and press 1, channel 0 and 1 of the PWM driver will set to PWM value and 0, respectively, and one of four motors will turn. It means that the turning motor is connected to channel 0 and 1 of the PWM driver. Notice whether the motor is front left, front right, rear left, or rear right and whether it is turning forward or backward (webcam is at the front of Goosebot). For example the turning motor is front left and it is turning forward. Then you go open keyboard_control.py (eg. using Thonny IDE that you can install using sudo apt install thonny) and go to line 72-75 and change motor_fl initialization to in1_channel=0 and in2_channel=1 (or in1_channel=1 and in2_channel=0 if motor turns backward). Pressing 2 (which activiates channel 2 & 3), 3 (channel 4 & 5), or 4 (channel 6 & 7) and repeat the same process. Save the keyboard_control.py. In the terminal, run it:

    python keyboard_control.py

The keyboard_control.py allows you to control the motors using w,a,s,d keys on your keyboard. 
If you did the mapping above correctly, when you press w: all four motors will turn forward. s: all four motors will turn backward. a: four motors will turn in a way that make Goosebot turning left. d: four motors will turn in a way that make Goosebot turning right. More info about the two programs are below.

# Scripts
## Mapping
As we don't know for certain which motor is mapped to which PWM channels and which of the two channels per motor is mapped to forward and backward. a basic script is written. It allows the user to easily determine directionality of the motors and channel mapping. This script is included in this section of the repo.


## Keyboard control
The keyboard control script is included in this section of the repo.


# Set up Network + SSH + VNC for Remote Control
Follow instructions in this link https://docs.radxa.com/en/rock5/rock5c/getting-started/basic-software-conf to set up Network + SSH + VNC. 

Network: ROCK 5C should use network: ask instructor, password: ask instructor. For remote access to ROCK 5C from your dev computer, make sure your dev computer (eg your Laptop) is on the same network as well. 

Remote access: You want this capability because the ROCK 5C will eventually be mounted on a mobile robot and thus the ability to remotely access ROCK 5C via network is needed. There are several ways to remotely access ROCK 5C: SSH, VNC, TeamViewer, etc. The link above show you how to set up SSH, VNC, TeamViewer. We will use SSH when we just want to run terminal commands on ROCK 5C. When we want to run programs with GUI on ROCK 5C, VNC or TeamViewer is needed. For our project, VNC is often enough. 

Setting up VNC is a little bit tricky so make sure you read and follow all the instructions carefully.

Once you have SSH and VNC set up, you can SSH or VNC into the ROCK 5C (instructions in the link above) and type

    python keyboard_control.py

and use w,s,a,d keys to remotely control the motors.
