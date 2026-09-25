# Work on GooseBot Code - Three Editing Methods

## Mission

Learn three safe ways to open and edit the code stored in `~/goose` on the ROCK 5C:

1. work directly on GooseBot with its monitor and keyboard;
2. connect from a laptop terminal with SSH and edit with `nano`; or
3. connect from laptop VS Code with the Remote - SSH extension.

All three methods edit the same files on GooseBot. Only the keyboard, screen, and editor change.

## Why It Matters

A laptop copy of the repository and the copy in `~/goose` on GooseBot are separate folders on separate computers. Editing a file in the laptop copy does not automatically change the file that runs on the robot. These checks help you avoid editing one copy and accidentally running another.

## Choose a Workflow

| Method | What you use | Where the file is stored | Best use |
|---|---|---|---|
| Direct on GooseBot | monitor and keyboard attached to the ROCK 5C | GooseBot `~/goose` | initial setup and network troubleshooting |
| Laptop terminal + SSH + `nano` | PowerShell, Terminal, or another SSH client | GooseBot `~/goose` | quick edits and running commands |
| Laptop VS Code + Remote SSH | VS Code interface and integrated terminal on the laptop | GooseBot `~/goose` | recommended for normal development |

> **Location check:** Before editing or running robot code, execute `hostname`, `whoami`, and `pwd`. For remote work, the prompt and VS Code status bar must indicate the ROCK 5C, and `pwd` must show the GooseBot repository on the ROCK 5C.

## Safety Gate

- Switch off or disconnect motor power while configuring networking or editing code.
- Lift the wheels clear of the table before starting any motor-control program.
- Keep the motor power disconnect within reach and use a spotter for floor tests.
- Never expose passwords, private keys, or campus credentials in screenshots, Git commits, or shared files.

## Part 1 - Prepare SSH on GooseBot

