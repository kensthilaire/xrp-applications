#!/usr/bin/env python3

import argparse
import logging
import random
import socket
import signal
import sys
import threading
import time

from bluetooth_manager import BluetoothManager

from adafruit_ble.services.nordic import UARTService
from bleak.exc import BleakError, BleakDBusError

from config import read_config

from logger import logger

import joystick
from joystick import Joystick

# dictionary of all the xbox controller buttons and controls. By enabling or disabling
# the controls, you can control how much extra traffic is sent down to the XRP.
controls = { 
    'ButtonA':        { 'abbr': 'BA', 'type': 'BUTTON', 'enabled': True },
    'ButtonB':        { 'abbr': 'BB', 'type': 'BUTTON', 'enabled': True  },
    'ButtonX':        { 'abbr': 'BX', 'type': 'BUTTON', 'enabled': True  },
    'ButtonY':        { 'abbr': 'BY', 'type': 'BUTTON', 'enabled': True  },
    'LeftBumper':     { 'abbr': 'LB', 'type': 'BUTTON', 'enabled': True  },
    'RightBumper':    { 'abbr': 'RB', 'type': 'BUTTON', 'enabled': True  },
    'Select':         { 'abbr': 'SEL', 'type': 'BUTTON', 'enabled': True  },
    'Start':          { 'abbr': 'ST', 'type': 'BUTTON', 'enabled': True  },
    'LeftThumb':      { 'abbr': 'LTH', 'type': 'BUTTON', 'enabled': True  },
    'RightThumb':     { 'abbr': 'RTH', 'type': 'BUTTON', 'enabled': True  },
    'LeftJoystickX':  { 'abbr': 'LX', 'type': 'AXIS',   'enabled': True  },
    'LeftJoystickY':  { 'abbr': 'LY', 'type': 'AXIS',   'enabled': True  },
    'LeftTrigger':    { 'abbr': 'LT', 'type': 'AXIS',   'enabled': True  },
    'RightJoystickX': { 'abbr': 'RX', 'type': 'AXIS',   'enabled': True  },
    'RightJoystickY': { 'abbr': 'RY', 'type': 'AXIS',   'enabled': True  },
    'RightTrigger':   { 'abbr': 'RT', 'type': 'AXIS',   'enabled': True  },
    'HatX':           { 'abbr': 'HX', 'type': 'AXIS',   'enabled': True  },
    'HatY':           { 'abbr': 'HY', 'type': 'AXIS',   'enabled': True  }
}                   


