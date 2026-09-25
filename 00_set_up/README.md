# Activity 00 - Set Up Python, VS Code, Git, and the GooseBot Repository

## Mission

Prepare your laptop for the GooseBot activities, run a Python program from Visual Studio Code, and clone the course repository so you can receive future instruction and code updates from GitHub.

Plan for approximately 45-75 minutes. You do not need the physical robot for this activity.

## Why It Matters

The later activities use Python for motor control, dataset tools, model training, model conversion, computer vision, and autonomous driving. VS Code provides one place to edit files and run terminal commands. Git records versions and delivers corrected course files. Verifying these tools now prevents software-installation problems from being confused with robot problems later.

## Success Criteria

You are ready when all of the following are true:

- `python --version` (or `python3 --version`) reports a modern 64-bit Python installation;
- `git --version` works;
- `code --version` works, or VS Code launches normally if the command-line launcher is unavailable;
- the Microsoft Python extension is installed in VS Code;
- the GooseBot repository opens in VS Code;
- a virtual environment can be created and activated; and
- `hello_goose.py` runs from the VS Code terminal.

## Part 1 - Install Python

### Windows 10 or 11

1. Download the current 64-bit CPython installer from [python.org](https://www.python.org/downloads/).
2. On the first installer screen, select **Add python.exe to PATH**.
3. Complete the normal installation. Avoid the Microsoft Store alias for this course.
4. Close and reopen PowerShell, then verify:

   ```powershell
   python --version
   where.exe python
   py -0p
   ```

### macOS

Install the current macOS package from [python.org](https://www.python.org/downloads/), open a new Terminal, and verify:

```bash
python3 --version
which -a python3
```

### Ubuntu

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
python3 --version
which python3
```

Later instructions use `python`. On macOS or Ubuntu, use `python3` if `python` is not recognized.

## Part 2 - Install Visual Studio Code

1. Download VS Code from [code.visualstudio.com](https://code.visualstudio.com/download).
2. Install it. On Windows, keep **Add to PATH** enabled if the installer shows that option.
3. Launch VS Code, open **Extensions**, and install **Python** published by Microsoft.
4. Optional: watch the instructor's [VS Code introduction](https://youtu.be/B-s71n0dHUk) while trying the Explorer, editor, integrated terminal, and Extensions panel yourself.
5. Open a new terminal and check:

   ```text
   code --version
   ```

If the command is unavailable but VS Code launches normally, continue. On macOS, open the Command Palette and run **Shell Command: Install 'code' command in PATH** if you want terminal access.

## Part 3 - Install and Configure Git

Windows and macOS installers are available from [git-scm.com](https://git-scm.com/downloads). On Ubuntu, Git was installed in Part 1 or can be installed with `sudo apt install git`.

Verify and configure it with your own name and an email associated with GitHub:

```bash
git --version
git config --global user.name "Your Full Name"
git config --global user.email "your.email@example.com"
git config --global --get user.name
git config --global --get user.email
```

## Part 4 - Clone and Open GooseBot

Use a short local path that is not inside OneDrive, iCloud, Dropbox, a network drive, or another synchronized folder.

Windows PowerShell:

```powershell
cd C:\
git clone https://github.com/hoanbklucky/goose.git
cd C:\goose
git status --short
code .
```

macOS or Ubuntu:

```bash
cd ~
git clone https://github.com/hoanbklucky/goose.git
cd ~/goose
git status --short
code .
```

Clone only once. In later sessions, enter the existing folder and use `git pull --rebase` after protecting any local work.

## Part 5 - Create a Small Python Project

1. In the repository root, create a folder named `practice`.
2. In that folder, create `hello_goose.py` with this content:

   ```python
   message = "GooseBot development environment is ready!"
   print(message)
   ```

3. In the VS Code terminal, create a virtual environment.

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python practice\hello_goose.py
   ```

   macOS or Ubuntu:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python practice/hello_goose.py
   ```

4. Select the `.venv` interpreter if VS Code asks. The expected output is:

   ```text
   GooseBot development environment is ready!
   ```

5. Deactivate the environment when finished:

   ```text
   deactivate
   ```

The `practice` folder and `.venv` are local exercises. Do not commit them to the shared course repository unless the instructor requests them.

## Command Breakdown

| Command | Meaning |
|---|---|
| `python --version` | confirms which Python command and version are active |
| `where.exe python` / `which python3` | shows the executable found by the shell |
| `python -m venv .venv` | asks that Python interpreter to create an isolated environment in `.venv` |
| `source .venv/bin/activate` | activates the environment on macOS or Linux |
| `.\.venv\Scripts\Activate.ps1` | activates the environment in Windows PowerShell |
| `git clone URL` | downloads the repository and its history once |
| `git status --short` | lists local changes; no output means the working tree is clean |
| `git pull --rebase` | downloads course updates and reapplies local commits after them |
| `code .` | opens the current folder in VS Code |

## What to Submit

Unless Canvas says otherwise, submit one readable screenshot showing:

- VS Code open to `hello_goose.py`;
- the integrated terminal displaying the successful program output; and
- the output of `python --version` and `git --version`.

Do not submit installed software, the `.venv` directory, passwords, or private account information.

## Troubleshooting

| Problem | Check |
|---|---|
| `python` is not recognized on Windows | reopen PowerShell; rerun the installer and enable **Add python.exe to PATH** |
| Windows opens the Microsoft Store | disable the Python App Execution Aliases or use the python.org installation shown by `py -0p` |
| script runs with the wrong interpreter | use **Python: Select Interpreter** in VS Code and choose the repository `.venv` |
| PowerShell blocks activation | run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, approve the change, and retry |
| `code` is not recognized | reopen the terminal or launch VS Code from its application shortcut |
| repository folder already exists | do not clone over it; enter the folder and run `git status --short` |
| Git update reports a conflict | do not force or discard changes; back up edited files and ask the instructor |

## Next Activity

Continue to [Activity 01 - Hardware Selection](../01_hardware_selection/README.md).
