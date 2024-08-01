#!/usr/bin/env python3

import argparse
import logging
import time
import signal
import sys

from enum import Enum, auto

from config import read_config
from logger import logger
from lidar import Lidar

from xrp_controller import XrpController

LED_RED = 0xFF0000
LED_GREEN = 0x00FF00
LED_BLUE = 0x0000FF
LED_YELLOW = 0xFFFF00

class LidarStates(Enum):
    INITIAL = auto()
    ACQUIRING = auto()
    ACQUIRED = auto()
    FOLLOWING = auto()
    STOPPED = auto()
    TERMINATING = auto()
    TERMINATED = auto()

class XrpLidarController(XrpController):
    def __init__(self, socket_type='UDP', host='', port=9999):
        super().__init__(socket_type, host, port)

        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        self.lidar = None
        self.lidar_state = LidarStates.INITIAL
        
        self.curr_turning_speed = 0.0
        self.turning_noupdates = 0
        self.curr_moving_speed = 0.0
        self.moving_noupdates = 0

    def shutdown( self, *args ):
        if self.lidar:
            logger.info( 'Terminating LIDAR Session' )
            self.set_lidar_state( LidarStates.TERMINATING)
            self.lidar.cancel()

            logger.info( 'Shutting down LIDAR' )
            controller.lidar.terminate()

        time.sleep(2)
        self.set_lidar_state( LidarStates.TERMINATED )
        logger.info( 'Shutdown complete.' )

        sys.exit(0)

    def set_lidar_state(self,new_state):
        curr_state = self.lidar_state

        if curr_state != new_state:
            logger.debug( 'State Transition From %s to %s' % (curr_state.name, new_state.name) )

            if new_state == LidarStates.ACQUIRING:
                self.set_led(LED_RED)
            elif new_state == LidarStates.ACQUIRED:
                if self.follow_distance != 0:
                    self.lidar.cancel()
                self.set_led(LED_GREEN)
            elif new_state == LidarStates.STOPPED:
                self.set_led(LED_GREEN)
            elif new_state == LidarStates.FOLLOWING:
                self.set_led(LED_BLUE)
            elif new_state == LidarStates.TERMINATING:
                self.set_led(LED_YELLOW)
            elif new_state == LidarStates.TERMINATED:
                self.set_led_off()

        self.lidar_state = new_state

    def set_led_off(self):
        led_event = { 'name': 'LED', 'value': 'OFF' }
        self.process_event( led_event )

    def set_led(self, led_pattern):
        led_event = { 'name': 'LED', 'value': 'RGB:0x%x' % led_pattern }
        self.process_event( led_event )

    def lidar_align(self, scan_data, precision_factor=1.0):
        #
        # in order to align the robot to the closest object, we will use the 'RightJoystickX' controller
        # to turn the robot left or right until the closest object is centered in the capture zone
        #
        turning_speed = 0.0
        if scan_data.get('valid', False)==True:
            self.turning_noupdates = 0

            angle = scan_data['angle']
            if angle < 5 or angle > 355:
                turning_speed = 0.0

                # if the lidar is acquiring the target, then
                # transition to the acquired state and wait 
                # for further command
                if self.lidar_state == LidarStates.ACQUIRING:
                    self.set_lidar_state( LidarStates.ACQUIRED )
                        
            elif angle < 20 or angle > 340:
                turning_speed = 0.2
            elif angle < 90 or angle > 270:
                turning_speed = 0.4
            else:
                turning_speed = 0.6
                
            # if the angle is greater than 180, then we will turn to the left
            if angle > 180:
                turning_speed *= -1.0

            if self.lidar_state == LidarStates.FOLLOWING:
                turning_speed *= precision_factor

            if turning_speed != self.curr_turning_speed:
                self.curr_turning_speed = turning_speed
                turning_event = { 'name': 'RightJoystickX', 'rounded_value': self.curr_turning_speed }
                self.process_event( turning_event )
                logger.debug( 'Setting turning speed to %0.1f' % turning_speed )
        else:
            self.turning_noupdates += 1

        if self.turning_noupdates == 5:
            if self.curr_turning_speed != 0.0:
                self.curr_turning_speed = 0.0
                turning_event = { 'name': 'RightJoystickX', 'rounded_value': self.curr_turning_speed }
                self.process_event( turning_event )
                logger.debug( 'No turning updates received recently, halting robot' )


    #
    # This function will instruct the robot to follow the closest object in the capture zone, maintaining 
    # alignment on that closest object and a minimum distance from the object.
    #
    def lidar_follow(self, scan_data):

        self.lidar.print_scan_data( scan_data )

        self.lidar_align( scan_data, precision_factor=0.3 )

        moving_speed = 0.0
        if scan_data.get('valid', False)==True:
            self.moving_noupdates = 0
            distance = scan_data['distance']
            angle = scan_data['angle']
            if distance <= self.follow_distance: 
                moving_speed = 0.0
                self.set_lidar_state( LidarStates.STOPPED )
            elif distance < self.follow_distance + 6:
                self.set_lidar_state( LidarStates.FOLLOWING )
            elif distance < self.follow_distance + 12:
                moving_speed = 0.5
            elif distance < self.follow_distance + 36:
                moving_speed = 0.7
            elif distance < self.follow_distance + 48:
                moving_speed = 0.9
            else:
                moving_speed = 1.0
            
            moving_speed *= -1.0

            if moving_speed != self.curr_moving_speed:
                self.curr_moving_speed = moving_speed
                moving_event = { 'name': 'LeftJoystickX', 'rounded_value': self.curr_moving_speed }
                self.process_event( moving_event )
                logger.debug( 'Setting moving speed to %0.1f' % moving_speed )
                logger.debug( 'Distance To Target: %d, Angle: %d' % (int(distance),int(angle)) )
        else:
            self.moving_noupdates += 1

        if self.moving_noupdates >= 5:
            if self.curr_moving_speed != 0.0:
                self.curr_moving_speed = 0.0
                moving_event = { 'name': 'LeftJoystickX', 'rounded_value': self.curr_moving_speed }
                self.process_event( moving_event )
                logger.debug( 'No moving updates received recently, halting robot' )

    #
    # Send commands to halt any movememnt of the robot
    #
    def lidar_halt(self):
        moving_event = { 'name': 'LeftJoystickY', 'rounded_value': 0.0 }
        self.process_event( moving_event )
        turning_event = { 'name': 'RightJoystickX', 'rounded_value': 0.0 }
        self.process_event( turning_event )


    def lidar_control(self, port='/dev/ttyUSB0', capture_distance=48, capture_zone='0-45,315-359', follow_distance=0):
        if self.lidar == None:
            self.lidar = Lidar(port)

        self.capture_distance = capture_distance
        self.follow_distance = follow_distance
        self.lidar.build_ranges(capture_zone)

        self.set_lidar_state( LidarStates.ACQUIRING )
        self.lidar.closest_in_range(ranges=None, min_distance=capture_distance, sample_interval=0.05, callback=self.lidar_align)

        if self.follow_distance != 0:
            self.set_lidar_state( LidarStates.STOPPED )
            self.lidar.closest_in_range(ranges=None, min_distance=self.lidar.MAX_DISTANCE, sample_interval=0.05, callback=self.lidar_follow)

        self.lidar_halt()
        self.set_lidar_state( LidarStates.TERMINATING )

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

    try:
        xrp_config = xrp_devices[0]
        xrp_ipaddr = xrp_config.get('ipaddr', 'localhost')
        xrp_port = xrp_config.get('port', 9999)

        controller = XrpLidarController(socket_type=socket_type, host=xrp_ipaddr, port=xrp_port)
        lidar_config = config.get('lidar',None)
        if lidar_config:
            controller.lidar_control( port=lidar_config.get('port', '/dev/ttyUSB0'),
                                      capture_zone=lidar_config.get('capture_zone', '0-60,300-359'),
                                      capture_distance=lidar_config.get('capture_distance', 30),
                                      follow_distance=lidar_config.get('follow_distance', 48) )
    except KeyboardInterrupt:
        logger.info( 'Shutting down controller' )
        controller.shutdown();

