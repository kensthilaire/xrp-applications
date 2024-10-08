# Driver Station Controller for XRP

This directory contains a Python application that will run on a computer to control an XRP robot using a gamepad controller, providing driver-operated control for your XRP.

## Compatibility
This program has been tested on the following computer platforms:

* Windows 10/11 laptop
* MacBook Pro (Intel-based)
* Raspberry Pi 3b and a Raspberry Pi Zero W.

This program has been tested with **`Logitech F310`** and **`Generic XBOX`** gamepad controllers. Additional devices and gamepad controllers will be tested over time.

This program is written for Python version 3.

## Future Plans
In this release, only WIFI connectivity is supported. Bluetooth support will be added in a future release.

## Relevant Files
* config.json - JSON-formatted configuration file to set parameters for the application
* config.py - Python module to read and parse the contents of the JSON configuration file
* joystick.py - Python module to provide the interface to the gamepad controller
* logger.py - Python module to set up the logging facility for the application
* requirements.txt - Requirements file providing python package dependencies
* xrp_controller.py - Main python module that provides the interface to the XRP robot over a WIFI network. Module supports UDP and TCP socket connections to the XRP.

## Installation and Setup

### Windows 10/11 Prerequisite Steps (Windows ONLY)

In order to make your life easier dealing with python programs in the Windows environment, please perform these steps to prepare your machine to run this application

#### Install Python3
Windows does not support python natively, so you will likely need to install python manually.

