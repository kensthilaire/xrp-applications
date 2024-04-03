import logging
from traceback import format_exc
import datetime

from schedule import Scheduler


#logger = logging.getLogger('schedule')


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
            print(format_exc())
            #logger.error(format_exc())
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()

