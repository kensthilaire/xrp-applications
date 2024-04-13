#!/usr/bin/env python3

import argparse
import logging
import socket
import signal
import sys
import threading
import time

from config import read_config

from logger import logger

import joystick
from joystick import Joystick

# dictionary of all the xbox controller buttons and controls. By enabling or disabling
# the controls, you can control how much extra traffic is sent down to the XRP.
controls = {
    'ButtonA':        { 'type': 'BUTTON', 'enabled': True },
    'ButtonB':        { 'type': 'BUTTON', 'enabled': True  },
    'ButtonX':        { 'type': 'BUTTON', 'enabled': True  },
    'ButtonY':        { 'type': 'BUTTON', 'enabled': True  },
    'LeftBumper':     { 'type': 'BUTTON', 'enabled': True  },
    'RightBumper':    { 'type': 'BUTTON', 'enabled': True  },
    'Select':         { 'type': 'BUTTON', 'enabled': True  },
    'Start':          { 'type': 'BUTTON', 'enabled': True  },
    'LeftThumb':      { 'type': 'BUTTON', 'enabled': True  },
    'RightThumb':     { 'type': 'BUTTON', 'enabled': True  },
    'LeftJoystickX':  { 'type': 'AXIS',   'enabled': True  },
    'LeftJoystickY':  { 'type': 'AXIS',   'enabled': True  },
    'LeftTrigger':    { 'type': 'AXIS',   'enabled': True  },
    'RightJoystickX': { 'type': 'AXIS',   'enabled': True  },
    'RightJoystickY': { 'type': 'AXIS',   'enabled': True  },
    'RightTrigger':   { 'type': 'AXIS',   'enabled': True  },
    'HatX':           { 'type': 'AXIS',   'enabled': True  },
    'HatY':           { 'type': 'AXIS',   'enabled': True  }
}

#
# class to implement the XRP controller. This class is derived from the Joystick class
# and supports an Xbox Controller connected via USB to a Raspberry Pi
#
class XrpController(Joystick):
    def __init__(self, path=None, socket_type='UDP', host='', port=9999):
        super().__init__(path)

        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        self.shutdown = False

        self.host = host
        self.port = int(port)
        self.socket = None
        self.socket_type = socket_type

    def initialize_client_socket(self):
        # create a socket based on the requested type
        logger.info( 'Creating Client Connection to %s:%d' % (self.host,self.port) )
        if self.socket_type == 'UDP':
            self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        elif self.socket_type == 'TCP':
            while not self.shutdown:
                try:
                    self.socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                    self.socket.connect( (self.host,self.port) )
                    logger.info( 'Client Connection Established to %s:%d' % (self.host,self.port) )
                    break
                except ConnectionRefusedError:
                    time.sleep(5)
                    logger.error( 'Error Connecting to %s:%d, Retrying' % (self.host,self.port) )
                except OSError:
                    time.sleep(5)
                    logger.error( 'Error Connecting to %s:%d, Check if XRP is running' % (self.host,self.port) )

    def shutdown( self, *args ):
        logger.info( 'Shutdown complete.' )

        sys.exit(0)

    def send_event( self, event ):
        command = None
        name = event['name']
        try:
            control = controls[name]

            if control.get('enabled', False) == True:
                if control['type'] == 'AXIS':
                    # for the axis type, send the value rounded to the nearest 2 decimal points
                    value = event['rounded_value']
                    command = '%s:%s:%f' % ('Event',name, value) 
                elif control['type'] == 'BUTTON':
                    # for the button type, send the value reported by the button (1:PRESSED or 0:RELEASED)
                    value = event['value']
                    command = '%s:%s:%d' % ('Event',name, value) 
                else:
                    logger.error( 'Unknown Event Type: %s' % name )

                if command:
                    logger.debug( 'Sending: %s' % command )
                    command += '\n'
                    if self.socket_type == 'UDP':
                        self.socket.sendto( command.encode('utf-8'), (self.host,self.port) )
                    if self.socket_type == 'TCP':
                        self.socket.sendall( command.encode('utf-8') )

        except KeyError:
            pass

    def joystick_control(self):
        try:
            for event in self.gamepad.read_loop():
                try:
                    decoded_event = self.decode_event( event )
                    self.send_event( decoded_event )
                except ConnectionResetError:
                    logger.error( 'Server Connection Error from %s:%d, Restablishing connection' % (self.host,self.port) )
                    self.initialize_client_socket()
                except BrokenPipeError:
                    logger.error( 'Client Connection Lost to %s:%d, Restablishing connection' % (self.host,self.port) )
                    self.initialize_client_socket()
        except OSError:
            logger.error( 'Controller Error Detected, terminating joystick processing' )

#
# Simple service routine that invokes the controller method that runs the joystick control loop
#
def controller_service( controller ):
    controller.initialize_client_socket()
    controller.joystick_control()


if __name__ == '__main__':

    #
    # parse out the command arguments
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', default=False)
    parser.add_argument('-c', '--config', action='store', dest='config', default='config.json')
    parser.add_argument('-p', '--port', action='store', dest='xrp_port', default='9999')
    parser.add_argument('-s', '--socket', action='store', dest='socket_type', default=None)
    parser.add_argument('-x', '--xrp', action='store', dest='xrp_ipaddr', default=None)
    options = parser.parse_args()

    #
    # Read the config file
    config = read_config( filename=options.config )

    logger.debug( 'Setting Log Level:\n' )
    # set the log level to debug if requested
    if options.debug or config.get('debug',False) == True:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # override the socket type setting if specified at the command line
    if options.socket_type:
        socket_type = options.socket_type.upper()
    else:
        socket_type = config.get('socket_type', 'TCP').upper()

    # if one or more XRPs are specified at the command line, use them instead of the configured
    # devices. Multiple XRPs can be specified as a comma-separated list
    xrp_devices = list()
    if options.xrp_ipaddr:
        xrp_ipaddresses = options.xrp_ipaddr.split(',')
        for index,xrp in enumerate(xrp_ipaddresses):
            name = 'XRP-%d' % index
            logger.debug( 'Configuring %s at %s:%s' % (name,xrp,options.xrp_port) )
            xrp_devices.append( { 'name': name, 'ipaddr': xrp, 'port':int(options.xrp_port) } )
    else:
        # retrieve the set of devices configured for this controller instance
        xrp_devices = config.get('devices', list())

    #
    # retrieve the list of joystick devices that are connected to this controller and 
    # create an XRP controller instance to assotiate with the joysticks.
    controller_threads = list()
    connected_joysticks = joystick.get_joysticks()
    for index, joystick in enumerate(connected_joysticks):
        if index < len(xrp_devices):
            xrp_config = xrp_devices[index]
            xrp_ipaddr = xrp_config.get('ipaddr', 'localhost')
            xrp_port = xrp_config.get('port', 9999)

            # Create the XRP controller instance
            controller = XrpController(path=joystick.path, socket_type=socket_type, host=xrp_ipaddr, port=xrp_port)
            controller_thread = threading.Thread( target=controller_service, args=(controller,), daemon=True )
            controller_threads.append( controller_thread )
            controller_thread.start()

    for index, thread in enumerate(controller_threads):
        try:
            thread.join()
        except KeyboardInterrupt:
            break
 
