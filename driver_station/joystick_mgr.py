import pygame

import argparse
import logging
import platform
import sys
import threading
import time

from logger import logger

controller_maps = {
    "XInput" : {
        "BUTTONS" : {
            0: { 'name': 'ButtonA' },
            1: { 'name': 'ButtonB' },
            2: { 'name': 'ButtonX' },
            3: { 'name': 'ButtonY' },
            4: { 'name': 'LeftBumper' },
            5: { 'name': 'RightBumper' },
            6: { 'name': 'Select' },
            7: { 'name': 'Start' },
            8: { 'name': 'Logo' },
            9: { 'name': 'Unknown' },
           10: { 'name': 'Unknown' }
        },

        "AXES" : {
            0:  { 'name': 'LeftJoystickX', 'min': -1.0, 'max': 1.0 },
            1:  { 'name': 'LeftJoystickY', 'min': -1.0, 'max': 1.0 },
            2:  { 'name': 'LeftTrigger', 'min': -1.0, 'max': 1.0, 'scale': True },
            3:  { 'name': 'RightJoystickX', 'min': -1.0, 'max': 1.0 },
            4:  { 'name': 'RightJoystickY', 'min': -1.0, 'max': 1.0 },
            5:  { 'name': 'RightTrigger', 'min': -1.0, 'max': 1.0, 'scale': True }
        },

        "HATS" : {
            0: { 'name': 'HatX', 'min': -1, 'max': 1 },
            1: { 'name': 'HatY', 'min': -1, 'max': 1 }
        }
    },

    "XInputWindows" : {    
        "BUTTONS" : {
            0: { 'name': 'ButtonA' },
            1: { 'name': 'ButtonB' },
            2: { 'name': 'ButtonX' }, 
            3: { 'name': 'ButtonY' },
            4: { 'name': 'LeftBumper' },
            5: { 'name': 'RightBumper' },
            6: { 'name': 'Select' },
            7: { 'name': 'Start' },
            8: { 'name': 'Unknown' },
            9: { 'name': 'Unknown' },
           10: { 'name': 'Logo' }
        },      
                    
        "AXES" : {  
            0:  { 'name': 'LeftJoystickX', 'min': -1.0, 'max': 1.0 },
            1:  { 'name': 'LeftJoystickY', 'min': -1.0, 'max': 1.0 },
            2:  { 'name': 'RightJoystickX', 'min': -1.0, 'max': 1.0 },
            3:  { 'name': 'RightJoystickY', 'min': -1.0, 'max': 1.0 },
            4:  { 'name': 'LeftTrigger', 'min': -1.0, 'max': 1.0, 'scale': True },
            5:  { 'name': 'RightTrigger', 'min': -1.0, 'max': 1.0, 'scale': True }
        },  
    
        "HATS" : {
            0: { 'name': 'HatX', 'min': -1, 'max': 1 },
            1: { 'name': 'HatY', 'min': -1, 'max': 1 }
        }       
    },          

    "DirectInput" : {
        "BUTTONS" : {
            0: { 'name': 'ButtonX' },
            1: { 'name': 'ButtonA' },
            2: { 'name': 'ButtonB' },
            3: { 'name': 'ButtonY' },
            4: { 'name': 'LeftBumper' },
            5: { 'name': 'RightBumper' },
            6: { 'name': 'LeftTrigger' },
            7: { 'name': 'RightTrigger' },
            8: { 'name': 'Select' },
            9: { 'name': 'Start' },
           10: { 'name': 'Unknown' },
           11: { 'name': 'Unknown' }
        },

        "AXES" : {
            0:  { 'name': 'LeftJoystickX', 'min': -1.0, 'max': 1.0 },
            1:  { 'name': 'LeftJoystickY', 'min': -1.0, 'max': 1.0 },
            2:  { 'name': 'RightJoystickX', 'min': -1.0, 'max': 1.0 },
            3:  { 'name': 'RightJoystickY', 'min': -1.0, 'max': 1.0 }
        },

        "HATS" : {
            0: { 'name': 'HatX', 'min': -1, 'max': 1 },
            1: { 'name': 'HatY', 'min': -1, 'max': 1 }
        }
    }
}

