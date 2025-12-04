# Wiring

![Goose V5 Wiring Diagram](https://github.com/lznfjv/goose/blob/main/03_mounting_and_wiring/assets/goose_wiring.png?raw=true)

Follow this wiring diagram to connect each component. Note that wires that are connected via screw terminals should be attached to their designated components *before* those components are mounted to the chassis.

# Chassis Mounting

As heat-set inserts are used to secure components to the chassis, those inserts must first be attached to the chassis using a soldering iron or other heated instrument. Myriad tutorials are available on the Internet in the use of heat-set inserts.

Each component (apart from the DC/DC converter, which can be left inline to the power cable harness) has a designated location on the chassis, marked by recessed outline.

Motor and sensor wires may be routed through the various openings in the chassis for a tidier appearance. It is advisable to cut, splice, solder, and heatshrink the webcam cable and any other cables that are excessively long so as to minimize the likelihood of cables catching upon obstacles or dragging along the ground.

# Camera Mount

Additional holes are present along the outer perimeter of the chassis as well as on the top of the front of the chassis. This is to allow flexibility in mounting locations for the camera, and adaptability for different camera sizes. The perimeter mounting holes can also be used to mount the time-of-flight sensors, although they have not yet been implemented in this instance of Goose.

# Battery Attachment
A standard 3S 2000mAh LiPo is most conveniently attached to the chassis between the sets of wheels on the underside of the chassis. A zip-tie can be routed beneath the Rock5c lite and down through the openings in the chassis to secure the battery back. Ensure that the battery's XT60 connector harness faces outwards towards the rear of the chassis to prevent the cable from obstructing the camera's line of sight.


# A note on I2C configuration
By default, the I2C bus that will be used to command the four motors may not be enabled in Radxa's operating system. To enable the specific I2C bus (there are several available on this board) that corresponds to the pins used in the above wiring diagram, follow these steps:

Login to the Rock5c lite through SSH. If connected via monitor in a desktop environment, open a terminal. Issue the following command to open the Radxa setup utility:

    sudo rsetup

Enter the administrator password when prompted and press enter. By default, the password is simply 'radxa'.

Use the arrow keys to navigate to 'Overlays' and press enter. You will be presented with a warning that changing overlays can break functionality. Select 'yes' and press enter to ignore.

Press 'enter' on 'Manage overlays'.

Use the up and down arrow keys to highlight the 'Enable I2C8-M2' option. Press SPACEBAR to select this option. An asterisk (*) should appear to the left of that option. Press ENTER to accept changes.

After changes have been applies, simply press ESC several times to exit the setup menu. A reboot is suggested before proceeding.