Download Python for Windows from [python.org/downloads/windows](https://python.org/downloads/windows) and install it for all users.

#### Install Git For Windows

Windows also does not have support for the **`git`** source code management utility, so we'll install that as well.

Download Git For Windoes from [gitforwindows.org](https://gitforwindows.org/) and install it to your computer. It is suggested that you accept all the default options when installing Git For Windows.

### Installing The Software Application (ALL Platforms)

You will need to create a local **`git`** repository with the application software.

On a Windows computer, launch a **`GitBash`** window.

On a Mac, Raspberry Pi, or Linus computer, open up a terminal window.

```
$ mkdir -p ~/GitHub
$ cd ~/GitHub
$ git clone https://github.com/kensthilaire/xrp-applications.git
$ cd xrp-applications/driver_station
```
### Setting Up The Python Virtual Environment

It is highly recommended to install the application using a python virtual environment. 

#### Raspberry Pi, Linux, and Mac Computers

On a Linux or Mac computer, I use the handy **`virtualenvwrapper`** utility to create and manage the python virtual environments. See [here](https://virtualenvwrapper.readthedocs.io/en/latest/) for information on how to install virtualenvwrapper.

```
# Create a directory where the python virtual environments will be located
$ mkdir -p ~/Envs

# Create the virtual environment
$ mkvirtualenv xrp-control

# Change to the application directory
$ cd ~/GitHub/xrp-applications/driver_station

# And, install all required python packages using pip
$ pip3 install -r requirements.txt
```

#### Windows Computers

On a Windows computer, I have not found a good alternative to **`virtualenvwrapper`**, so you will have to create and manage your virtual environment using individual shell commands. No

```
# Create a directory where the python virtual environments will be located
$ mkdir -p ~/Envs

# Create the virtual environment
$ python -m venv ~/Envs/xrp-control

# Activate a virtual environment from Git Bash
$ . ~/Envs/xrp-control/Scripts/activate

# Change to the application directory
$ cd ~/GitHub/xrp-applications/driver_station

# And, install all required python packages using pip
$ pip install -r requirements.txt

```
## Connecting Your Gamepad Controller

Connect your gamepad controller to any USB connector on the computer.  

Currently, this program can communicate to the XRP over a WIFI network, with both the computer and the XRP attached to the same WIFI network. 

The XRP library itself supports both Station (STA) and Access Point (AP) modes. For STA mode, both the XRP and the computer will connect to a separate WIFI enabled device. For AP mode, the XRP will provide the WIFI access point and the computer will need to connect to the SSID advertised by the XRP.

**NOTE: For most typical situations, using the separate WIFI device and running the XRP in STA mode may prove to be easier to manage.**

## Configuration
The xrp_controller.py application supports command arguments that can be used to specify all of the configuration settings, but for convenience a separate config file is supported to allow the configuration to be setup and referenced. `config.json` is a JSON-formatted file containing each of the settable parameters for the application. Following is an example configuration file with the supported configuration elements.

    { 
        "name"       : "XRP-CTRL",
        "controller" : "joystick",
        "socket_type": "TCP", 
        "devices"    : [
            {
                "name"   : "XRP-1",
                "ipaddr" : "<XRP IP address>",
                "port"   : 9999
            },
            {
                "name"   : "XRP-2",
                "ipaddr" : "<another XRP IP address>",
                "port"   : 9999
            }
        ],
        "debug"      : false 
    }

The devices array allows for the specification of a set of XRPs with known IP addresses. Each XRP IP address and port can be individually configured.

**NOTE: Be sure that the config.json file is properly formatted JSON.**

**TIP: Copy the default config.json file to a separate file (e.g. my\_config.json), edit the file for the specific configuration and specify this JSON configuration file when invoking the control application (e.g. python xrp\_controller.py -c my\_config.json).**

### Configuration Parameter Descriptions 
 * name - descriptive short name for the control application and the XRP devices.
 * controller - must be set to `joystick`. Future versions of the application will likely support additional controller types.
 * devices - JSON array used to specify one or more XRP devices. You may omit the devices array if you specify the XRP devices via command line arguments.
 * ipaddr - used to specify the IP address of the XRP devices.
 * port - used to define the UDP/TCP port number for the socket connection between the control application and the XRP. This port number should be greater than 5000 and less than 65534. Default is port 9999.
 * socket_type - specifies the type of socket connection, either TCP or UDP.
 * debug - enables debug logging for additional output, set to `false` to disable verbose logging.

## Running the XRP Controller Application


### Running The Program With Configuration File Settings
To run the application using the values as defined in the `config.json` file, simply run this command from the **`~/GitHub/xrp-applications/driver_station`** directory in a terminal window that has the python virtual environment activated:

```
(xrp-control)$ python xrp_controller
```
The output should be similar to the following:

```
INFO:MyLogger:device /dev/input/event1, name "Logitech Gamepad F310", phys "usb-3f980000.usb-1.2/input0"
INFO:MyLogger:Creating Client Connection to 192.168.1.129:9999
INFO:MyLogger:Client Connection Established to 192.168.1.129:9999
DEBUG:MyLogger:Sending: Event:LeftBumper:1
DEBUG:MyLogger:Sending: Event:LeftBumper:0
DEBUG:MyLogger:Sending: Event:LeftJoystickX:0.030000
DEBUG:MyLogger:Sending: Event:LeftJoystickY:-0.090000
DEBUG:MyLogger:Sending: Event:LeftJoystickX:0.070000
DEBUG:MyLogger:Sending: Event:LeftJoystickY:-0.170000
```
### Terminating The Program
Terminate the program by typing Ctrl-C in the terminal window.

### Using Command Arguments To Override Configuration Settings
The `xrp_controller.py` application supports command line arguments to override any of the configuration parameters contained in the `config.json` file.  

To list all the supported command line arguments, run the program with the `--help` argument:

```
$ cd ~/GitHub/xrp-applications
$ python xrp_controller --help
usage: xrp_controller.py [-h] [-d] [-c CONFIG] [-p XRP_PORT] [-s SOCKET_TYPE] [-x XRP_IPADDR]

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug
  -c CONFIG, --config CONFIG
  -p XRP_PORT, --port XRP_PORT
  -s SOCKET_TYPE, --socket SOCKET_TYPE
  -x XRP_IPADDR, --xrp XRP_IPADDR
```

Examples:

```
Specifying an alternate configuration file:

$ python xrp_controller -c my_config.json

Specifying one or more XRP devices:

$ python xrp_controller -x 192.168.1.130,192.168.1.140
```

### Running the XRP Controller Application Automatically (Raspberry Pi Only)
The XRP control application can be set up to run automatically when the Raspberry Pi starts, using the linux systemd service.

An example system service configuration file is provided in the repository and can be used directly if the file paths are all the same in your installation. To configure the service, issue the following commands:

```
$ pushd /etc/systemd/system
$ sudo ln -s /home/pi/GitHub/xrp-applications/driver_station/xrp_controller.service xrp_controller.service
$ popd
$ sudo enable xrp_controller.service
$ sudo start xrp_controller.service
```

To manually start, stop, restart the XRP control application service, use one of the following commands. The start command will launch the application if it is not already running. The stop command will terminate a running application, and a restart command will issue the stop/start commands in sequence to restart the application.

```
$ sudo systemctl start xrp_controller.service
$ sudo systemctl stop xrp_controller.service
$ sudo systemctl restart xrp_controller.service
```
You can also check the status of a running application by issuing:

```
$ sudo systemctl status xrp_controller.service
```

To configure the XRP application service to run automatically at startup, issue this command:

```
$ sudo systemctl enable xrp_controller.service
```

To disable the XRP application from running automatically, issue this command:

```
$ sudo systemctl disable xrp_controller.service
```

**NOTE: If you disable the service from running automatically, you will likely have to run the initial setup command sequence to re-enable it later**

## Viewing the Log Files (Raspberry Pi Only)

Much of the XRP control application has been set up to use the linux system logger. For Raspberry Pi Bookworm distributions, you can view the log file using the `journalctl` command as follows:

```
$ journalctl -f
```

For earlier versions of the Raspberry Pi distribution (e.g. Bullseye), you should be able to view the syslog files in /var/log:

```
$ sudo tail -f /var/log/syslog
```
