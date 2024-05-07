
import logging
import threading
import time

from logger import logger

from adafruit_ble import BLERadio

class BluetoothManager():
    def __init__(self):
        logger.info( 'Creating Bluetooth Manager' )
        self.shutdown_flag = False
        self.devices = dict()
        self.scan_list = None
        self.ble = BLERadio()

        self.mutex = threading.Lock()

        scanner_thread = threading.Thread( target=self.bluetooth_scanner, daemon=True )
        scanner_thread.start()

    def bluetooth_scanner(self):
        logger.info( 'BLE_MGR: Launching Bluetooth Scanner' )
        while self.shutdown_flag == False:
            with self.mutex:
                logger.info( 'BLE_MGR: Scanning For XRP Bluetooth Devices' )
                for entry in self.ble.start_scan(timeout=60, minimum_rssi=-80):
                    if entry.complete_name:
                        #logger.info( 'BLE_MGR: Discovered XRP device: %s' % entry.complete_name )
                        add_device = False
                        if self.scan_list:
                            if entry.complete_name in self.scan_list:
                                add_device = True
                        else:
                            if entry.complete_name.startswith( 'XRP' ):
                                add_device = True

                        if add_device:
                            logger.info( 'BLE_MGR: Saving XRP device: %s' % entry.complete_name )
                            self.devices[entry.complete_name] = entry
                            self.ble.stop_scan()
                            break
            time.sleep(1)
        logger.info( 'BLE_MGR: Bluetooth Scanner Terminated' )

    def get_device(self, device_name):
        device=None
        with self.mutex:
            device = self.devices.get(device_name, None)
        return device

    def connect_device(self, entry):
        connection = None
        with self.mutex:
            logger.info( 'BLE_MGR: Connecting To Bluetooth Device: %s' % entry.complete_name )
            connection = self.ble.connect(entry)
            del self.devices[entry.complete_name]

        return connection

    def add_device_to_scan(self,name):
        if self.scan_list == None:
            self.scan_list = list()
        if name not in self.scan_list:
            logger.info( 'BLE_MGR: Adding XRP device to scan list: %s' % name )
            self.scan_list.append(name)
    def remove_device_from_scan(self,name):
        if self.scan_list:
            if name in self.scan_list:
                logger.info( 'BLE_MGR: Removing XRP device from scan list: %s' % name )
                self.scan_list.remove( name )


    def shutdown(self):
        logger.info( 'BLE_MGR: Bluetooth Manager Shutdown Requested' )
        self.shutdown_flag = True

