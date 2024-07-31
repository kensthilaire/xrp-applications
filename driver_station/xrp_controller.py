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

from joystick_mgr import JoystickMgr

# dictionary of all the xbox controller buttons and controls. By enabling or disabling
# the controls, you can control how much extra traffic is sent down to the XRP.
controls = {
    'ButtonA':        { 'type': 'BUTTON', 'enabled': True },
    'ButtonB':        { 'type': 'BUTTON', 'enabled': True },
    'ButtonX':        { 'type': 'BUTTON', 'enabled': True },
    'ButtonY':        { 'type': 'BUTTON', 'enabled': True },
    'LeftBumper':     { 'type': 'BUTTON', 'enabled': True },
    'RightBumper':    { 'type': 'BUTTON', 'enabled': True },
    'Select':         { 'type': 'BUTTON', 'enabled': True },
    'Start':          { 'type': 'BUTTON', 'enabled': True },
    'LeftThumb':      { 'type': 'BUTTON', 'enabled': True },
    'RightThumb':     { 'type': 'BUTTON', 'enabled': True },
    'LeftTrigger':    { 'type': 'BUTTON', 'enabled': True },
    'RightTrigger':   { 'type': 'BUTTON', 'enabled': True },
    'LeftJoystickX':  { 'type': 'AXIS',   'enabled': True },
    'LeftJoystickY':  { 'type': 'AXIS',   'enabled': True },
    'RightJoystickX': { 'type': 'AXIS',   'enabled': True },
    'RightJoystickY': { 'type': 'AXIS',   'enabled': True },
    'HatX':           { 'type': 'HAT',    'enabled': True },
    'HatY':           { 'type': 'HAT',    'enabled': True },

    'LED':            { 'type': 'CUSTOM', 'enabled': True }
}

#
#
#
class XrpController():
    def __init__(self, socket_type='UDP', host='', port=9999):

        self.curr_values = {}

        self.host = host
        self.port = int(port)
        self.socket = None
        self.socket_type = socket_type.upper()

        self.gamepad_id = None

        self.initialize_client_socket()

    def shutdown(self):
        # Perform any necessary cleanup as part of shutdown
        pass

    def __str__(self):
        return 'XRP Address: %s:%d, Type: %s' % (self.host,self.port,self.socket_type)

    def initialize_client_socket(self):
        connected = True
        err = ''

        # create a socket based on the requested type
        if self.socket_type == 'UDP':
            logger.info( 'Creating UDP Client Connection to %s:%d' % (self.host,self.port) )
            self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        elif self.socket_type == 'TCP':
            logger.info( 'Creating TCP Client Connection to %s:%d' % (self.host,self.port) )
            while True:
                try:
                    self.socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                    self.socket.connect( (self.host,self.port) )
                    logger.info( 'Client Connection Established to %s:%d' % (self.host,self.port) )
                    break
                except ConnectionRefusedError:
                    logger.error( 'Error Connecting to %s:%d, Connection Refused' % (self.host,self.port) )
                    connected = False
                    err = 'Connection Refused'
                    break
                except OSError:
                    logger.error( 'Error Connecting to %s:%d, Check if XRP is running' % (self.host,self.port) )
                    connected = False
                    err = 'XRP Not Reachable'
                    break
                except:
                    logger.error( 'Unknown Error Connecting to %s:%d, Check if XRP is running' % (self.host,self.port) )
                    connected = False
                    err = 'XRP Connection Error'
                    break
        else:
            logger.error( 'Unknown Socket Type: %s' % (self.socket_type) )

        return connected,err

    def process_event( self, event ):
        try:
            self.send_event( event )
        except ConnectionResetError:
            logger.error( 'Server Connection Error from %s:%d, Restablishing connection' % (self.host,self.port) )
            self.initialize_client_socket()
        except ConnectionRefusedError:
            logger.error( 'Connection Refused Error from %s:%d, Restablishing connection' % (self.host,self.port) )
            self.initialize_client_socket()
        except ConnectionAbortedError:
            logger.error( 'Connection Aborted Error from %s:%d, Restablishing connection' % (self.host,self.port) )
            self.initialize_client_socket()
        except BrokenPipeError:
            logger.error( 'Client Connection Lost to %s:%d, Restablishing connection' % (self.host,self.port) )
            self.initialize_client_socket()
        except OSError:
            logger.error( 'Unknown OS Error from %s:%d, Restablishing connection' % (self.host,self.port) )
            self.initialize_client_socket()

    def send_event( self, event ):
        command = None
        name = event['name']
        try:
            control = controls[name]
            if control.get('enabled', False) == True:
                if control['type'] == 'AXIS':
                    # for the axis type, send the value rounded to the nearest 2 decimal points
                    value = event['rounded_value']
                    if self.curr_values.get(name, 0.0) != value:
                        # only send the command if the value has changed
                        self.curr_values[name] = value
                        command = '%s:%s:%f' % ('Event',name, value) 
                        logger.debug( 'Axis Type: %s, Value: %f' % (name,value) )
                elif control['type'] == 'BUTTON':
                    # for the button type, send the value reported by the button (1:PRESSED or 0:RELEASED)
                    value = event['value']
                    command = '%s:%s:%d' % ('Event',name, value) 
                    logger.debug( 'Button Type: %s, Value: %d' % (name,value) )
                elif control['type'] == 'HAT':
                    # for the hat type, send the value as an integer value
                    value = event['value']
                    command = '%s:%s:%d' % ('Event',name, value) 
                    logger.debug( 'Hat Type: %s, Value: %d' % (name,value) )
                elif control['type'] == 'CUSTOM':
                    value = event['value']
                    command = '%s:%s:%s' % ('Event',name, value) 
                    logger.debug( 'Custom Event Type: %s, Value: %s' % (name,value) )
                else:
                    logger.error( 'Unknown Event Type: %s' % name )

                if command:
                    logger.debug( 'Sending: %s' % command )
                    command += '\n'
                    if self.socket_type == 'TCP':
                        self.socket.sendall( command.encode('utf-8') )
                    elif self.socket_type == 'UDP':
                        self.socket.sendto( command.encode('utf-8'), (self.host,self.port) )

        except KeyError:
            pass

    def set_gamepad_id( self, gamepad_id ):
        self.gamepad_id = gamepad_id

    def get_gamepad_id(self):
        return self.gamepad_id

    def clear_gamepad_id(self):
        self.gamepad_id = None