#
# class to implement the XRP controller. This class is derived from the Joystick class
# and supports an Xbox Controller connected via USB to a Raspberry Pi
#
class XrpController(Joystick):
    def __init__(self, path=None, name='NoName', protocol='UDP', host='', port=9999, ble_manager=None):
        super().__init__(path)

        self.shutdown_flag = False

        self.path = path
        self.name = name
        self.host = host
        self.port = int(port)
        self.socket = None
        self.protocol = protocol.upper()
        self.connection = None

        self.curr_values = {}

        self.ble_manager = ble_manager


    def __str__(self):
        return 'XRP Address: %s:%d, Type: %s' % (self.host,self.port,self.protocol)

    def initialize_client(self):
        connected = True
        err = ''

        # create a socket based on the requested type
        if self.protocol == 'UDP':
            logger.info( 'Creating UDP Client Connection to %s:%d' % (self.host,self.port) )
            self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        elif self.protocol == 'TCP':
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
                    err = 'XRP TCP Connection Error'
                    break
        elif self.protocol == 'BLUETOOTH':
            while self.shutdown_flag == False:
                self.connection = None
                logger.info( 'Finding Bluetooth Device: %s' % (self.name) )
                device_entry = self.ble_manager.get_device(self.name)
                if device_entry:
                    logger.debug('Bluetooth Device Found: %s' % (self.name) )
                    self.connection = self.ble_manager.connect_device(device_entry)

                    if self.connection:
                        if UARTService in self.connection:
                            logger.info( 'Connected To Bluetooth Device: %s' % (self.name) )
                            self.uart_service = self.connection[UARTService]
                        else:
                            logger.info( 'Bluetooth Device: %s Does NOT Support UART Service' % (self.name) )
                            self.connection.disconnect()
                            self.uart_service = None
                            connected = False
                            err = 'UART Service Not Supported'
                        break
                    else:
                        logger.info( 'Could Not Establish Connection To Bluetooth Device: %s' % (self.name) )
                        connected = False
                        err = 'XRP Bluetooth Connection Error'
                        break
                else:
                    logger.debug('Bluetooth Device %s Not Discovered' % self.name)
                    time.sleep(2)
        else:
            err = 'Unknown Protocol Type: %s' % (self.protocol)
            logger.error( err )
            connected = False

        return connected,err

    def shutdown( self, *args ):
        self.shutdown_flag = True
        self.terminate_read_loop = True
        logger.info( 'Shutdown complete.' )

    def send_event( self, event ):
        command = None
        event_name = event['name']
        try:
            control = controls[event_name]
            # cmd_type of 'EV' is a control event
            cmd_type = 'EV'
            name = control['abbr']

            if control.get('enabled', False) == True:
                if control['type'] == 'AXIS':
                    # for the axis type, send the value to the nearest tenth
                    value = event['rounded_value']

                    # As a way to reduce the packets being sent to the XRP, only send changes
                    # to the most recent value and only send even values
                    #
                    # Reducing the transmitted packets helps with response time and reduces
                    # controller lag. As we refine the packet intereface between the control 
                    # application and the XRP to increase the throughput, we may remove the
                    # packet throughput constraints 
                    if value == self.curr_values.get(name,0) or int(value*10) % 2 != 0:
                        return
                    self.curr_values[name] = value
                        
                    command = '%s:%s:%0.2f' % (cmd_type,name, value) 
                elif control['type'] == 'BUTTON':
                    # for the button type, send the value reported by the button (1:PRESSED or 0:RELEASED)
                    value = event['value']
                    command = '%s:%s:%d' % (cmd_type,name, value) 
                else:
                    logger.error( 'Unknown Event Type: %s' % name )

                if command:
                    logger.debug( 'Sending: %s' % command )
                    command += '\n'
                    if self.protocol == 'UDP':
                        self.socket.sendto( command.encode('utf-8'), (self.host,self.port) )
                    elif self.protocol == 'TCP':
                        self.socket.sendall( command.encode('utf-8') )
                    elif self.protocol == 'BLUETOOTH':
                        self.uart_service.write( command.encode('utf-8') )

        except KeyError:
            pass

    def joystick_control(self):
        err = ''
        try:
            for event in self.gamepad.read_loop():
                try:
                    decoded_event = self.decode_event( event )
                    self.send_event( decoded_event )
                except ConnectionResetError:
                    logger.error( 'Server Connection Error from %s:%d, Restablishing connection' % (self.host,self.port) )
                    connected, err = self.initialize_client()
                    if not connected:
                        logger.info( 'Connection Could Not Be Restablished, terminating joystick processing' )
                        err = 'Connection Reset'
                        break
                except BrokenPipeError:
                    logger.error( 'Client Connection Lost to %s:%d, Restablishing connection' % (self.host,self.port) )
                    connected, err = self.initialize_client()
                    if not connected:
                        logger.info( 'Connection Could Not Be Restablished, terminating joystick processing' )
                        err = 'Broken Pipe'
                        break
                except BleakError:
                    logger.error( 'Bluetooth Connection Lost to %s, Restablishing connection' % (self.name) )
                    attempts = 0
                    connected = False
                    while not connected and attempts < 5:
                        try:
                            connected, err = self.initialize_client()
                        except AttributeError:
                            logger.debug('Attribute error, delay then retry')
                            time.sleep(1)
                            attempts += 1
                        except BleakDBusError:
                            # this error may be generated if we attempt to scan for multiple XRP devices over 
                            # bluetooth at the same time. The solution for now is to catch the exception and
                            # retry after a slight delay
                            time.sleep(1)
                            attempts += 1
                    if not connected:
                        logger.info( 'Connection Could Not Be Restablished, terminating joystick processing' )
                        err = 'Connection Lost'
                        break

                if self.terminate_read_loop:
                    logger.info( 'Terminating Controller Read Loop' )
                    break
        except OSError:
            logger.error( 'Controller Error Detected, terminating joystick processing' )

        return err