Connect a monitor and keyboard directly to the ROCK 5C. Follow the official [Radxa ROCK 5C Quick Setup - SSH](https://docs.radxa.com/en/rock5/rock5c/getting-started/basic-software-conf#ssh) instructions to identify the username and IP address and verify the SSH service.

These commands provide the essential checks:

```bash
whoami
hostname
hostname -I
sudo systemctl status ssh --no-pager
```

Record the username and the ROCK 5C IPv4 address. Do not use `127.0.0.1`; that address always refers to the computer on which the command is running.

If Radxa's status check reports that the SSH service is missing, install and enable it:

```bash
sudo apt update
sudo apt install openssh-server openssh-sftp-server
sudo systemctl enable --now ssh
sudo systemctl status ssh --no-pager
```

The final status should contain `active (running)`. The laptop and GooseBot must be able to reach each other through an approved local network or the school VPN.

## Part 2 - Verify the Repository on GooseBot

On the ROCK 5C, run:

```bash
cd ~/goose
hostname
whoami
pwd
git status --short
```

The `pwd` output should end in `/goose`. If `~/goose` does not exist, complete the repository-cloning step in [Activity 04](../04_motor_test/README.md) before continuing.

If `git status --short` lists files you did not intentionally change, stop and ask the instructor before pulling, switching branches, or discarding anything.

## Method 1 - Edit Directly on GooseBot

Use the monitor and keyboard connected to the ROCK 5C. Open a terminal and enter:

```bash
cd ~/goose
hostname
pwd
nano 04_motor_test/keyboard_control.py
```

Essential `nano` controls are shown at the bottom of the editor. The `^` symbol means the Ctrl key.

| Action | Keys |
|---|---|
| search | Ctrl+W |
| save | Ctrl+O, then Enter |
| exit | Ctrl+X |
| exit without saving an unwanted change | Ctrl+X, then `N` |

After saving, return to the terminal and run the appropriate activity commands. For Activity 04:

```bash
source ~/goose-motor-venv/bin/activate
cd ~/goose/04_motor_test
python keyboard_control.py
```

## Method 2 - Use a Laptop Terminal, SSH, and `nano`

Open PowerShell on Windows or Terminal on macOS/Linux. Replace the placeholders with the values recorded in Part 1:

```bash
ssh <username>@<GOOSEBOT_IP>
```

Example format only:

```bash
ssh radxa@192.0.2.10
```

On the first connection, compare the host information with the robot or ask the instructor before accepting the SSH fingerprint. Entering a password produces no dots or other screen feedback; this is normal.

After login, prove that the terminal is on GooseBot before editing:

```bash
hostname
whoami
cd ~/goose
pwd
git status --short
nano 04_motor_test/keyboard_control.py
```

Use the same `nano` controls from Method 1. To run Activity 04 after saving:

```bash
source ~/goose-motor-venv/bin/activate
cd ~/goose/04_motor_test
python keyboard_control.py
```

When finished, stop the program safely and close the SSH session:

```bash
exit
```

## Method 3 - Use Laptop VS Code with Remote SSH

This is the recommended workflow for substantial editing. VS Code runs its interface on the laptop while opening and operating on files stored on GooseBot.

1. Install **Remote - SSH**, published by Microsoft, from the laptop VS Code Extensions view. See Microsoft's [Remote Development using SSH](https://code.visualstudio.com/docs/remote/ssh) documentation.
2. Confirm that Method 2 works first. VS Code uses the same SSH connection underneath.
3. In VS Code, open the Command Palette with Ctrl+Shift+P on Windows/Linux or Cmd+Shift+P on macOS.
4. Run **Remote-SSH: Connect to Host...**.
5. Enter the same connection used in Method 2, such as `radxa@192.0.2.10`.
6. Select **Linux** if VS Code asks for the remote platform.
7. After connection, check the lower-left status-bar indicator. It must show an SSH connection to GooseBot.
8. Select **File > Open Folder...** and open the repository on GooseBot. For the `radxa` user, the usual path is `/home/radxa/goose`. If the username differs, run `printf '%s\n' "$HOME/goose"` in the remote terminal to obtain the exact path.
9. Open **Terminal > New Terminal** inside the connected VS Code window and verify:

   ```bash
   hostname
   whoami
   pwd
   git status --short
   ```

10. Confirm that `pwd` ends in `/goose` before editing or running code.

The VS Code Explorer and integrated terminal now operate on GooseBot. A normal VS Code window without the SSH status indicator may instead be editing the laptop's separate clone.

### Optional: Give GooseBot a Short SSH Name

In VS Code, run **Remote-SSH: Open SSH Configuration File...** and add:

```sshconfig
Host goosebot
    HostName <GOOSEBOT_IP>
    User <username>
```

You may then connect with either:

```bash
ssh goosebot
```

or **Remote-SSH: Connect to Host... > goosebot**. Update `HostName` if the ROCK 5C receives a different IP address.

## Before Every Editing Session

Use this short check regardless of the chosen method:

```bash
hostname
whoami
cd ~/goose
pwd
git status --short
```

Then activate the environment required by the activity. Do not use `sudo python`; activate the documented virtual environment and run `python` from that environment.

## Command Breakdown

| Command | Meaning |
|---|---|
| `hostname` | identifies the computer running the terminal |
| `whoami` | identifies the current Linux user |
| `hostname -I` | displays network addresses assigned to GooseBot |
| `pwd` | displays the exact current folder |
| `systemctl status ssh` | checks whether the SSH server is running |
| `ssh user@address` | opens a shell on GooseBot from the laptop |
| `nano file.py` | edits a text file in the terminal |
| `git status --short` | shows changed or untracked repository files |
| `exit` | closes the current SSH shell |

## Success Criteria

You are ready for remote development when you can:

- explain where the edited file is stored for all three methods;
- connect from the laptop using a terminal SSH client;
- open and save a file with `nano`;
- connect with VS Code Remote SSH and open the remote `~/goose` repository;
- use `hostname`, `whoami`, and `pwd` to prove that commands run on GooseBot; and
- disconnect safely without interrupting an active motor test.

## What to Submit

Unless the activity or Canvas says otherwise, submit one screenshot from the recommended VS Code Remote SSH method showing:

- the SSH host indicator in the lower-left status bar;
- the remote GooseBot repository in the Explorer;
- terminal output from `hostname`, `whoami`, and `pwd`; and
- no passwords, private keys, campus credentials, or unnecessary personal information.

## Troubleshooting

| Problem | Check |
|---|---|
| connection times out | confirm both devices have approved network access; verify the current ROCK 5C IP address and school VPN requirement |
| connection is refused | check `sudo systemctl status ssh`; install or restart the SSH service using Radxa's instructions |
| password seems not to type | SSH intentionally hides password characters; type carefully and press Enter |
| host-key warning appears after an IP change | do not bypass it automatically; confirm the device identity and ask the instructor |
| `cd ~/goose` fails | clone the repository on GooseBot as instructed in Activity 04 |
| edited code does not affect the robot | run `hostname` and `pwd`; you may have edited the laptop clone instead of the GooseBot copy |
| VS Code opens a local window | reconnect with **Remote-SSH: Connect to Host...** and confirm the SSH status indicator before opening the folder |
| VS Code connection stalls | first prove ordinary terminal SSH works, then inspect **Remote - SSH** in the VS Code Output panel |
| permission denied while saving | confirm you are editing files owned by your normal user inside `~/goose`; do not solve this by running VS Code or the editor with `sudo` |
| IP address changes | rerun `hostname -I` on GooseBot and update the SSH command or `HostName` entry |

## Continue the Course

Return to the activity that sent you here. Remote motor testing begins in [Activity 04](../04_motor_test/README.md), and the same workflow is reused for NPU execution and autonomous driving.
