# Quick reference

## 1. Laptop `~/.bashrc` additions

```bash
# PATH for pip --user tools (gp-saml-gui)
export PATH="$HOME/.local/bin:$PATH"

# Aliases
alias vpn='gp-saml-gui -S --gateway vpn.floridapoly.edu -- --csd-wrapper=$HOME/Downloads/openconnect-9.21/hipreport.sh --no-dtls'
alias phredg='ssh phredg'

# ROS 2 (robot link)
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
```

The `phredg` alias relies on this entry in `~/.ssh/config`:

```
Host phredg
    HostName <robot-ip-or-hostname>
    User phredg
```

Reload with `source ~/.bashrc`.

## 2. Robot `~/.bashrc` additions

Use the same ROS lines so both machines match:

```bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
```

Adjust these to whatever actually made discovery work. If you needed `ROS_STATIC_PEERS`, add it on both sides. Nodes only pick up these settings when they are launched after the exports, so restart them after any change. If a service launches your nodes automatically, it needs the settings too.

## 3. Mount the robot's map folder

```bash
mkdir -p ~/robot_ros
sshfs phredg@[ip]:/home/phredg/ ~/robot_ros
rtabmap-databaseViewer ~/robot_ros/.ros/goosebot_rtabmap.db
```

Unmount with `fusermount -u ~/robot_ros`.

The database can be large, so for a smoother view copy it first with `scp phredg:/home/phredg/.ros/goosebot_rtabmap.db ~/` and open the local copy. Don't open it while the robot is still writing to it.

## 4. Live view from the laptop

Both machines need to be on the same Wi-Fi network. The VPN blocked UDP from the robot to the laptop, so live viewing over the VPN won't work unless that gets fixed. The VPN is still fine for SSH and for the offline database.

```bash
# check you can see the robot
ros2 daemon stop
ros2 topic list --no-daemon

# RViz
rviz2
# Fixed Frame: map
# Add -> By topic: /map, /tf
# /map display: Durability Policy = Transient Local

# or the rtabmap viewer
ros2 run rtabmap_viz rtabmap_viz
```

Save your RViz layout with File -> Save Config As, then reopen it with `rviz2 -d ~/goose.rviz`.

## 5. If it stops working

1. Check the robot's nodes are running and were launched with the right ROS settings.
2. Check both machines are on the same subnet (the first three IP numbers match).
3. Run `ros2 daemon stop` on the laptop and try `ros2 topic list --no-daemon` again.
4. If the robot's IP changed, update `~/.ssh/config` and any `ROS_STATIC_PEERS`.