def joystick_callback( event_type, gamepad_id ):
    if event_type == 'CONNECTED':
        if xrp_controllers:
            for controller in xrp_controllers:
                if controller.get_gamepad_id() == None:
                    logger.info( 'Binding Joystick %d to XRP controller' % gamepad_id )
                    joystick_mgr.bind_device(gamepad_id,controller)
                    break

def shutdown_handler(signum, frame):
    shutdown_all()
    sys.exit(0)

def shutdown_all():
    logger.info( 'Terminating XRP controller service' )
    if xrp_controllers:
        for controller in xrp_controllers:
            controller.shutdown()
        time.sleep(2)

if __name__ == '__main__':

    # install signal handlers to handle a shutdown request
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

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

        xrp_ipaddr = config.get('xrp_ipaddr',None)
        if xrp_ipaddr:
            name = 'XRP-%s' % xrp_ipaddr.split('.')[-1]
            logger.debug( 'Configuring %s at %s:%s' % (name,xrp_ipaddr,options.xrp_port) )
            xrp_devices.append( { 'name': name, 'ipaddr': xrp_ipaddr, 'port':int(options.xrp_port) } )
            
    # list of xrp_controllers instantiated as part of this application
    xrp_controllers = list()

    # initialize the joystick manager instance, binding each joystick to an XRP instance
    joystick_mgr = JoystickMgr()

    #
    # retrieve the list of joystick devices that are connected to this controller and 
    # create an XRP controller instance to assotiate with the joysticks.
    connected_joysticks = joystick_mgr.get_joysticks()

    logger.debug( 'Number of connected joysticks: %d' % len(connected_joysticks) )

    index = 0
    for joystick in connected_joysticks.values():
        if index < len(xrp_devices):
            xrp_config = xrp_devices[index]
            xrp_ipaddr = xrp_config.get('ipaddr', 'localhost')
            xrp_port = xrp_config.get('port', 9999)

            # Create the XRP controller instance to service this XRP device
            logger.debug( 'Creating XRP instance %s, Type: %s, Host: %s' % (xrp_config.get('name','Unknown'), socket_type, xrp_ipaddr) )
            controller = XrpController(socket_type=socket_type, host=xrp_ipaddr, port=xrp_port)
            xrp_controllers.append( controller )

            # Bind the XRP controller to the joystick instance. All events received from that joystick will be handled by the
            # controller instance.
            joystick_mgr.bind_device(joystick.get_instance_id(),controller)

            index += 1
        else:
            # we have more connected joysticks than XRP devices
            break

    # launch the joystick manager run loop to process events from the gamepad controllers. This function will not return until
    # the program is terminated
    joystick_mgr.run( mgmt_callback=joystick_callback)

    # perform any final cleanup as part of the shutdown
    shutdown_all()
