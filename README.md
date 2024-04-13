# XRP Control Applications
This repository contains a set of python programs to control the XRP robot. These programs are compatible with MicroPython and are intended to be uploaded to the XRP robot using the XRP Integrated Development Environment (IDE) located at [xrpcode.wpi.edu](http://xrpcode.wpi.edu).

This repository also contains a driver station application that runs on a Raspberry Pi and allows an XRP to be driver controlled using a gamepad controller.

## Files
* config.json - JSON-formatted configuration file to set parameters for the XRP robot
* xrp_control.py - Python module containing the base class definition for the XRP control application
* xrp_servo_triggers.py - Python module containing derived class definition that adds trigger support for the servo arm
* xrp_tank.py - Python module containing derived class definition that supports simple tank drive for the XRP
* driver_station - Directory containing the drive station application for the Raspberry Pi
##

