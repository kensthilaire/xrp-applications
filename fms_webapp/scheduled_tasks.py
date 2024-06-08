import argparse
import datetime
import django
import logging
import os
import time

from schedule import Scheduler
from traceback import format_exc

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fms.settings")

django.setup()

from xrp_registry.models import Device
from xrp_registry.logger import logger

class SafeScheduler(Scheduler):
    """
    An implementation of Scheduler that catches jobs that fail, logs their
    exception tracebacks as errors, optionally reschedules the jobs for their
    next run time, and keeps going.

    Use this to run jobs that may or may not crash without worrying about
    whether other jobs will run or if they'll crash the entire script.
    """

    def __init__(self, reschedule_on_failure=True):
        """
        If reschedule_on_failure is True, jobs will be rescheduled for their
        next run as if they had completed successfully. If False, they'll run
        on the next run_pending() tick.
        """
        self.reschedule_on_failure = reschedule_on_failure
        Scheduler.__init__(self)

    def _run_job(self, job):
        try:
            Scheduler._run_job(self,job)
        except Exception:
            logger.error(format_exc())
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()


def check_device_status():
    logger.info( 'Checking Device Reported Status' )
    devices = Device.objects.all()
    curr_time = int(time.time())

    for device in devices: 
        since_reported = curr_time - device.last_timestamp
        if since_reported > 300 and device.state != 'unknown':
            logger.info( 'Marking device status to unknown for device: %s' % device.hardware_id )
            device.state = 'unknown'
            device.save()

    logger.info( 'Device Status Check Complete.' )
            
if __name__ == '__main__':

    # 
    # parse out the command arguments
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', default=False)
    options = parser.parse_args()

    # set the log level to debug if requested
    if options.debug:
        logger.setLevel(logging.DEBUG)
    else: 
        logger.setLevel(logging.INFO)

    scheduler = SafeScheduler()
    scheduler.every(60).seconds.do(check_device_status)

    check_device_status()

    delay = 0.5
    while True:
        try:
            scheduler.run_pending()
            time.sleep( delay )
        except KeyboardInterrupt:
            break

