
import time

from .models import Device

def add_or_update_device( config ):
    ret_val = 'Successful'

    hardware_id = config.get( 'hardware_id', None )
    if hardware_id:
        devices = Device.objects.filter(hardware_id = hardware_id)
        if len(devices) == 0:
            print( 'Create New Device' )
            device_obj = Device( hardware_id=hardware_id,
                                 type=config.get('type', 'Unknown'),
                                 name=config.get('name', 'Unassigned'),
                                 ip_address=config.get('ip_address', 'Unassigned'),
                                 port=config.get('port', '9999'),
                                 protocol=config.get('protocol', 'tcp'),
                                 state=config.get('state', 'registered'),
                                 status=config.get('status', 'Unknown')
                         )
            device_obj.save()
        else:
            print( 'Update Existing Device' )
            device_obj = devices[0]
            device_obj.type=config.get('type', 'Unknown')
            device_obj.ip_address=config.get('ip_address', 'Unassigned')
            device_obj.port=config.get('port', '9999')
            device_obj.protocol=config.get('protocol', 'tcp')
            device_obj.state=config.get('state', 'registered')
            device_obj.status=config.get('status', 'Unknown')
            device_obj.application=config.get('application', 'Unknown')
            device_obj.version=config.get('version', 'Unknown')
            device_obj.last_reported = time.time()
            device_obj.save()
    else:
        print( 'No Hardware Device Provided' )

    return ret_val

def delete_device( config ):
    ret_val = 'Successful'

    hardware_id = config.get( 'hardware_id', None )
    if hardware_id:
        Device.objects.filter(hardware_id=hardware_id).delete()
    else:
        print( 'No Hardware Device Provided' )
    return ret_val

def update_device( status_info ):
    ret_val = 'Successful'

    hardware_id = status_info.get( 'hardware_id', None )
    if hardware_id:
        devices = Device.objects.filter(hardware_id = hardware_id)
        if len(devices) == 0:
            print( 'Device %s NOT Found In Registry!' % hardware_id )
        else:
            print( 'Updating Device Status For %s' % hardware_id )
            device_obj = devices[0]
            device_obj.state='running'
            device_obj.status=status_info.get('status', 'Unknown')
            device_obj.last_reported = time.time()
            device_obj.save()
    else:
        print( 'No Hardware Device Provided' )

    return ret_val
