from XRPLib.defaults import *

from xrp_control_base import XrpControl, read_config

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
class XrpArcade(XrpControl):
    def __init__(self, config):
        super().__init__(config)


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

    # create the instance of the XRP controller and launch the run loop
    controller = XrpArcade( config ).run()