class JoystickMgr:

    BUTTON_STATES = {
        0: 'RELEASED',
        1: 'PRESSED'
    }

    def __init__(self, scan_for_joysticks=True):
        self.joysticks = {}
        self.devices = {}
        self.controller_maps = {}
        self.curr_hat_x = {}
        self.curr_hat_y = {}

        pygame.init()

        if scan_for_joysticks:
            # do an initial scan to process events which will detect any 
            # currently connected joystick devices
            done = False
            while not done:
                done = self.process_events()
                if done:
                    sys.exit(0)

                if len(self.joysticks) > 0:
                    done = True
                else:
                    logger.error( 'No Gamepad Controllers Detected, retrying' )
                    time.sleep(2)

    #
    # set of functions to manage the binding between a joystick instance and
    # an associated device
    #
    def bind_device(self, joystick_key, device):
        device.set_gamepad_id(joystick_key)
        self.devices[joystick_key] = device

    def get_bound_device(self, joystick_key):
        device = self.devices.get( joystick_key, None )
        return device

    def remove_device_binding(self, joystick_key):
        try:
            device = self.get_bound_device(joystick_key)
            if device:
                device.clear_gamepad_id()
            self.devices[joystick_key] = None
        except:
            pass

    def get_num_joysticks(self):
        pygame.joystick.get_count()

    def get_joysticks(self):
        return self.joysticks

    # function decodes the joystick events to a form that can then be passed
    # to a controller instance
    def decode_event(self, event):
        decoded_event = { 'type': 'UNKNOWN', 'name': '', 'value': None }

        print( 'Event: %s' % str(event) )

        if event.type == pygame.JOYBUTTONDOWN:
            decoded_event['type'] = 'BUTTON'
            button = self.controller_maps[event.instance_id]['BUTTONS'].get(event.button,None)
            if button:
                decoded_event['name'] = button['name']
                decoded_event['value'] = 1
        elif event.type == pygame.JOYBUTTONUP:
            decoded_event['type'] = 'BUTTON'
            button = self.controller_maps[event.instance_id]['BUTTONS'].get(event.button,None)
            if button:
                decoded_event['name'] = button['name']
                decoded_event['value'] = 0
        elif event.type == pygame.JOYAXISMOTION:
            decoded_event['type'] = 'AXIS'
            axis = self.controller_maps[event.instance_id]['AXES'].get(event.axis,None)
            value = 0.0
            if axis:
                decoded_event['name'] = axis['name']
                scaled = axis.get('scale', False)
                if scaled == True:
                    range = axis['max'] - axis['min']
                    value = abs((event.value + (range/2))/range)
                else:
                    value = event.value / axis['max']
                decoded_event['value'] = value
                decoded_event['rounded_value'] = round(value, 1)
        elif event.type == pygame.JOYHATMOTION:
            decoded_event['type'] = 'HAT'
            # look for a change in the hat values for X and Y coordinates and map any
            # change to discrete events corresponding to the changed setting
            if self.curr_hat_x[event.instance_id] != event.value[0]:
                hat = self.controller_maps[event.instance_id]['HATS'].get(0,None)
                if hat:
                    decoded_event['name'] = hat['name']
                    decoded_event['value'] = event.value[0]
                    self.curr_hat_x[event.instance_id] = event.value[0]
            elif self.curr_hat_y[event.instance_id] != event.value[1]:
                hat = self.controller_maps[event.instance_id]['HATS'].get(1,None)
                if hat:
                    decoded_event['name'] = hat['name']
                    decoded_event['value'] = event.value[1]
                    self.curr_hat_y[event.instance_id] = event.value[1]
        elif event.type == pygame.JOYDEVICEADDED:
            decoded_event['type'] = 'MGMT'
            decoded_event['name'] = 'JOYSTICK'
            decoded_event['value'] = 'CONNECTED'
        elif event.type == pygame.JOYDEVICEREMOVED:
            decoded_event['type'] = 'MGMT'
            decoded_event['name'] = 'JOYSTICK'
            decoded_event['value'] = 'DISCONNECTED'
        elif event.type == pygame.KEYDOWN:
            # Check for a ctrl-C being pressed and raise the KeyboardInterrupt 
            # exception to terminate the program
            if event.unicode == '\x03':
                decoded_event['type'] = 'QUIT'

        #logger.debug( 'Decoded Event: %s' % str(decoded_event) )
        return decoded_event

    def process_events(self):
        done = False
        for event in pygame.event.get():
            decoded_event = self.decode_event( event )
            if decoded_event['type'] in ['BUTTON', 'AXIS', 'HAT']:
                device = self.devices.get(event.instance_id, None)
                if device:
                    device.process_event( decoded_event )
                else:
                    logger.debug( 'No Device Bound To Process Event: %s %s %s' % (decoded_event['name'], decoded_event['type'], decoded_event['value']) )
            elif decoded_event['type'] == 'MGMT':
                logger.debug( 'Management Event: %s %s' % (decoded_event['name'], decoded_event['value']) )
                if decoded_event['value'] == 'CONNECTED':
                    joystick = pygame.joystick.Joystick(event.device_index)
                    self.joysticks[joystick.get_instance_id()] = joystick
                    self.curr_hat_x[joystick.get_instance_id()] = 0
                    self.curr_hat_y[joystick.get_instance_id()] = 0
                    if joystick.get_numaxes() == 6:
                        os_type = platform.system()
                        if os_type == 'Windows':
                            logger.info( 'Windows XInput Joystick: %s Connected' % joystick.get_instance_id() )
                            self.controller_maps[joystick.get_instance_id()] = controller_maps['XInputWindows']
                        else:
                            logger.info( 'XInput Joystick: %s Connected' % joystick.get_instance_id() )
                            self.controller_maps[joystick.get_instance_id()] = controller_maps['XInput']
                    else:
                        logger.info( 'DirectInput Joystick: %s Connected' % joystick.get_instance_id() )
                        self.controller_maps[joystick.get_instance_id()] = controller_maps['DirectInput']
                elif decoded_event['value'] == 'DISCONNECTED':
                    logger.info( 'Joystick %d disconnected' % event.instance_id )
                    self.remove_device_binding(event.instance_id)
                    del self.joysticks[event.instance_id]

            elif decoded_event['type'] == 'QUIT':
                logger.debug( 'Quit received, returning done' )
                done = True

        return done

    def run(self):
        done = False
        while not done:
            try:
                done = self.process_events()
                time.sleep(0.1)
            except KeyboardInterrupt:
                done = True

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    #
    # parse out the command arguments
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list', action='store_true', dest='list_devices', default=False)
    options = parser.parse_args()

    joystick_mgr = JoystickMgr().run()

