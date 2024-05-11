
# available variables from defaults: left_motor, right_motor, drivetrain,
#      imu, rangefinder, reflectance, servo_one, board, webserver
from XRPLib.defaults import *
from XRPLib.pid import PID


import asyncio
import json
import machine
import network
import socket
import sys
import time
import urequests as requests
import _thread

from ble_uart_stream import BLEUARTStream

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

#
# Function to retrieve a string representation of the unique hardware ID 
# of the connected XRP
#
def get_id(short_id=False):
    id = ''
    s = machine.unique_id()
    for b in s : id += str(hex(b)[2:])
    if short_id:
        id = id[11:]
    return id
    

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

event_map = {
    'BA': 'ButtonA',
    'BB': 'ButtonB',
    'BX': 'ButtonX',
    'BY': 'ButtonY',
    'LB': 'LeftBumper',
    'RB': 'RightBumper',
    'SEL': 'Select',
    'ST': 'Start',
    'LTH': 'LeftThumb',
    'RTH': 'RightThumb',
    'LX': 'LeftJoystickX',
    'LY': 'LeftJoystickY',
    'LT': 'LeftTrigger',
    'RX': 'RightJoystickX',
    'RY': 'RightJoystickY',
    'RT': 'RightTrigger',
    'HX': 'HatX',
    'HY': 'HatY'
}

