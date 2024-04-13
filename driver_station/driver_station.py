#!/usr/bin/env python3

import argparse
import json
import logging
import requests
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

class DriverStation():
    def __init__(self, config):
        self.config = config

        self.fms_registered = False

        fms_config = self.config.get('fms', None)
        if fms_config:
            for fms in fms_config:
                if fms.get('enabled', False) == True:
                    if self.register( fms['url_base'] ) == True:
                        break

        self.controllers = list()
        self.controller_threads = list()

        self.scheduler = SafeScheduler()
        self.setup_schedule()

        self.status_reported = 0
        self.status = 'Running'

    def setup_schedule(self):
        self.scheduler.every(30).seconds.do(self.send_status)
        self.scheduler.every(5).seconds.do(self.scan_controllers)
        self.scheduler.every(10).seconds.do(self.connect_devices)

    def register(self, url_base):
        if self.fms_registered:
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

            url = '%s/register/' % url_base
            headers = {'Content-type': 'application/json'}
            try:
                resp = requests.post(url, json=data, headers=headers, verify=False)
                if resp.status_code == 200:
                    logger.info( 'Registration With FMS Complete' )
                    self.fms_url_base = url_base
                    self.fms_config = self.get_my_config()
                    self.fms_registered = True
                else:
                    logger.error( 'Error Registering With FMS: %d' % resp.status_code )
            except OSError:
                logger.error( 'Error Registering With FMS at %s, Check if FMS is running or correct IP address' % url_base )

        return self.fms_registered
 
    def send_status(self):
        curr_time = int(time.time())
        logger.debug( 'Sending Status...')
        data = {}
        data['hardware_id'] = self.config.get('uuid', 'No UUID')
        data['status'] = self.status
        data['last_reported'] = self.status_reported

        url = '%s/status/' % self.fms_url_base
        headers = {'Content-type': 'application/json'}
        try:
            resp = requests.post(url, json=data, headers=headers, verify=False)
            if resp.status_code == 200:
                logger.debug( 'Status Sent' )
            else:
                logger.error( 'Error Sending Status To FMS: %d' % resp.status_code )
            self.status_reported = curr_time

        except OSError:
            logger.error( 'Error Connecting To FMS')

    def get_my_config(self):
        my_config = None
        logger.info( 'Retrieving my configuration stored on the FMS...')
        url = '%s/api/devices/?id=%s' % (self.fms_url_base, self.config['uuid'])
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json()
                print( json.dumps(data, indent=4) )
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
        
    def get_devices(self):
        logger.info( 'Retrieving list of registered XRP devices...')
        url = '%s/api/devices/?type=XRP&alliance=%s' % (self.fms_url_base, self.fms_config['alliance'])
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
            logger.info( 'New controller plugged in' )
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

    def connect_device(self, controller): 
        logger.debug( 'Controller: %s' % controller )
        for device in self.devices:
            if not device.get('controller', None):
                logger.info( 'Connecting %s at address: %s:%s to controller: %s' % \
                              (device['name'],device['ip_address'],device['port'],controller) )
                app = XrpController(path=controller.path, socket_type=device['protocol'], host=device['ip_address'], port=int(device['port']))
                device['controller'] = controller.path
                app_thread = threading.Thread( target=ds_controller_service, args=(device,app,), daemon=True )
                self.controller_threads.append( app_thread )
                app_thread.start()
                break

    def connect_devices(self): 
        for controller in self.controllers:
            logger.debug( 'Controller: %s' % controller )
            for device in self.devices:
                if not device.get('controller', None):
                    logger.info( 'Connecting %s at address: %s:%s to controller: %s' % \
                                  (device['name'],device['ip_address'],device['port'],controller) )
                    app = XrpController(path=controller.path, socket_type=device['protocol'], host=device['ip_address'], port=int(device['port']))
                    device['controller'] = controller.path
                    app_thread = threading.Thread( target=ds_controller_service, args=(device,app,), daemon=True )
                    self.controller_threads.append( app_thread )
                    app_thread.start()
                    break
                
def ds_controller_service( device, controller ):

    # invoke the XRP controller service routine which will not return unless there is an error
    controller_service( controller )

    # if the controller service function ever returns, it's because of a gamepad/joystick 
    # communication failure. Just clear the controller setting within the device and 
    # the device will reconnect once the problem clears
    device['controller'] = None        

if __name__ == '__main__':

    #
    # parse out the command arguments
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', default=False)
    parser.add_argument('-c', '--config', action='store', dest='config', default='ds_config.json')
    parser.add_argument('-ds', '--driver_station', action='store_true', dest='driver_station', default=True)
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

    if options.driver_station:
        ds = DriverStation(config)

        while not ds.fms_registered:
            time.sleep(10)
            ds.register()

        ds.devices = ds.get_devices()

        ds.scan_controllers()

        controller_threads = ds.connect_devices()
        
        delay = 0.5
        done = False
        while done == False:
            try:
                while True:
                    ds.scheduler.run_pending()
                    time.sleep( delay )
            except KeyboardInterrupt:
                logger.info( 'Waiting For Threads to exit' )
                done=True
            
