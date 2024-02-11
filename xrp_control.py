
# available variables from defaults: left_motor, right_motor, drivetrain,
#      imu, rangefinder, reflectance, servo_one, board, webserver
from XRPLib.defaults import *

import json
import network
import socket
import time

#
# Function to read a JSON formatted config file with the XRP configuration
# information to set up the network interface and other control parameters
#
def read_config( filename='config.json' ):
    data = ''

    with open( filename ) as fd:
        try:
            data = json.load(fd)
        except ValueError as err:
            print( err )
    return data

# Set of control events that could be sent from the driver station application
# to the XRP. These events correspond to the Xbox Controller buttons and
# axis controls.
#
# At present, this dictionary is included to define all the expected events. 
# Additional functionality will be added to make more use of the dictionary.
#
control_events = {
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
# Main control class for the XRP application.
#
class XrpControl():
    def __init__(self, config):
        # save the configuration within this object
        self.config = config
        
        # set up the network based on the specified configuration
        self.setup_network()

        # initialize certain variables used to control the robot
        self.current_speed = 0.0
        self.current_turn = 0.0

    #
    # Function will set up the network connection based on the 
    # configuration.
    #
    # Currently, only station (STA) mode is supported. Access point (AP)
    # mode will be added, along with support for Bluetooth
    #
    # Additionally, initially UDP transport is being used for simplicity
    # and efficiency. Testing to date has shown that the unreliable nature
    # of UDP sockets has not been an issue. But, TCP will be added at some
    # point for completeness.
    #
    def setup_network(self):
        if self.config['network_type'] == 'STA':
            sta_if = network.WLAN(network.STA_IF)
            sta_if.active(True)

            sta_if.connect(self.config['ssid'], self.config['wifi_passcode'])
            if sta_if.isconnected():
                network_config = sta_if.ifconfig()
                self.my_ipaddr = network_config[0]
                self.my_port = self.config['listening_port']

        if self.config['socket_type'] == 'UDP':
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind( (self.my_ipaddr, self.my_port) )
            print( 'Connected to WIFI, IP Address: %s, Port: %d' % (self.my_ipaddr,self.my_port) )

    #
    # Function will read from the network and return the command and data associated with the
    # command.
    #
    # A simple command format has been specified of the form:
    #   <command>:<arg1>:<arg2>:etc
    #
    # The command string is decoded and split on the colon(':') to create a list of command
    # tokens that are returned to the caller
    #
    def get_command(self):
        if self.config['socket_type'] == 'UDP':
            data,addr=self.socket.recvfrom(1024)
            print( 'Received: ', str(data), ' From: ', addr )
            tokens = data.decode('utf-8').split(':')
            return tokens[0],tokens[1:]
        else:
            return None,None

    #
    # Function processes the Event command, interpreting the event type and 
    # invoking the appropriate robot control behavior specified by the event
    #
    def process_event( self, event, args ):
        #print( 'Processing Event: %s, Args %s' % (event,str(args)))
        if event == 'LeftJoystickY':
            # save off the current speed for reference
            self.current_speed = float(args[0]) * -1.0
            # update the drivetrain with the new speed and turn settings
            drivetrain.arcade( self.current_speed, self.current_turn )
        elif event == 'RightJoystickX':
            # save off the current turning setting for reference
            self.current_turn = float(args[0]) * -1.0
            # update the drivetrain with the new speed and turn settings
            drivetrain.arcade( self.current_speed, self.current_turn )
        elif event == 'LeftBumper':
            # Open (lower) the arm when the left bumper is pressed
            if int(args[0]) == 1:
                servo_one.set_angle( 0 )
        elif event == 'RightBumper':
            # Close (raise) the arm when the right bumper is pressed
            if int(args[0]) == 1:
                servo_one.set_angle( 180 )
        else:
            # add more event handling operations here...
            pass

if __name__ == '__main__':

    # read the config.json file located in the base directory
    config = read_config()

    # create the instance of the XRP controller
    controller = XrpControl( config )

    # jump into the control loop to listen for events from the
    # network
    while True:
        command,args = controller.get_command()
        if command != None:
            if command == 'Event':
                controller.process_event( args[0], args[1:] )
            else:
                print('Ignoring Unexpected Command: %s, Args: %s' % (command,str(args)) )

