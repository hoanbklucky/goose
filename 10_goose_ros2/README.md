You have implemented self driving using drive.py. Now let's learn how to implement self driving using ROS2. The idea is to divide drive.py into subprograms called nodes.
We will have 4 nodes
- perception_node: read image from webcam and run YOLO interference for lane and other object detection. From there, lane error will be calculated.
- control_node: this will calculate steering based on error (published by perception_node) and PID control.
- motor_node: this will convert steering (published by control_node) to left and right motors speed (base speec +/- steering)
- web_stream_node: this will create a web app that display webcam video and debug info (pubished by perception_node).

Below is node graph:
<img width="2102" height="916" alt="rqt_graph" src="https://github.com/user-attachments/assets/98007d86-c588-495e-872a-e795769b5d42" />

To implement self driving using ROS2:
- Download ros2_humble built for Rock5C from this [link](https://flpoly-my.sharepoint.com/:u:/g/personal/hngo_floridapoly_edu/IQAPDKnjsL5PRq6V_H-vSAHcAaKjL2YlWQ6TgBGAb3ETujg?e=0buhDM) and unzip it
- Put the unzipped folder "ros2_humble" inside /home on Rock5C
- Create a folder named ros2_ws (i.e., ros2 workspace) inside /home
- Download src.zip from this GitHub folder and unzip it.
- Put the unzipped folder "src" into the newly created ros2_ws folder. Now you have source of ROS2 code inside ros2_ws
- In terminal, activate yolovenv environment

    ```source ~/yolovenv/bin/activate```
  
    ```pip install -U colcon-common-extensions```
  
    ```pip install opencv-python```
  
- Edit goose_adapter.py inside ~/ros2_ws/src/goose_ros2/goose_ros2 to have motor mapping match your robot

- With yolovenv environment activate, you cd into ros2_ws:

    ```cd ~/ros2_ws```

- Build goose_ros2 package, source it:

    ```colcon build --packages-select goose_ros2 --symlink-install```
  
    ```source install/setup.bash```

- Edit ~/.bashrc so that everytime you open a new terminal, it will source ros2_humble and ros2_ws:

    ```nano ~/.bashrc```

- Add two lines below to the end of .bashrc file:

    ```source ~/ros2_humble/install/setup.bash```
  
    ```source ~/ros2_ws/install/setup.bash```

- Ctrl + O and Ctrl + X to save and edit from nano editor
- Still inside ~/ros2_ws folder, launch goose_ros2 package:

    ```ros2 launch goose_ros2 bringup.launch.py```

- If everything goes well, you should see something similar to the below:

<img width="1008" height="796" alt="instruction on how to build and launch goose_ros2 package" src="https://github.com/user-attachments/assets/e7fbae98-c82e-46c7-a590-34eae3195916" />

- If you get error, copy error message into AI for quick help or check with instructor.
- Click the URL provided to open debug video
- Open a new terminal and try different ROS2 command (ros2 node list, ros2 topic list, ros2 topic hz <topic_name>, ros2 node info <node_name>, ros2 topic info <topic_name>, rqt_graph, etc.) to understand more about nodes and topics.
- Put robot infront of white and yellow lane and look at debug video to see if best_w_x (white lane x coordinate prediction) and best_y_x (yellow lane x coordinate prediction), etc. are reasonable.
- Let robot self drive. 
    

    