#
# Main control class for the XRP application.
#
class XrpControl():
    def __init__(self, config, application='XRP_Base'):
        print( '\nInitializing XRP...')
        
        # save the configuration within this object
        self.config = config
        
        # retrieve and save the unique machine ID
        self.id = get_id()
        print( 'XRP Id: %s' % self.id)
        
        # set up the network based on the specified configuration
        # flash the LED on the pico to indicate that we're connecting to the network
        board.led_blink(2)
        self.setup_network()
        board.led_off()
        
        # initialize some variables used to control the robot
        self.current_speed = 0.0
        self.current_turn = 0.0
        self.desired_heading = 0.0
        self.reset_heading = True
        self.partial_cmd_buffer = ''
        
        self.max_angle = 180
        self.min_angle = 0
        self.servos = ( {'servo': servo_one, 'angle':0},{'servo': servo_two, 'angle':0} )
        self.curr_servo = 0
        
        self.status = 'Initialized'
        self.shutdown = False
        self.status_reported = 0
        self.application = application
        self.ble_connection = 'Uninitialized'
        
        # if an FMS is configured, then attempt to register this device with the FMS
        self.fms_configured = False
        fms_config = self.config.get('fms', None)
        if fms_config:
            for fms in fms_config:
                if fms.get('enabled', False) == True:
                    self.fms_configured = True
                    if self.register(fms['url_base']) == True:
                        break

        self.imu_assist = False
        xrp_settings = self.config.get('settings', None)
        if xrp_settings:
            self.imu_assist = xrp_settings.get('imu_assist', False)

    #
    # Utility function that will set the angle of the selected servo, saving
    # the current angle position
    #
    def set_servo_angle( self, angle ):
        self.servos[self.curr_servo]['servo'].set_angle( angle )
        self.servos[self.curr_servo]['angle'] = angle

    #
    # Utility function to retrieve the current angle position of the selected
    # servo
    #
    def get_servo_angle( self ):
        return self.servos[self.curr_servo]['angle']
        
    #
    # Function will set up the network connection based on the 
    # configuration.
    #
    # Currently, Station (STA) and Access Point (AP) modes are supported.
    # Bluetooth support will be added in future support
    #
    def setup_network(self):
        MAX_ATTEMPTS = 20
        networks = self.config['networks']
        for network_config in networks:
            num_attempts = 0
            if network_config['enabled']:
                if network_config['network_type'] == 'STA':
                    # Station mode
                    print( 'Connecting to WIFI network: %s' % network_config['ssid'])
                    sta_if = network.WLAN(network.STA_IF)
                    sta_if.active(True)
                    sta_if.connect(network_config['ssid'], network_config['wifi_passcode'])

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
                            
                    if sta_if.isconnected():
                        break
                    else:
                        print( 'Error connecting to WIFI network: %s' % network_config['ssid'] )
                elif network_config['network_type'] == 'AP':
                    # Access Point mode
                    print( 'Setting up access point: %s' % network_config['ssid'])
                    ap_if = network.WLAN(network.AP_IF)
                    ap_if.config(essid=network_config['ssid'], password=network_config['wifi_passcode'])
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
                            
                    if ap_if.active():
                        break
                    else:
                        print( 'Error setting up access point: %s' % network_config['ssid'])
                else:
                    print( 'Unsupported Network Mode Requested: %s' % network_config['network_type'] )

        if num_attempts >= MAX_ATTEMPTS:
            print( 'Unable to set up the network for %s mode' % network_config['network_type'] )
            sys.exit(0)

    #
    # Function will initialize the local server socket based on the configuration. Two types of
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
    async def server_task(self):
        server_config = self.config['server']
        self.my_port = server_config['listening_port']

        if server_config['socket_type'] == 'UDP':
            self.read_commands = self.read_udp_commands

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind( (self.my_ipaddr, self.my_port) )
            self.socket.settimeout(5)
            print( 'Created UDP socket to receive commands')
        elif server_config['socket_type'] == 'TCP':
            self.server = await asyncio.start_server(self.handle_tcp_client, self.my_ipaddr, self.my_port)
            print( 'Created TCP socket to listen for connections on %s:%d' % (self.my_ipaddr, self.my_port) )
            self.status = 'Waiting For Connection'
        elif server_config['socket_type'] == 'BLUETOOTH':
            print( 'Initializing BLUETOOTH service for %s' % server_config['name'])
            self.ble_stream = BLEUARTStream( server_config['name'] )
            await self.handle_bluetooth_client()
        else:
            print( 'Unknown socket type: %s' % server_config['socket_type'])
    
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

    def handle_tcp_client(self, rx_stream, tx_stream):
        commands = []

        self.status = 'Connected'
        print( 'TCP Connection Established From: %s' % rx_stream.get_extra_info('peername')[0])
        while True:
            try:
                data = await asyncio.wait_for(rx_stream.readline(), 5)
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
                    print( 'TCP Client Connection Error, Closing Socket' )
                    raise OSError
                    
            except asyncio.TimeoutError:
                print( 'Read Timeout' )
                commands = ['ReadTimeout']

            except OSError:
                self.stop_movement()
                await rx_stream.wait_closed()
                self.status = 'Disconnected'
                break
            
            self.process_commands( commands )
    
    async def handle_bluetooth_client(self):
        commands = []
        data = bytearray(32)
        self.ble_connection = 'Disconnected'

        print( 'Starting Bluetooth Client Handler' )

        while True:
            # Check for active bluetooth connections and adjust the status of the
            # connection accordingly
            if len(self.ble_stream._uart._connections) > 0:
                if self.ble_connection == 'Disconnected':
                    print( 'Bluetooth Connection Established' )
                    self.ble_connection = 'Connected'
            else:
                if self.ble_connection == 'Connected':
                    print( 'Bluetooth Connection Closed' )
                    self.ble_connection = 'Disconnected'
                
            # read from the input stream and process any received data. If there is nothing
            # to read from the buffer, the read function will simply return with no data.
            bytes_read = self.ble_stream.readinto(data)
            if bytes_read:
                decoded_data = self.partial_cmd_buffer + data[0:bytes_read].decode('utf-8')
                # split the decoded data into separate commands delimited by a newline
                commands = decoded_data.split('\n')

                # for Bluetooth connections, each read may only contain up to 20 bytes, so the
                # data may contain a partial command, which will be the last item in the commands
                # list. We'll store that last item as the partial command so that we can attach the
                # next received data to the partial command string.
                self.partial_cmd_buffer = commands.pop()

                self.process_commands( commands )

            # yield the CPU by sleeping for a brief moment so that other tasks can run
            await asyncio.sleep_ms(100)

    def process_commands(self, commands ):
        for command in commands:
            #print( 'Command: %s' % command )
            tokens = command.split(':')
            if tokens[0] == 'Event' or tokens[0] == 'EV':
                self.status = 'Processing Command'
                try:
                    event = event_map[tokens[1]]
                except KeyError:
                    event = tokens[1]
                self.process_event( event, tokens[2:] )
            elif command == 'ReadTimeout':
                # If the read times out, then no commands have been received from the
                # driver station in awhile. We have seen the drive station not totally 
                # zero the speed/turn when the controls are released and this clause 
                # will handle that condition and stop any residual motion.
                self.stop_movement()
                self.status = 'Waiting For Command'
            else:
                print('Ignoring Unexpected Command Type: %s, Args: %s' % (tokens[0],str(tokens[1:])) )

    # 
    # Function to periodically send status to a configured FMS
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
            self.current_speed = float(args[0]) * -1.0
        elif event == 'RightJoystickX' or event == 'LeftJoystickX':
            if self.current_speed != 0.0:
                # if we are currently moving forward or backward, let's dampen the
                # turn amount so that it's less abrupt
                dampened_turn = float(args[0]) * 0.3
            else:
                dampened_turn = float(args[0])
            
            # and if we are going backwards, let's flip the direction of the
            # turn so that the robot will move in a natural direction
            if self.current_speed < 0.0:
                self.current_turn = dampened_turn
            else:
                self.current_turn = dampened_turn * -1.0

            # if the current turning setting returns to zero, signal to the drive
            # task to update the heading to the current yaw position
            if self.current_turn == 0.0:
                self.reset_heading = True
                
        elif event == 'LeftBumper':
            # Open (lower) the arm when the left bumper is pressed
            if int(args[0]) == 1:
                self.set_servo_angle( self.min_angle )
        elif event == 'RightBumper':
            # Close (raise) the arm when the right bumper is pressed
            if int(args[0]) == 1:
                self.set_servo_angle( self.max_angle )
        elif event == 'ButtonA':
            if int(args[0]) == 1:
                print( 'Selecting Servo One' )
                self.curr_servo = 0
        elif event == 'ButtonB':
            if int(args[0]) == 1:
                print( 'Selecting Servo Two' )
                self.curr_servo = 1
        elif event == 'ButtonY':
            if int(args[0]) == 1:
                if not self.imu_assist:
                    print( 'Enabling IMU Assist' )
                    self.imu_assist = True
                else:
                    print( 'Disabling IMU Assist' )
                    self.imu_assist = False
        else:
            # add more event handling operations here...
            pass

    async def drive_task(self):
        # initialize the PID controller for imu_assist driving when enabled
        imu_pid = PID(kp = 0.075, kd=0.001,)

        while True:
            if self.imu_assist == False:
                # if the IMU assist is disabled, then just run the standard 
                # arcade drive
                drivetrain.arcade( self.current_speed, self.current_turn )
            else:
                # else if IMU assist is enabled, then use the IMU with PID to
                # maintain a set heading while driving.
                if self.current_speed == 0.0 or self.current_turn != 0.0:
                    drivetrain.arcade( self.current_speed, self.current_turn )
                else:
                    if self.reset_heading:
                        self.reset_heading = False
                        self.desired_heading = imu.get_yaw()

                    heading_correction = imu_pid.update(self.desired_heading - imu.get_yaw())
                    drivetrain.set_effort(self.current_speed - heading_correction, self.current_speed + heading_correction)
            
            await asyncio.sleep_ms(25)

    #
    # Simple function for force the XRP to stop moving. This function is used to handle cases
    # where the XRP robot continues to move following a command invocation.
    #
    def stop_movement(self):
        self.current_speed = 0.0
        self.current_turn = 0.0

    #
    # Function to register this device with a configured FMS
    #
    # The FMS application can be used in a deployment configuration where you don't want to 
    # have to explicitly configure the driver station with the IP addresses of all the XRPs. 
    # With the FMS, the XRPs need only be configured with the FMS address. Each XRP will
    # register with the FMS, providing their IP address, and the driver station application
    # will learn the IP addresses of all connected XRPs from the FMS.
    #
    def register(self, url_base):
        print( 'Registering Device With FMS: %s' % url_base )
        self.registered = False
        reg_data = {}
        reg_data['hardware_id'] = self.id
        reg_data['type'] = 'XRP'
        reg_data['ip_address'] = self.my_ipaddr
        reg_data['port'] = self.my_port
        reg_data['protocol'] = self.config['server']['socket_type']
        reg_data['application'] = self.application
        reg_data['version'] = '1.0 Beta'
        reg_data['status'] = self.status
        reg_data['ble_service'] = 'XRP-' + get_id(short_id=True)

        # Add in the name if configured (optional)
        try:
            reg_data['name'] = self.config['name']
        except:
            pass

        url = '%s/register/' % url_base
        headers = {'Content-type': 'application/json'}
        try:
            resp = requests.post(url, data=json.dumps(reg_data), headers=headers)
            if resp.status_code == 200:
                print( 'Registration With FMS Complete' )
                self.fms_url_base = url_base
                self.registered = True
            else:
                print( 'Error Registering With FMS: %d' % resp.status_code )
        except OSError:
            print( 'Error Connecting To FMS: %s' % url_base )
        return self.registered


    #
    # Function represents the main processing loop for the XRP controller. This function 
    # reads commands from the network interface and invokes the command procesing to 
    # control the robot.
    #
    async def run(self):
        asyncio.create_task(self.drive_task())
        asyncio.create_task(self.server_task())
        asyncio.create_task(self.status_task())
        
        while True:
            await asyncio.sleep(10)
            print( 'Main Run Loop')
            
    # 
    # Function to periodically send status to a configured FMS
    #
    # This function is called periodically from the main processing thread to send
    # a simple status message to the FMS.
    #
    # This message will be expanded over time to convey more information to the FMS 
    #
    async def status_task(self):
        print( 'Starting Status Reporting Loop')

        while True:
            # Send the status every so often to the FMS if configured
            if self.fms_configured and self.registerd:
                print( 'Sending Status...')
                data = {}
                data['hardware_id'] = self.id
                data['status'] = self.status

                url = '%s/status/' % self.fms_url_base
                headers = {'Content-type': 'application/json'}
                try:
                    resp = requests.post(url, data=json.dumps(data), headers=headers)
                    if resp.status_code == 200:
                        print( 'Status Sent' )
                    else:
                        print( 'Error Sending Status To FMS: %d' % resp.status_code )
                    self.status_reported = curr_time

                except OSError:
                    print( 'Error Connecting To FMS')
            else:
                print('Nothing To Report')
                
            await asyncio.sleep(15)


if __name__ == '__main__':

    # read the config.json file located in the base directory
    config = read_config()

    # create the instance of the XRP controller and launch the run loop
    controller = XrpControl( config )
    if controller:
        print( 'Starting Controller Main Loop...')
        asyncio.run(controller.run())
