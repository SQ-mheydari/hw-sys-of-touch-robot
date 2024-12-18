# Documentation

Most documentation can be found under `doc/` directory.

This file outlines the procedure for developers to set up development environment.

# Setting up for development

## Windows

- Make sure you have Git installed and configured
- [Install Python 3.7.9](https://www.python.org/downloads/windows/)
  - Install 32-bit version or 64-bit version
  - Make sure that path is correct: In command prompt `py -3.7-32` / `py -3.7` should launch the required python version.
- Open command prompt (cmd.exe, not powershell or any other) and navigate to path where to develop
- Clone the repository: `git clone git@git.optofidelity.net:robotics/tnt_server_gt.git`
- Go to the repository `cd tnt_server_gt`
- Run `develop_env_win32.bat` if using 32-bit Python or `develop_env_win64.bat` if using 64-bit Python

## macOS

- Make sure you have Git installed and configured
  	- You should have these items in your pip.conf:
        - extra-index-url = http://jenkins-master.optofidelity.net:8081/simple/
        - trusted-host = jenkins-master.optofidelity.net
  	- For complete instructions, see: https://wiki.optofidelity.com/display/OFPYTHON/Local+Python+Package+Index
- Install Python 3.7.9 64-bit
	- Consider using pyenv to help manage multiple python versions
- Open terminal, and navigate to path where to develop
- Clone the repository: `git clone git@git.optofidelity.net:robotics/tnt_server_gt.git`
- Go to the repository `cd tnt_server_gt`
- You need to comment out `pyaudio` in `requirements.txt` in case Portaudio is not available
- Run `./develop_env_macos.sh`
- When the script finishes, run `source venv/bin/activate` to activate the virtual environment

## Linux (Debian 10, Ubuntu 18.04)

- Make sure you have Git installed and configured
  	- You should have these items in your pip.conf:
        - extra-index-url = http://jenkins-master.optofidelity.net:8081/simple/
        - trusted-host = jenkins-master.optofidelity.net
  	- For complete instructions, see: https://wiki.optofidelity.com/display/OFPYTHON/Local+Python+Package+Index
- Install Python 3.7.9 64-bit (see below)
- Open terminal, and navigate to path where to develop
- Clone the repository: `git clone git@git.optofidelity.net:robotics/tnt_server_gt.git`
- Go to the repository `cd tnt_server_gt`
- You need to comment out `pyaudio` in `requirements.txt` in case Portaudio is not available
- Run `./develop_env_linux.sh`
- When the script finishes, run `source venv/bin/activate` to activate the virtual environment

### Installing Python 3.7.9

The most convenient way to manage different Python versions without affecting the system is by use of `pyenv`.
To install `pyenv`, run following commands:

    sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl
    curl https://pyenv.run | bash

Copy the lines indicated by output to your `.bashrc` file and restart the terminal window. Then install Python

    pyenv install 3.7.9

You can now switch to using the new python version by executing `pyenv global 3.7.9`. This is used in `develop_env_linux.sh` script.

## PyCharm

[PyCharm](https://www.jetbrains.com/pycharm/) is the recommended IDE. To get started, open the repository directory in PyCharm. Then open File -> Settings -> Project -> Project Interpreter. Click the Project Interpreter down and select Show All. Locate the previously created venv.
In case PyCharm appears to be slow, the virus scanner might be interfering with it. In this case PyCharm should be added in scanner's excluded application list.

## Submodules

At the moment the installer used by Jenkins build system is included as submodule. If you require the installer in your development environment, issue the following in command line under the repository directory:

```
git submodule sync
git submodule update --init --recursive
```

In case you get "Permission denied" errors, try changing `url` in `.gitmodules` to https form: `https://git.optofidelity.net/tnt/tnt-server-installer.git`. Then run both of the above commands again.

# Running TnT Server in development environment

Make sure the virtual environment is active in terminal (see section above).

## Running visual simulator

Start the server by issuing

    python main.py --configuration configuration/simulation_3axis.yaml

This should start the simulator and open browser window for visualization.

## Running numerical simulator
1. In the configuration file change the robot argument "simulator" to be true (false by default)
2. Run the server with command line option 
```
--visual-simulation=false
```
In case you get errors about wrong axis addresses, you might need to change the ones in the configuration file to comply with the hard-coded values in the simulator source code.
