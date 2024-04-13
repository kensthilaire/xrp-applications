# Driver Station Controller for Raspberry Pi

This directory contains a Python application that will run on a Raspberry Pi to control an XRP robot using a Xbox Gamepad controller.

## Compatibility
This program has been tested on a Raspberry Pi 3b and a Raspberry Pi Zero W. When using a Pi Zero, you will likely need a USB hub to plug in the gamepad controller, keyboard, etc.

This program has been tested with a Logitech F310 Gamepad controller. Additional devices and gamepad controllers will be tested over time.

This program is written for Python version 3.
## Future Plans
In this release, only WIFI connectivity is supported. Bluetooth support will be added in a future release.

## Files
* config.json - JSON-formatted configuration file to set parameters for the application
* config.py - Python module to read and parse the contents of the JSON configuration file
* joystick.py - Python module to provide the interface to the gamepad controller
* logger.py - Python module to set up the logging facility for the application
* requirements.txt - Requirements file providing python package dependencies
* xrp_controller.py - Main python module that provides the interface to the XRP robot over a WIFI network. Module supports UDP and TCP socket connections to the XRP.

## Installation and Setup
It is highly recommended to install the application using a python virtual environment. I use the virtualenvwrapper utility to manage the python virtual environments. See [here](https://virtualenvwrapper.readthedocs.io/en/latest/) for information on virtualenvwrapper.

```
$ mkdir -p ~/GitHub
$ cd ~/GitHub
$ git clone https://github.com/kensthilaire/xrp-applications.git
$ cd xrp-applications/driver_station
$ mkvirtualenv xrp-control
$ pip3 install -r requirements.txt
```
Connect your gamepad controller to any USB connector on the Raspberry Pi.  

Currently, this program can communicate to the XRP over a WIFI network, with both the Raspberry Pi and the XRP attached to the same WIFI network. 

The XRP library itself supports both Station (STA) and Access Point (AP) modes. For STA mode, both the XRP and the Raspberry Pi will connect to a separate WIFI enabled device. For AP mode, the XRP will provide the WIFI access point and the Raspberry Pi will need to connect to the SSID advertised by the XRP.

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

**NOTE: Be sure that the config.json file is properly formatted JSON.

**TIP: Copy the default config.json file to a separate file (e.g. my_config.json), edit the file for the specific configuration and specify this JSON configuration file when invoking the control application (e.g. python xrp_controller.py -c my_config.json).

### Configuration Parameter Descriptions 
 * controller - must be set to `joystick`. Future versions of the application will likely support additional controller types.
 * xrp_ipaddr - used to specify the IP address of the XRP. You may remove this parameter if you want to specify the XRP IP address at the command line
 * port - used to define the UDP/TCP port number for the socket connection between the control application and the XRP. This port number should be greater than 5000 and less than 65534.
 * socket_type - specifies the type of socket connection, either TCP or UDP
 * debug - enables debug logging for additional output, set to `false` to disable verbose logging
    
## Running the XRP Controller
### Running The Program With Configuration File Settings
To run the application using the values as defined in the `config.json` file, simply run this command:

```
$ python xrp_controller
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
