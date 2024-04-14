
from evdev import InputDevice, categorize, ecodes, KeyEvent, list_devices

import argparse
import logging
import sys
import threading
import time

from logger import logger

SUPPORTED_DEVICES = (
    "Logitech Gamepad F310"
    )

class Joystick:

    BUTTONS = {
        304: { 'name': 'ButtonA' },
        305: { 'name': 'ButtonB' },
        307: { 'name': 'ButtonX' },
        308: { 'name': 'ButtonY' },
        310: { 'name': 'LeftBumper' },
        311: { 'name': 'RightBumper' },
        314: { 'name': 'Select' },
        315: { 'name': 'Start' },
        317: { 'name': 'LeftThumb' },
        318: { 'name': 'RightThumb' }
    }

    BUTTON_STATES = {
        0: 'RELEASED',
        1: 'PRESSED'
    }

    AXIS_TYPES = {
        0:  { 'name': 'LeftJoystickX', 'min': -32768, 'max': 32767 },
        1:  { 'name': 'LeftJoystickY', 'min': -32768, 'max': 32767 },
        2:  { 'name': 'LeftTrigger', 'min': 0, 'max': 255 },
        3:  { 'name': 'RightJoystickX', 'min': -32768, 'max': 32767 },
        4:  { 'name': 'RightJoystickY', 'min': -32768, 'max': 32767 },
        5:  { 'name': 'RightTrigger', 'min': 0, 'max': 255 },
        16: { 'name': 'HatX', 'min': -1, 'max': 1 },
        17: { 'name': 'HatY', 'min': -1, 'max': 1 }
    }

    def __init__(self, path=None):
        self.gamepad = None
        self.terminate_read_loop = False

        while not self.gamepad:
            if path:
                self.gamepad = InputDevice(path)
            else:
                devices = [InputDevice(path) for path in list_devices()]
                for device in devices:
                    if device.name in SUPPORTED_DEVICES:
                        logger.info( 'Gamepad Detected - %s' % str(device) )
                        self.gamepad = InputDevice(device.path)
                        break
            if not self.gamepad:
                logger.error( 'No Gamepad Controller Detected, retrying' )
                time.sleep(2)

    def decode_event(self, event):
        decoded_event = { 'type': 'UNKNOWN', 'name': '', 'value': event.value }

        if event.type == ecodes.EV_SYN:
            decoded_event['type'] = 'SYN'
        elif event.type == ecodes.EV_KEY:
            decoded_event['type'] = 'BUTTON'
            button = self.BUTTONS.get(event.code, None)
            if button:
                decoded_event['name'] = button['name']
                decoded_event['value'] = event.value
        elif event.type == ecodes.EV_ABS:
            decoded_event['type'] = 'AXIS'
            axis = self.AXIS_TYPES.get(event.code, None)
            if axis:
                decoded_event['name'] = axis['name']
                decoded_event['value'] = event.value / axis['max']
                decoded_event['rounded_value'] = round((event.value / axis['max']), 2)

        return decoded_event

    def read(self):
        for event in self.gamepad.read_loop():
            decoded_event = self.decode_event( event )
            if decoded_event['type'] == 'SYN':
                # ignore the SYN event types, not much to do with them
                pass
            elif decoded_event['type'] == 'BUTTON':
                processed_state = self.BUTTON_STATES.get(decoded_event['value'], 'UNKNOWN')
                logger.debug( 'Button Type: %s, Value: %s' % (decoded_event['name'], processed_state) )
            elif decoded_event['type'] == 'AXIS':
                logger.debug( 'Axis Type: %s, Value: %f' % (decoded_event['name'], decoded_event['value']) )
            else:
                logger.info( 'Unknown Event Type: %d, Code: %d, Value: %f' % (event.type, event.code, event.value) )

            # if something has set the terminate flag on this instance, then break out of the read loop and return
            if self.terminate_read_loop:
                break

def get_joysticks():
    joysticks = []
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
        if device.name in SUPPORTED_DEVICES:
            joysticks.append( device )
    return joysticks

def print_devices():
    print( 'Connected Devices:' ) 
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
        print( '\t%s' % str(device) )

def read_thread( joystick ):
    print( 'Starting read loop...' ) 
    joystick.read()
    print( 'Read loop returned.' ) 

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    #
    # parse out the command arguments
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list', action='store_true', dest='list_devices', default=False)
    options = parser.parse_args()

    if options.list_devices:
        print_devices()
        sys.exit(0)

    joysticks = list()
    service_threads = list()
    controllers = get_joysticks()
    for controller in controllers:
        joystick = Joystick(path = controller.path)
        logger.info( 'Creating service thread for %s' % controller.path )
        x = threading.Thread( target=read_thread, args=(joystick,), daemon=True )
        service_threads.append( x )
        joysticks.append(joystick)
        x.start()

    done = False
    while not done:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            done = True
            print( 'Terminating joystick service threads' )
            for joystick in joysticks:
                joystick.terminate_read_loop = True

    time.sleep(2)
    print( 'Joystick servicing terminated' )
