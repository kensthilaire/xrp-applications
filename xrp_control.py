
# available variables from defaults: left_motor, right_motor, drivetrain,
#      imu, rangefinder, reflectance, servo_one, board, webserver
from XRPLib.defaults import *

import json
import network
import socket
import time
import sys

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
        
        board.led_blink(2)
        # set up the network based on the specified configuration
        self.setup_network()
        board.led_off()
        
        # initialize the network sockets that we'll use to read command data
        self.initialize_sockets()

        # initialize some variables used to control the robot
        self.current_speed = 0.0
        self.current_turn = 0.0
        self.partial_cmd_buffer = ''

    #
    # Function will set up the network connection based on the 
    # configuration.
    #
    # Currently, Station (STA) and Access Point (AP) modes are supported.
    # Bluetooth support will be added in future support
    #
    def setup_network(self):
        MAX_ATTEMPTS = 20
        num_attempts = 0

        if self.config['network_type'] == 'STA':
            # Station mode
            sta_if = network.WLAN(network.STA_IF)
            sta_if.active(True)
            sta_if.connect(self.config['ssid'], self.config['wifi_passcode'])

            while num_attempts < MAX_ATTEMPTS:
                if sta_if.isconnected():
                    network_config = sta_if.ifconfig()
                    self.my_ipaddr = network_config[0]
                    print( 'Connected to WIFI, IP Address: %s' % (self.my_ipaddr) )
                    break
                else:
                    # increment the number of attempts, then pause and retry. We have seen the XRP 
                    # needing some time following powerup before it will successfully connect to the
                    # network
                    num_attempts += 1
                    time.sleep(1)

        elif self.config['network_type'] == 'AP':
            # Access Point mode
            ap_if = network.WLAN(network.AP_IF)
            ap_if.config(essid=self.config['ssid'], password=self.config['wifi_passcode'])
            ap_if.active(True)

            while num_attempts < MAX_ATTEMPTS:
                if ap_if.active():
                    network_config = ap_if.ifconfig()
                    self.my_ipaddr = network_config[0]
                    print( 'WIFI Access Point Activated, IP Address: %s' % (self.my_ipaddr) )
                    break
                else:
                    # increment the number of attempts, then pause and retry. We have seen the XRP 
                    # needing some time following powerup before it will successfully connect to the
                    # network
                    num_attempts += 1
                    time.sleep(1)
        else:
            print( 'Unsupported Network Mode Requested: %s' % self.config['network_type'] )

        if num_attempts >= MAX_ATTEMPTS:
            print( 'Unable to set up the network for %s mode' % self.config['network_type'] )
            sys.exit(0)

    #
    # Function will initialize the local listening socket based on the configuration. Two types of
    # sockets are supported: UDP (User Datagram Protocol) and TCP (Transmission Control Protocol). 
    # UDP sockets are connectionless and provide an efficient way to pass data. UDP sockets are 
    # "unreliable" in that delivery is not guaranteed, so some packet loss may occur. TCP sockets, on 
    # the other hand, are connection-oriented and data delivery is guaranteed. There is additional
    # overhead with TCP sockets which may result in delays.
    #
    # For the XRP, either UDP or TCP sockets should work just fine. The defined control protocol uses
    # short messages between the driver station control application and the XRP, so the observed behavior
    # will likely be similar between the two socket protocols.
    # 
    def initialize_sockets(self):
        self.my_port = self.config['listening_port']

        if self.config['socket_type'] == 'UDP':
            self.read_commands = self.read_udp_commands

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind( (self.my_ipaddr, self.my_port) )
            self.socket.settimeout(5)
            print( 'Created UDP socket to receive commands')
        elif self.config['socket_type'] == 'TCP':
            self.connection = None
            self.read_commands = self.read_tcp_commands

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind( (self.my_ipaddr, self.my_port) )
            self.socket.listen(1)
            print( 'Created TCP socket to listen for connections')

    #
    # Set of functions that read from the network and return the command and data associated with the
    # command.
    #
    # A simple command format has been specified of the form:
    #   <command>:<arg1>:<arg2>:etc
    #
    # The command string is decoded and split on the colon(':') to create a list of command
    # tokens that are returned to the caller. Note that each command is terminated by a newline '\n'
    #
    def read_udp_commands(self):
        commands = []
        try:
            data,addr=self.socket.recvfrom(1024)
            #print( 'Received: ', str(data), ' From: ', addr )
            commands = data.decode('utf-8').split('\n')

            # discard the last element in the commands list, which should be an empty string
            # for a properly formed command string
            commands.pop()
        except OSError:
            commands = ['ReadTimeout']
        return commands

    def read_tcp_commands(self):
        commands = []
        try:
            if not self.connection:
                self.connection, self.client_address = self.socket.accept()
                self.connection.settimeout(5)
                print( 'Connection accepted from %s' % str(self.client_address))

            data=self.connection.recv(1024)
            #print( 'Received: ', str(data) )

            decoded_data = self.partial_cmd_buffer + data.decode('utf-8')
            
            if decoded_data:
                print( 'Decoded Received: ', decoded_data )

                # split the decoded data into separate commands delimited by a newline
                commands = decoded_data.split('\n')

                # for TCP connections, it is possible that the received data may contain a partial
                # command, which will be the last item in the commands list. We'll store that last
                # item as the partial command so that we can attach the next received data to the
                # partial command string.
                self.partial_cmd_buffer = commands.pop()
            else:
                print( 'Client connection error, closing socket')
                self.connection.close()
                self.connection = None
        except OSError:
            commands = ['ReadTimeout']
        return commands

    
    #
    # Function represents the main processing loop for the XRP controller. This function 
    # reads commands from the network interface and invokes the command procesing to 
    # control the robot.
    #
    def run(self):
        while True:
            commands = self.read_commands()
            for command in commands:
                tokens = command.split(':')
                if tokens[0] == 'Event':
                    self.process_event( tokens[1], tokens[2:] )
                elif command == 'ReadTimeout':
                    # If the read times out, then no commands have been received from the
                    # driver station in awhile. We have seen the drive station not totally 
                    # zero the speed/turn when the controls are released and this clause 
                    # will handle that condition and stop any residual motion.
                    self.stop_movement()
                else:
                    print('Ignoring Unexpected Command Type: %s, Args: %s' % (tokens[0],str(tokens[1:])) )

    #
    # Function processes the Event command, interpreting the event type and 
    # invoking the appropriate robot control behavior specified by the event
    #
    # OVERLOAD THIS FUNCTION IN A DERIVED CLASS TO MODIFY THE BEHAVIOR FOR
    # YOUR XRP CONFIGURATION
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

    #
    # Simple function for force the XRP to stop moving. This function is used to handle cases
    # where the XRP robot continues to move following a command invocation.
    #
    def stop_movement(self):
        self.current_speed = 0.0
        self.current_turn = 0.0
        drivetrain.arcade( self.current_speed, self.current_turn )
        

if __name__ == '__main__':

    # read the config.json file located in the base directory
    config = read_config()

    # create the instance of the XRP controller and launch the run loop
    controller = XrpControl( config ).run()

