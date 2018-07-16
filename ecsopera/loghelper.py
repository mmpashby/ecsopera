# pylint: disable=C0111,E1111,W0511
import logging
from ecsopera.asciistr import ecsopera_title


class LogHelper(object):
    """A ecsopera logging helper class."""

    def __init__(self, stream, level, fmt):
        self.banner = ecsopera_title
        self.stream = stream
        self.level = level
        self.fmt = fmt
        self.cmdname = 'ecsopera:'
        self.lstartfin = '###'
        self.bconfig = logging.basicConfig(stream=self.stream,
                                           level=self.level,
                                           format=self.fmt)

    def _join_log_msg(self, msg):
        return '{0} {1} {2} {3}'.format(self.lstartfin,
                                        self.cmdname,
                                        msg,
                                        self.lstartfin)

    def error(self, msg):
        return logging.error(self._join_log_msg(msg))

    def warn(self, msg):
        return logging.warning(self._join_log_msg(msg))

    def info(self, msg):
        return logging.info(self._join_log_msg(msg))

    # TODO: Include project info into this method as part of banner.
    def display_banner(self):
        print(self.banner)
