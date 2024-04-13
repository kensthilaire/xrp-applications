#!/usr/bin/env python3

import argparse
import json
import logging
import requests
import signal
import socket
import subprocess
import sys
import threading
import time

from config import read_config

from logger import logger
from safe_scheduler import SafeScheduler

import joystick
from xrp_controller import XrpController, controller_service

#
# Service routine that will be run as a separate thread for each XRP control instance to an
# XRP device. This service routin will call the base controller service and it will only
# return if there is some form of error, like when a controller is disconnected
#
def ds_controller_service( device, controller ):

    # invoke the XRP controller service routine which will not return unless there is an error
    controller_service( controller )

    # if the controller service function ever returns, it's because of a gamepad/joystick 
    # communication failure. Just clear the controller setting within the device and 
    # the device will reconnect once the problem clears
    device['controller'] = None

class DriverStation():
    def __init__(self, config):
        self.config = config

        # set up the scheduler service with the default items. Do this early
        # in the initialization sequence so that additional items can be added
        # based on configuration
        self.setup_schedule()

        # initialize the list of XRP devices and controllers that are attached to this instance
        self.devices = list()
        self.controllers = list()

        # if an FMS is configured, then register with the first available FMS in the 
        # configuration list
        self.fms = None
        fms_config = self.config.get('fms', None)
        if fms_config:
            # loop to continue to attempt to register with the FMS, we can't do much without being able to access the FMS
            while not self.fms:
                # loop through the list of configured FMS instances and connect to
                # the first available instance
                for fms in fms_config:
                    if fms.get('enabled', False) == True:
                        if self.register( fms ) != None:
                            self.fms = fms
                            self.scheduler.every(30).seconds.do(self.send_status)
                            break
                if not self.fms:
                    logger.error( 'No FMS available, will try again in 30 seconds' )
                    time.sleep(30)

        self.status_reported = 0
        self.status = 'Running'

    #
    # Instantiate the periodic job scheduler and install the default handlers
    #
    def setup_schedule(self):
        self.scheduler = SafeScheduler()
        self.scheduler.every(5).seconds.do(self.scan_controllers)
        self.scheduler.every(10).seconds.do(self.connect_devices)

    #
    # Function to register this driver station control instance with the FMS. Once registered,
    # any additional configuration information maintained by the FMS will be retrieved.
    #
    def register(self, fms):
        if self.fms:
            logger.info( 'Driver Station Already Registered With FMS...')
        else:
            logger.info( 'Registering Device With FMS...')
            data = {}
            data['hardware_id'] = self.config.get('uuid', 'No UUID')
            data['type'] = 'Driver Station'
            data['name'] = self.config.get('name','No Name')
            data['ip_address'] = subprocess.check_output( ['hostname','-I'] ).decode('utf8').strip()
            data['port'] = 'n/a'
            data['protocol'] = 'n/a'
            data['application'] = 'Driver Station App'
            data['version'] = '0.1'

            url = '%s/register/' % fms['url_base']
            headers = {'Content-type': 'application/json'}
            try:
                resp = requests.post(url, json=data, headers=headers, verify=False)
                if resp.status_code == 200:
                    logger.info( 'Registration With FMS Complete' )
                    self.fms = fms
                    self.fms_config = self.get_my_config(fms)
                else:
                    logger.error( 'Error Registering With FMS: %d' % resp.status_code )
            except OSError:
                logger.error( 'Error Registering With FMS at %s, Check if FMS is running or correct IP address' % fms['url_base'] )

        return self.fms
 
    #
    # Function will be called periodically to send current status to the connected FMS
    #
    def send_status(self):
        if self.fms:
            logger.debug( 'Sending Status To FMS...')
            data = {}
            data['hardware_id'] = self.config.get('uuid', 'No UUID')
            data['status'] = self.status

            url = '%s/status/' % self.fms['url_base']
            headers = {'Content-type': 'application/json'}
            try:
                resp = requests.post(url, json=data, headers=headers, verify=False)
                if resp.status_code == 200:
                    logger.debug( 'Status Successfully Sent' )
                else:
                    logger.error( 'Error Sending Status To FMS: %d' % resp.status_code )

            except OSError:
                logger.error( 'Error Connecting To FMS')

    #
    # The FMS may have some additional configuration data for this driver station instance. This
    # function will retrieve that configuration and store it in this instance.
    #
    def get_my_config(self, fms):
        my_config = None
        if not self.fms:
            logger.error( 'Error retrieving driver station configuration, no FMS connected' )
            return my_config()

        logger.info( 'Retrieving my configuration stored on the FMS...')
        url = '%s/api/devices/?id=%s' % (fms['url_base'], self.config['uuid'])
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json()
                #print( json.dumps(data, indent=4) )
                if len(data) == 0:
                    logger.error( 'Error - No configuration for driver station on FMS' )
                elif len(data) > 1:
                    logger.error( 'Error - Multiple configurations for driver station returned from FMS' )
                else:
                    my_config = data[0]
            else:
                logger.error( 'Error Retrieving My Configuration From FMS: %d' % resp.status_code )
        except OSError:
            logger.error( 'Error Connecting To FMS')

        return my_config
        
    #
    # Function will retrieve the list of registered devices for this driver station instance from the FMS.
    # If an alliance has been configured for this instance, then request just those instances that are
    # associated with this instance. If not, then ask for all devices.
    # 
    def get_devices(self):
        if not self.fms:
            logger.error( 'Error retrieving devices, no FMS connected' )
            return list()

        logger.info( 'Retrieving list of registered XRP devices...')
        url = '%s/api/devices/?type=XRP' % (self.fms['url_base'])

        alliance = self.fms_config.get( 'alliance', None )
        if alliance:
            url += '&alliance=%s' % (alliance)

        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                devices = resp.json()
                for device in devices:
                    logger.info( 'Device: %s' % str(device) )
            else:
                logger.error( 'Error Retrieving Devices From FMS: %d' % resp.status_code )
        except OSError:
            logger.error( 'Error Connecting To FMS')

        return devices
        
    #
    # Function is called periodically to scan for any newly connected or disconnected gamepad controllers
    # For newly discovered controllers, a new XRP control thread will be created to service any unconnected
    # devices. And, for any disconnected controllers, the control thread will be terminated automatically by
    # the underlying driver, and we'll remove that controller from this driver station instance
    #
    def scan_controllers(self):
        new_controllers = joystick.get_joysticks()
        if len(new_controllers) == len(self.controllers):
            # no change detected
            pass
        elif len(new_controllers) < len(self.controllers):
            logger.info( 'Controller removal detected' )
            # we now have less controllers plugged in
            pass
        else:
            logger.info( 'New controller discovered' )
            # we have a new controller, so let's find the new one and connect it up to any unconnected device
            for new_controller in new_controllers:
                logger.info( 'Controller: %s' % str( new_controller ) )
                found = False
                for curr_controller in self.controllers:
                    if new_controller.path == curr_controller.path:
                        logger.info( 'Controller: %s' % str( new_controller ) )
                        found = True
                        break
                if not found:
                    self.connect_device(new_controller)
                        
        self.controllers = new_controllers

    #
    # Function will create an XRP control session with the specified controller instance. This function will
    # look for an XRP device that is not yet connected to a gamepad controller and initiate the connection
    #
    def connect_device(self, controller): 
        logger.debug( 'Controller: %s' % controller )
        for device in self.devices:
            if not device.get('controller', None):
                logger.info( 'Connecting %s at address: %s:%s to controller: %s' % \
                              (device['name'],device['ip_address'],device['port'],controller) )
                controller_instance = XrpController(path=controller.path, socket_type=device['protocol'], host=device['ip_address'], port=int(device['port']))
                device['controller'] = controller_instance
                control_thread = threading.Thread( target=ds_controller_service, args=(device,controller_instance,), daemon=True )
                device['thread'] = control_thread
                control_thread.start()
                break

    #
    # Function will loop through the set of discovered controllers and initiate a connection to all devices
    # associated with this driver station instance
    #
    def connect_devices(self): 
        for controller in self.controllers:
            self.connect_device( controller )
                
#
# Signal handler for the signals to gracefully terminate the service
#
def shutdown_handler(signum, frame):
    shutdown_all()
    sys.exit(0)

def shutdown_all():
    logger.info( 'Terminating controller service threads' )
    for device in ds.devices:
        controller = device.get('controller', None)
        if controller:
            controller.terminate_read_loop = True
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
    parser.add_argument('-c', '--config', action='store', dest='config', default='ds_config.json')
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

    ds = DriverStation(config)

    # retrieve the list of XRP devices associated with this driver station instance
    ds.devices = ds.get_devices()

    # perform an initial scan for gamepad controllers and associate the controllers with XRP devices
    ds.scan_controllers()

    delay = 0.5
    while True:
        try:
            ds.scheduler.run_pending()
            time.sleep( delay )
        except KeyboardInterrupt:
            logger.info( 'Initiating shutdown from keyboard' )
            shutdown_all()
                
    logger.info( 'Driver Station Application Terminated.' )
