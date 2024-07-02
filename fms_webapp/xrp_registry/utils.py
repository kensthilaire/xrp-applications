
import time
import datetime

from .models import Device
from .logger import logger

def add_or_update_device( config, update_config=False ):
    ret_val = 'Successful'

    logger.debug( 'Add/Update Device: %s' % str(config) )

    hardware_id = config.get( 'hardware_id', None )
    if hardware_id:
        devices = Device.objects.filter(hardware_id = hardware_id)
        if len(devices) == 0:
            logger.info( 'Create New Device: %s' % hardware_id )
            device_obj = Device( hardware_id=hardware_id,
                                 type=config.get('type', 'Unknown'),
                                 name=config.get('name', 'Unassigned'),
                                 ip_address=config.get('ip_address', 'Unassigned'),
                                 port=config.get('port', '9999'),
                                 protocol=config.get('protocol', 'tcp'),
                                 state=config.get('state', 'registered'),
                                 status=config.get('status', 'Unknown'),
                                 alliance=config.get('alliance', 'any'),
                                 application=config.get('application', ''),
                                 version=config.get('version', ''),
                                 ble_service=config.get('ble_service', '')
                         )
            device_obj.save()
        else:
            logger.info( 'Update Existing Device: %s' % hardware_id )
            device_obj = devices[0]
            device_obj.type=config.get('type', 'Unknown')
            device_obj.ip_address=config.get('ip_address', 'Unassigned')
            device_obj.last_timestamp = int(time.time())

            # Only update these configuration items if the update flag is set. This is done to ensure that
            # the devices themselves do not update certain configuration parameters that the FMS itself 
            # is expected to override.
            if update_config == True:
                device_obj.port=config.get('port', '9999')
                device_obj.protocol=config.get('protocol', 'tcp')
                try:
                    device_obj.name=config['name']
                except KeyError:
                    pass
                
                try:
                    device_obj.alliance=config['alliance']
                except KeyError:
                    pass
            else:
                device_obj.last_reported = datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p' )

            # add in the optional parameters if they are specified in the update
            try:
                device_obj.application=config['application']
            except KeyError:
                pass
            try:
                device_obj.state=config['state']
            except KeyError:
                pass
            try:
                device_obj.status=config['status']
            except KeyError:
                pass
            try:
                device_obj.version=config['version']
            except KeyError:
                pass
            try:
                device_obj.ble_service=config['ble_service']
            except KeyError:
                pass

            device_obj.save()

    else:
        logger.info( 'No Hardware Device Provided' )

    return ret_val

def delete_device( config ):
    ret_val = 'Successful'

    hardware_id = config.get( 'hardware_id', None )
    if hardware_id:
        Device.objects.filter(hardware_id=hardware_id).delete()
    else:
        logger.info( 'No Hardware Device Provided' )
    return ret_val

def update_device_status( status_info ):
    ret_val = 'Successful'

    hardware_id = status_info.get( 'hardware_id', None )
    if hardware_id:
        devices = Device.objects.filter(hardware_id = hardware_id)
        if len(devices) == 0:
            logger.info( 'Device %s NOT Found In Registry!' % hardware_id )
        else:
            logger.info( 'Updating Device Status For %s' % hardware_id )
            device_obj = devices[0]
            device_obj.state='running'
            device_obj.status=status_info.get('status', 'Unknown')
            device_obj.last_reported = datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p' )
            device_obj.last_timestamp = int(time.time())
            device_obj.save()
    else:
        logger.info( 'No Hardware Device Provided' )

    return ret_val

