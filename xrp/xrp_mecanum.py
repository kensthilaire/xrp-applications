from XRPLib.defaults import *

import asyncio

from xrp_control import XrpControl, read_config

from xrp_led_strip import XrpLedStrip

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

left_rear_motor = EncodedMotor.get_default_encoded_motor(index=3)
right_rear_motor = EncodedMotor.get_default_encoded_motor(index=4)

#
# Main control class for the XRP application.
#
class XrpMecanum(XrpControl):
    def __init__(self, config):
        super().__init__(config, application='XRP_Mecanum')
        
        self.current_twist = 0.0
        self.motor_effort = [0.0, 0.0, 0.0, 0.0]

        self.xrp_bling = None
        led_config = config.get('led_strip')
        if led_config:
            try:
                self.xrp_bling = XrpLedStrip()
            except:
                print('Error initializing XRP LED Strip')

    async def drive_task(self):
        print( 'Starting Mecanum Drive Task')
        while True:
            # set the effort of each wheel based on the current axis values
            self.motor_effort[0] = self.current_speed - self.current_turn + self.current_twist
            self.motor_effort[1] = self.current_speed + self.current_turn - self.current_twist
            self.motor_effort[2] = self.current_speed + self.current_turn + self.current_twist
            self.motor_effort[3] = self.current_speed - self.current_turn - self.current_twist
            
            # find the maximum value across all the effort values so that we can normalize
            # them for the valid range 0.0-1.0
            max_effort = 0.0
            for effort in self.motor_effort:
                if effort > max_effort:
                    max_effort = effort
            
            # if the maximum effort exceeds 1.0, then scale all the values relative to the
            # maximum values
            if max_effort > 1.0:
                for i in range(0,len(self.motor_effort)):
                    self.motor_effort[i] /= max_effort
            
            # set the effort for each of the motors, keeping in mind that the rear motor
            # settings need to be inverted
            left_motor.set_effort( self.motor_effort[0] )
            right_motor.set_effort( self.motor_effort[1] )
            left_rear_motor.set_effort( self.motor_effort[2] * -1.0 )
            right_rear_motor.set_effort( self.motor_effort[3] * -1.0 )

            # pause to allow other tasks to run
            await asyncio.sleep_ms(20)

    #
    # Function processes the Event command, interpreting the event type and 
    # invoking the appropriate robot control behavior specified by the event
    #
    def process_event( self, event, args ):
        #print( 'Processing Event: %s, Args %s' % (event,str(args)))
        if event == 'LeftJoystickY':
            self.current_speed = float(args[0]) * -1.0
        elif event == 'LeftJoystickX':
            self.current_turn = float(args[0]) * -1.0
        elif event == 'RightJoystickX':
            self.current_twist = float(args[0]) * 1.0
        elif event == 'ButtonA':
            if int(args[0]) == 1:
                if self.xrp_bling:
                    self.xrp_bling.set_color('green', toggle=True)
        elif event == 'ButtonB':
            if int(args[0]) == 1:
                if self.xrp_bling:
                    self.xrp_bling.set_color('red', toggle=True)
        elif event == 'ButtonX':
            if int(args[0]) == 1:
                if self.xrp_bling:
                    self.xrp_bling.set_color('blue', toggle=True)
        elif event == 'ButtonY':
            if int(args[0]) == 1:
                if self.xrp_bling:
                    self.xrp_bling.set_color('yellow', toggle=True)
        else:
            # add more event handling operations here...
            super().process_event(event, args)

if __name__ == '__main__':

    # read the config.json file located in the base directory
    config = read_config()

    # create the instance of the XRP controller and launch the run loop
    controller = XrpMecanum( config )
    if controller:
        print( 'Starting Controller Main Loop...')
        asyncio.run(controller.run())

