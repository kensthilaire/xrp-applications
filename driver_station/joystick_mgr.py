import pygame

import argparse
import logging
import sys
import threading
import time

from logger import logger

class JoystickMgr:

    BUTTONS = {
        0: { 'name': 'ButtonX' },
        1: { 'name': 'ButtonA' },
        2: { 'name': 'ButtonB' },
        3: { 'name': 'ButtonY' },
        4: { 'name': 'LeftBumper' },
        5: { 'name': 'RightBumper' },
        6: { 'name': 'LeftTrigger' },
        7: { 'name': 'RightTrigger' },
        8: { 'name': 'Select' },
        9: { 'name': 'Start' }
    }

    BUTTON_STATES = {
        0: 'RELEASED',
        1: 'PRESSED'
    }

    AXIS_TYPES = {
        0:  { 'name': 'LeftJoystickX', 'min': -1.0, 'max': 1.0 },
        1:  { 'name': 'LeftJoystickY', 'min': -1.0, 'max': 1.0 },
        2:  { 'name': 'RightJoystickX', 'min': -1.0, 'max': 1.0 },
        3:  { 'name': 'RightJoystickY', 'min': -1.0, 'max': 1.0 }
    }

    HATS = {
        0: { 'name': 'HatX', 'min': -1, 'max': 1 },
        1: { 'name': 'HatY', 'min': -1, 'max': 1 }
    }

    def __init__(self, path=None):
        self.joysticks = {}
        self.devices = {}
        self.curr_hat_x = {}
        self.curr_hat_y = {}

        pygame.init()

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

    # simple function to associated a controller device to a joystick instance
    def bind_device(self, key, device):
        self.devices[key] = device

    def get_num_joysticks(self):
        pygame.joystick.get_count()

    def get_joysticks(self):
        return self.joysticks

    # function decodes the joystick events to a form that can then be passed
    # to a controller instance
    def decode_event(self, event):
        decoded_event = { 'type': 'UNKNOWN', 'name': '', 'value': None }

        if event.type == pygame.JOYBUTTONDOWN:
            decoded_event['type'] = 'BUTTON'
            button = self.BUTTONS.get(event.button, None)
            if button:
                decoded_event['name'] = button['name']
                decoded_event['value'] = 1
        elif event.type == pygame.JOYBUTTONUP:
            decoded_event['type'] = 'BUTTON'
            button = self.BUTTONS.get(event.button, None)
            if button:
                decoded_event['name'] = button['name']
                decoded_event['value'] = 0
        elif event.type == pygame.JOYAXISMOTION:
            decoded_event['type'] = 'AXIS'
            axis = self.AXIS_TYPES.get(event.axis, None)
            if axis:
                decoded_event['name'] = axis['name']
                decoded_event['value'] = event.value / axis['max']
                decoded_event['rounded_value'] = round((event.value / axis['max']), 2)
        elif event.type == pygame.JOYHATMOTION:
            decoded_event['type'] = 'HAT'
            # look for a change in the hat values for X and Y coordinates and map any
            # change to discrete events corresponding to the changed setting
            if self.curr_hat_x[event.instance_id] != event.value[0]:
                hat = self.HATS.get(0, None)
                if hat:
                    decoded_event['name'] = hat['name']
                    decoded_event['value'] = event.value[0]
                    self.curr_hat_x[event.instance_id] = event.value[0]
            elif self.curr_hat_y[event.instance_id] != event.value[1]:
                hat = self.HATS.get(1, None)
                if hat:
                    decoded_event['name'] = hat['name']
                    decoded_event['value'] = event.value[1]
                    self.curr_hat_y[event.instance_id] = event.value[1]
        elif event.type == pygame.JOYDEVICEADDED:
            decoded_event['type'] = 'MGMT'
            decoded_event['name'] = 'JOYSTICK'
            decoded_event['value'] = 'CONNECTED'
            joystick = pygame.joystick.Joystick(event.device_index)
            logger.info( 'Joystick: %s Connected' % joystick )
            self.joysticks[joystick.get_instance_id()] = joystick
            self.curr_hat_x[joystick.get_instance_id()] = 0
            self.curr_hat_y[joystick.get_instance_id()] = 0
        elif event.type == pygame.JOYDEVICEREMOVED:
            decoded_event['type'] = 'MGMT'
            decoded_event['name'] = 'JOYSTICK'
            decoded_event['value'] = 'DISCONNECTED'
            del self.joysticks[event.instance_id]
            logger.info( 'Joystick %d disconnected' % event.instance_id )
        elif event.type == pygame.KEYDOWN:
            # Check for a ctrl-C being pressed and raise the KeyboardInterrupt 
            # exception to terminate the program
            if event.unicode == '\x03':
                decoded_event['type'] = 'QUIT'

        logger.debug( 'Decoded Event: %s' % str(decoded_event) )
        return decoded_event

    def process_events(self):
        done = False
        for event in pygame.event.get():
            print( event )
            decoded_event = self.decode_event( event )
            if decoded_event['type'] in ['BUTTON', 'AXIS', 'HAT']:
                device = self.devices.get(event.instance_id, None)
                if device:
                    try:
                        logger.debug( 'Sending Event: %s' % str(decoded_event) )
                        device.send_event( decoded_event )
                    except ConnectionResetError:
                        logger.error( 'Server Connection Error from %s:%d, Restablishing connection' % (device.host,device.port) )
                        device.initialize_client_socket()
                    except BrokenPipeError:
                        logger.error( 'Client Connection Lost to %s:%d, Restablishing connection' % (device.host,device.port) )
                        device.initialize_client_socket()
            elif decoded_event['type'] == 'MGMT':
                logger.debug( 'Management Event: %s %s' % (decoded_event['name'], decoded_event['value']) )
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