#
# Simple service routine that invokes the controller method that runs the joystick control loop
#
def controller_service( controller ):
    global mutex
    logger.info( 'XRP Controller Service Starting For Device: %s' % str(controller) )

    connected = False
    while not connected:
        try:
            connected, err = controller.initialize_client()
        except AttributeError:
            logger.debug('Attribute error, delay then retry')
        except BleakDBusError:
            # this error may be generated if we attempt to scan for multiple XRP devices over 
            # bluetooth at the same time. The solution for now is to catch the exception and
            # retry after a slight delay
            logger.debug('Bleak DBus Error: Pausing to allow other Bluetooth connections')

        if not connected:
            delay = random.randint(5,10)
            logger.debug('Pausing %d seconds to allow other connections' % delay)
            time.sleep(delay)

    if connected:
        err = controller.joystick_control()

    logger.info( 'XRP Controller Service Terminated For Device: %s' % str(controller) )
    return err

#
#
#
def shutdown_handler(signum, frame):
    shutdown_all()
    time.sleep(3)
    sys.exit(0)

def shutdown_all():
    logger.info( 'Terminating controller service threads' )
    shutdown_flag = True
    for controller in xrp_controllers:
        controller.shutdown()
    if ble_manager:
        ble_manager.shutdown()

if __name__ == '__main__':

    # install signal handlers to handle a shutdown request
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    #
    # parse out the command arguments
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--bluetooth', action='store_true', dest='bluetooth', default=False)
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', default=False)
    parser.add_argument('-c', '--config', action='store', dest='config', default='config.json')
    parser.add_argument('-p', '--port', action='store', dest='port', default='9999')
    parser.add_argument('-t', '--protocoltype', action='store', dest='protocol', default=None)
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

    # if one or more XRPs are specified at the command line, use them instead of the configured
    # devices. Multiple XRPs can be specified as a comma-separated list
    xrp_devices = list()
    if options.xrp_ipaddr:
        xrp_ipaddresses = options.xrp_ipaddr.split(',')
        for index,xrp in enumerate(xrp_ipaddresses):
            name = 'XRP-%d' % index
            logger.debug( 'Configuring %s at %s:%s' % (name,xrp,options.port) )
            xrp_devices.append( { 'name': name, 'ipaddr': xrp, 'port':int(options.port) } )
    else:
        # retrieve the set of devices configured for this controller instance
        xrp_devices = config.get('devices', list())
        logger.debug( 'Number of configured devices: %d' % len(xrp_devices) )

    ble_manager = None
    if options.bluetooth or config.get('bluetooth',False) == True:
        ble_manager = BluetoothManager()

        for device in xrp_devices:
            ble_manager.add_device_to_scan(device.get('name', 'NoName'))
    #
    # retrieve the list of joystick devices that are connected to this controller and 
    # create an XRP controller instance to associate with the joysticks.
    xrp_controllers = list()
    connected_joysticks = joystick.get_joysticks()
    logger.debug( 'Number of connected joysticks: %d' % len(connected_joysticks) )

    for index, joystick in enumerate(connected_joysticks):
        if index < len(xrp_devices):
            # retrieve the device configuration
            xrp_config = xrp_devices[index]
            if xrp_config.get('enabled',True) == True:
                xrp_name = xrp_config.get('name', 'NoName')
                xrp_ipaddr = xrp_config.get('ipaddr', None)
                xrp_port = xrp_config.get('port', None)
                xrp_protocol = xrp_config.get('protocol', None)

                # override device settings if specified at the command line
                if options.port:
                    xrp_port = options.port
                if options.protocol:
                    xrp_protocol = options.protocol.upper()

                # Create the XRP controller instance
                controller = XrpController(path=joystick.path, name=xrp_name, protocol=xrp_protocol, host=xrp_ipaddr, port=xrp_port, ble_manager=ble_manager)
                controller_thread = threading.Thread( target=controller_service, args=(controller,), daemon=True )
                xrp_controllers.append( controller )
                controller_thread.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info( 'Initiating shutdown from keyboard' )
            ble_manager.shutdown()
            shutdown_all()
        
    print( 'XRP Control application terminated.' )

