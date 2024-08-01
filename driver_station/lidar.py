
import argparse
import logging
import threading
import time
import traceback

from rplidar import RPLidar

from logger import logger

#
# Lidar is a class derived from the base RP Lidar class which contains all the
# the underlying driver code that provides the interface to the Slamtec RP Lidar
# devices.
#
# This class wraps the base class with some higher level operations that can be used
# to control a robot.
#
class Lidar(RPLidar):

    def __init__(self, port='/dev/ttyUSB0', debug=False):
        super().__init__( port )       

        self.debug = debug
        self.cancel_scan = False
        self.capture_ranges = None
        self.scan_lock = threading.Lock()

        # set the max distance to 25 meters, converting to inches for ease of use
        self.MAX_DISTANCE = int(25 * 39.37)

        self.reset_closest()

    def get_closest(self):
        with self.scan_lock:
            closest = self.closest
        return closest

    def reset_closest(self):
        with self.scan_lock:
            self.closest = { 'valid': False, 'distance': self.MAX_DISTANCE, 'angle': 0 }

    def update_closest(self, distance, angle):
        with self.scan_lock:
            if distance < self.closest['distance']:
                self.closest['distance'] = distance
                self.closest['angle'] = angle
                self.closest['valid'] = True

    def range_scan(self, ranges=((0,359)), min_distance=42):
        self.debug = True
        if self.debug:
            logger.debug( 'Capture Ranges: %s' % str(ranges) )

        for i, scan in enumerate(self.iter_scans()):

            scan_map = [self.MAX_DISTANCE] * 360

            for measurement in scan:
                if self.cancel_scan:
                    return

                distance = measurement[2]/25.4
                try:
                    if distance <= min_distance:
                        scan_map[int(measurement[1])] = distance
                except IndexError:
                    try:
                        scan_map[(int(measurement[1])-360)] = distance
                    except IndexError:
                        logger.info( 'Error indexing into scan map - %d' % int(measurement[1]) )

            for range in ranges:
                curr_closest = min(scan_map[range[0]:range[1]])
                curr_angle = scan_map.index(curr_closest) 
                self.update_closest( curr_closest, curr_angle )

    def cancel(self):
        self.cancel_scan = True
        self.scan_thread.join()

    def terminate(self):
        self.stop()
        self.stop_motor()
        self.disconnect()

    def build_ranges(self,range_str):
        self.capture_ranges = []
        ranges = range_str.replace(' ','').split(',')
        for range in ranges:
            range_spec = range.split('-')
            self.capture_ranges.append( (int(range_spec[0]),int(range_spec[1])) )

    def closest_in_range(self, ranges=None, min_distance=42, sample_interval=0.05, callback=None):

        if ranges == None:
            ranges = self.capture_ranges

        self.cancel_scan = False
        self.scan_thread = threading.Thread(target=self.range_scan, args=(ranges,min_distance,))
        self.scan_thread.start()

        while self.cancel_scan == False:
            time.sleep(sample_interval)
            if callback:
                callback( self.get_closest() )
            self.reset_closest()

    def print_scan_data(self,scan_data):
        if scan_data.get('valid', False)==True:
            logger.debug( 'Closest scan measurement in capture zone is: %0.1f at angle: %d' % (scan_data['distance'], scan_data['angle']) )
    

if __name__ == '__main__':

    #
    # parse out the command arguments
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', dest='debug', default=False)
    parser.add_argument('-d', '--distance', action='store', dest='distance', default='42')
    parser.add_argument('-r', '--range', action='store', dest='range', default='0-359')
    parser.add_argument('-p', '--port', action='store', dest='port', default='/dev/ttyUSB0')
    options = parser.parse_args()

    if options.debug:
        logger.setLevel(logging.DEBUG)

    #
    # program supports multiple capture ranges for the scan, defined as a comma-separated
    # set of ranges (e.g. '0-45,315-360' will capture the 90 degrees towards the front
    # of the LIDAR device). 
    #
    capture_ranges = []
    ranges = options.range.replace(' ','').split(',')
    for range in ranges:
        range_spec = range.split('-')
        capture_ranges.append( (int(range_spec[0]),int(range_spec[1])) )

    # initialize the lidar device itself
    lidar = Lidar(options.port, options.debug)

    #
    # dump out the info block for the lidar and display the health of the device
    #
    logger.debug(lidar.get_info())
    logger.debug(lidar.get_health())

    #
    # perform the requested scan operation
    #
    try:

        # launch the operation which will terminate only upon either an exception or a keyboard interrupt (ctrl-C)
        lidar.closest_in_range(ranges=capture_ranges, min_distance=int(options.distance),
                               sample_interval=0.05, callback=lidar.print_scan_data)

    except KeyboardInterrupt:
        logger.debug( 'Canceling LIDAR scan' )
        lidar.cancel()
    except:
        logger.info( 'Unexpected Exception Encountered During Scan Operation' )
        traceback.print_exc()

    #
    # we need to cleanly shut down the LIDAR device before exiting
    #
    logger.info( 'Shutting down LIDAR' )
    lidar.terminate()

    logger.info( 'Done' )
