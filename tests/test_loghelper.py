from ecsopera.asciistr import ecsopera_title
from ecsopera.version import __version__
import sys
import logging
import pytest


class TestLogHelper(object):

    def _join_log_msg(self, msg):
        return '{0} {1} {2} {3}'.format(self.lstartfin,
                                        self.cmdname,
                                        str(msg),
                                        self.lstartfin)

    def error(self, msg):
        return logging.error(self._join_log_msg(msg))

    def warn(self, msg):
        return logging.warning(self._join_log_msg(msg))

    def info(self, msg):
        return logging.info(self._join_log_msg(msg))

    @pytest.mark.parametrize('msg', [
        'This is a error log message.',
        'This is another error log message.',
        123
    ])
    def test_error(self, msg):
        self.bconfig = logging.basicConfig(stream=sys.stdout,
                                           level=logging.ERROR,
                                           format='%(levelname)s %(message)s')
        self.lstartfin = '###'
        self.cmdname = 'ecsopera:'
        expected_log = logging.error(msg)
        assert self.error(msg) == expected_log

    @pytest.mark.parametrize('msg', [
        'This is a warn log message.',
        'This is another warn log message.',
        123456
    ])
    def test_warn(self, msg):
        self.bconfig = logging.basicConfig(stream=sys.stdout,
                                           level=logging.WARNING,
                                           format='%(levelname)s %(message)s')
        self.lstartfin = '###'
        self.cmdname = 'ecsopera:'
        expected_log = logging.warning(msg)
        assert self.warn(msg) == expected_log

    @pytest.mark.parametrize('msg', [
        'This is a info log message.',
        'This is another info log message.',
        12345
    ])
    def test_info(self, msg):
        self.bconfig = logging.basicConfig(stream=sys.stdout,
                                           level=logging.INFO,
                                           format='%(levelname)s %(message)s')
        self.lstartfin = '###'
        self.cmdname = 'ecsopera:'
        expected_log = logging.info(msg)
        assert self.info(msg) == expected_log

    @pytest.mark.parametrize('msg', [
        'This is an awesome log message.',
        'This is also an awesome log message.',
        1234
    ])
    def test__join_log_msg(self, msg):
        self.lstartfin = '###'
        self.cmdname = 'ecsopera:'
        expected_joined_msg = '{0} {1} {2} {3}'.format(self.lstartfin,
                                                       self.cmdname,
                                                       msg,
                                                       self.lstartfin)
        assert self._join_log_msg(msg) == expected_joined_msg

    def test_banner(self):
        self.banner = ecsopera_title
        self.projver = __version__
        assert isinstance(self.projver, str)
        assert isinstance(self.banner, str)
