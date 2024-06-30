import platform
import logging
import logging.handlers

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('XrpLogger')
logger.setLevel(logging.INFO)

os_type = platform.system()
if os_type == 'Linux':
    syslog_address = '/dev/log'
elif os_type == 'Darwin':
    syslog_address = '/var/run/syslog'
elif os_type == 'Windows':
    syslog_address = ('localhost', 514)

handler = logging.handlers.SysLogHandler(address = syslog_address)
logger.addHandler(handler)

