![Goose](https://github.com/lznfjv/goose/blob/main/assets/circuit.mp4?raw=true)

# Bringing it All Together
So far, we have a severely over-powered RC car that also happens to run an object detection model. Now, we can synthesize those two featuresets into a rudimentary self-driving car algorithm.

This section assumes that you have a model town set up, with dashed yellow lane divider lines and solid white outer lane boundary lines. You can also add some red stop bar lines here and there if you want to see your robot politely pause at the stop bars before proceeding on its merry way.

The code for this lane-following system is provided for you in the drive.py script. Here, I will break down what each part of the code is doing.

**NOTE:** This is a cobbled-together lane-following and object-detection script that demonstrates an extremly basic mechanism for having a robot autonomously follow lanes. It is far, *far* from perfect, and may be observed occasionally losing its place and giving up on lane following if it encounters something it doesn't expect. Please feel free to build on this as you please, or tear it apart and start over. It is only provided to demonstrate essential capabilities and as a reference for further development.

# Script Set-up
It is best to SSH into Rock5C and do the below from your dev computer. You should set up your Rock5C so that it auto login and connect to Wifi. That way, you can SSH into the Rock5C from your dev computer without the need to hook up monitor + keyboard + mouse to your Rock5C to login first. For the Rock5C to automatically login whenever you turn it on, you can try this https://docs.radxa.com/en/rock5/rock5b/radxa-os/autologinLinks to an external site. Note: if you do System Update as instructed in the link, after System Update, besides enabling gdm.service as instructed, you need to enable I2C again (see Github for instruction). Once Rock5C auto login, it should auto connect to Wifi. If not, try option "Store password for all users (not encrypted)" under Password and click Apply.

For convenience, let's place the drive.py script in the same `yolodetect` directory we created in chapter 6. Also, make sure your `yolovenv` Python virtual environment is active, so that we know we have an environment that is set up to run object detection models on the NPU. As a refresher:

Deactivate any existing Python venv.

    deactivate

Change directory to your home folder.

    cd ~

Activate the `yolovenv` virtual environment then enter the `yolodetect` folder.

    source yolovenv/bin/activate
    cd yolodetect

Copy the `drive.py` file into this directory, if you haven't already:

    cp ~/goose/09_self_driving/drive.py ~/yolodetect

We also need to install the Python packages that we previously used for motor testing, as the same packages are used by the script to maneuver the robot.

    pip install board adafruit-blinka adafruit-circuitpython-pca9685 gpiod adafruit-circuitpython-pca9685

# Run the Script
Let's run the script and see how it behaves. Before sending Goose into action, place it in the outer lane of your model town's road, in between the yellow dashed and white solid lines.

Next, make sure that the script knows where to find your RKNN model folder. Edit line 11 in `drive.py` to point to the correct model path. There are different ways to do this. You can edit code on Goosebot from VSCode on your dev computer if you connect your VSCode to Goosebot via SSH (https://docs.radxa.com/en/rock5/rock5c/app-development/vscode-remote-ssh). Or you can use Nano terminal command. From terminal:

    nano drive.py

Edit line 11 to name of folder storing RKNN model. Edit line 80 and 81 (left_motors = [Motor(pca, 0, 1), Motor(pca, 2, 3)], right_motors = [Motor(pca, 6, 7), Motor(pca, 4, 5)] ) to match PWM channels for left motors (front and rear) and right motors (front and rear) (review 04_motor_test for how to identify those numbers). For my robot, left front use channel 0 and 1, left rear use 2 and 3, right front use 6 and 7, and right rear use 4 and 5. Press Ctrl + O to save and Ctrl + X to exit. 

To run the script:

    python drive.py

You should see URL. Ctrl + Click the second one and you will see video stream with debug information.
- best_w_x: best estimate of white lane centroid's x coordinate
- best_y_x:  best estimate of yellow lane centroid's x coordinate
- target_x: best estimate of the middle point between white and yellow lane. In another word, this is the best estimate of the middle/center of the lane. Highlighted by a green circle.
- CENTER_X: center of video view. There is a vertical line right at the middle of video view. We want to control/steer our robot so that center of (video) view (vertical line) is coincident with the center of the lane (green circle).
- error: difference between target_x and CENTER_X.
- steering: degree of steering. The larger the error, the larger steering is needed (PD control).
- BASE_SPEED: larger means faster driving. Set at 0.08 first for testing.

You want to adjust webcam angle (look up and ahead instead of look down) so that best_w_x and/or best_y_x can be calculated (instead of None) for target_x, error, and steering calculation.

- Put your robot in the middle and straight and you should see error zero or small and steering is zero or small.
- Manually turn your robot to the left and you should see some error and steering.
- Manually turn your robot to the right and you should see some error and steering (with opposite sign).

Once the numbers behave properly, for the robot to move, you need to uncomment a line in drive.py (you have to find out what line by yourself ^.^), save it (Ctrl + O and Ctrl + X if you use Nano), and run again:

    python drive.py
    
Hold your robot up and point its camera to the lanes at different angle and see if the motors turn properly https://youtube.com/shorts/GMXl9YynOF8?feature=share. Once the motors behave properly, you can put the robot the ground. Goose should start to move and follow the lane, and the terminal should present you with a URL where you can view the object-detection model's hits in near-real-time https://youtu.be/XVL9MJ0nml4. 

# Analysis
Let's go through the code. 

## Imports
Lines 1-9 are the same imports we've been using thus far, loading relevant Python packages and libraries for the peripherals we've connected, like the I2C-to-PWM bridge module.

## Config
Lines 10-18 expose some essential configuration parameters. We set the model path, then define the axis sizes for the video feed. This is pre-set to 640x480, because this is low-resolution enough for the NPU to run inferences rapidly while maintaining high enough resolution to clearly distinguish objects. The Host IP is set to `0.0.0.0` to tell the Flask web app to broadcast to the entire local network, allowing your laptop or other host machine to receive the video stream that is being produced on the Rock5c lite.

The default port of 5000 can be changed if necessary, but if you can see the video stream without issue, there's no reason to do so. If multiple robots are running on the same network, you may want to allocate unique ports such that you don't experience network connectivity issues when trying to access the stream.

## Tuning Parameters
Lines 20-25 include some parameters that **significantly** influence the performance of the lane following algorithm. 

The first of these is an RoI (region of interest) cutoff. By default, it is set to `0.65`, essentially telling the lane following algorithm to ignore any objects that are detected in the upper 65% of the video feed. This helps to prevent Goose from turning too early in response to bends that are further down the road (early apexing), or being computationally overwhelmed by all the potential detections of a larger image. You will want to adjust this parameter if you are not using the provided camera mounting bracket, or if your camera has a wider angle than anticipated.

`Kp`, `Kd`, and `BASE_SPEED` set the proportional gain, differential gain, and uninhibited forward motor throttle, respectively. The proportional and differential gains can be adjusted if turns are being taken too slowly/quickly or if overshoots and undershoots cause harmonic oscillations. Read up on PID controllers for more information.

Lines 27-30 dictate Goose's behavior when it comes across a red-line stopbar. The time for which Goose will pause, cooldown before another stopbar trigger can occur, and distance at which a stopbar can be perceived can be adjusted here.

Finally, lines 32-34 specify some base throttle characteristics. This is dependent on several factors, such as the specific motors used, battery charge, and motor driver circuitry. As DC motors stop functioning entirely below a certain power threshold, a minimum acceptable value is defined. A maximum steer ratio is also provided to prevent the robot from completely rotating in place when it only intends to perform a gradual, 45-degree turn.

## Motor Control
A motor class is defined. It utilizes the PCA library to relate different I2C messages to distinct PWM channels, thus driving the four motors in either direction (this is why we need eight signal wires to the motor drivers - one PWM signal per one motor direction).

 The motor class also defines `set_speed` and `stop` methods, to do exactly as the names suggest.

 ## Robot Control Loop
 Now, we arrive at the critical logic of the script. The control loop begins by initializing the motors and PCA module (I2C/PWM bridge).

 The robot's speed is updated at the start of each cycle of the loop. 

 The true control logic of the robot is performed by first querying the object detection model set to run on the NPU, and drawing bounding boxes around each detected and labeled object. Areas are calculated for each bounding box, and centroids are derived. 

 The algorithm then calculates its approximate trajectory based on the center of the video feed relative to the centroids of the `yellowline` and `whiteline` bounded regions. The difference between the `target` center and the actual center drives a control law, indicating positive or negative (right or left) turning, so long as the difference is over a given threshold. The threshold is applied so as to enforce a maximum acceptable deviation from the target centroid, thus preventing unwanted 'jitter' in the robot's travel path.

 Furthermore, similar area-calculating logic is employed to detect the `redline` class's presence in the RoI. If that `redline`, or stopbar, is encountered, the aforementioned stop parameters take effect to pause the operation of the robot for a given duration.

 Throughout all of this motion control, desired changes in the robot's motion are fed into an ongoing PID control loop, where the `Kp` and `Kd` parameters are employed. The results can be witnessed in the included videos, both from the perspective of an observer and from the view of the camera aboard the robot.
