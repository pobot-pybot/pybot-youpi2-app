# -*- coding: utf-8 -*-

import sys
import signal

from pybot.core import cli
from pybot.core import log

from nros.youpi2.client import ArmClient

from pybot.youpi2.ctlpanel import ControlPanel
from pybot.youpi2.ctlpanel.devices.fs import FileSystemDevice

__author__ = 'Eric Pascual'

_sig_names = {
    getattr(signal, s): s
    for s in (s for s in dir(signal) if s.startswith('SIG') and not s.startswith('SIG_'))
}


class YoupiApplication(log.LogMixin):
    """ Base class for creating applications for the Youpi2 environment.

    This class takes care of getting access to the hardware resources (panel and arm)
    and making them available as attributes and setting up the common aspects of a
    typical application. It handles base CLI arguments too for specifying the panel
    file system path and the arm nROS name in case non-default values are needed.

    Termination signals sent by the shell are handled so that the application core
    loop is exited gracefully, and the termination process is invoked for any required
    cleanup before leave.

    Defining a concrete application consists in sub-classing this class and defining
    the appropriate extension points.

    The class extension points are:
        `add_custom_arguments`
            for adding addition CLI arguments if needed

        `setup`
            invoked at the beginning for initializing specific aspects of the application

        `loop`
            invoked repeatedly until the application terminates. This method should not include
            the application loop itself, otherwise the termination signal will not be handled
            properly

        `teardown`
            invoked once the main loop is exited, whatever way (normal termination or error
            condition)

        `on_terminate`
            callback invoked when an external terminate signal has been caught. The application
            `terminated` attribute has already been set when invoked.

        `on_run_error`
            callback invoked when an expected error is caught

        `on_unexpected_error`
            callback invoked when an unexpected error is caught

    Since these extension points are empty by default, there is no need to invoke `super` in
    sub-classes.
    """
    NAME = 'app'
    TITLE = "Youpi application"
    VERSION = None

    def __init__(self, log_level=log.INFO):
        log_name = 'youpi2-' + self.NAME
        log.setup_logging(log_name=log_name, debug=log_level==log.DEBUG)
        log.LogMixin.__init__(self, name=log_name, level=log_level)

        self.pnl = None
        self.arm = None
        self.terminated = False

    @classmethod
    def main(cls):
        parser = cli.get_argument_parser()
        parser.add_argument('--pnldev', default="/mnt/lcdfs")
        parser.add_argument('--arm-node-name', default="nros.youpi2")
        cls.add_custom_arguments(parser)

        args = parser.parse_args()
        app = cls(log_level=log.DEBUG if (args.debug or args.verbose) else log.INFO)
        sys.exit(app.run(args))

    def terminate(self, sig, frame):
        self.terminated = True
        self.log_info('!! signal %s caught', _sig_names[sig])
        self.on_terminate(sig, frame)

    def clear_screen(self):
        self.pnl.clear()
        self.pnl.center_text_at(self.TITLE, line=1)

    def run(self, args):
        self.log_starting_banner(self.VERSION)

        self.log_info('creating control panel device (path=%s)', args.pnldev)
        self.pnl = ControlPanel(FileSystemDevice(args.pnldev))

        self.log_info('getting access to the arm nROS node (name=%s)', args.arm_node_name)
        self.arm = ArmClient(args.arm_node_name)

        signal.signal(signal.SIGTERM, self.terminate)
        signal.signal(signal.SIGINT, self.terminate)

        self.clear_screen()

        exit_code = 0
        try:
            self.log_info('invoking application setup')
            self.setup(**args.__dict__)
        except Exception as e:
            self.log_exception(e)
            self.on_run_error(e)

            self.pnl.display_error(e)
            exit_code = 1
        else:
            try:
                self.log_info('starting application loop')
                loop_stop = False
                while not self.terminated and not loop_stop:
                    loop_stop = self.loop()
            except Exception as e:
                self.log_exception(e)
                self.on_unexpected_error(e)

                self.pnl.display_error(e)
                exit_code = 1
            finally:
                self.clear_screen()
                self.pnl.center_text_at('terminating', 3)

                self.log_info('invoking application teardown with exit_code=%s', exit_code)
                self.teardown(exit_code)

                self.arm.soft_hi_Z()
                self.logger.info('arm set in Hi-Z')

        self.log_info('returning with exit_code=%s', exit_code)
        return exit_code

    @classmethod
    def add_custom_arguments(cls, parser):
        pass

    def setup(self, **kwargs):
        pass

    def loop(self):
        """ Sub-class will override this method most of the time, by providing
        the code to be executed repeatedly.

        The method can return True if the application must exit its main loop.
        There is no need to return False otherwise, since None is
        defaulted by Python if no explicit return value.

        .. WARNING::

            Do not code the main loop yourself here, otherwise the external
            interruption signal will not be properly handled.
        """
        pass

    def teardown(self, exit_code):
        pass

    def on_run_error(self, e):
        pass

    def on_unexpected_error(self, e):
        pass

    def on_terminate(self, *args):
        pass


class ApplicationError(Exception):
    pass
