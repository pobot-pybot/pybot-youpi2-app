# -*- coding: utf-8 -*-

import sys
import signal

from pybot.core import cli
from pybot.core import log

from nros.youpi2.client import ArmClient

from pybot.youpi2.ctlpanel import ControlPanel
from pybot.youpi2.ctlpanel.devices.fs import FileSystemDevice

__author__ = 'Eric Pascual'


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
        log.setup_logging(log_name=log_name)
        log.LogMixin.__init__(self, name=log_name, level=log_level)

        self.pnl = None
        self.arm = None
        self.terminated = False

    def main(self):
        parser = cli.get_argument_parser()
        parser.add_argument('--pnldev', default="/mnt/lcdfs")
        parser.add_argument('--arm-node-name', default="nros.youpi2")

        self.add_custom_arguments(parser)
        sys.exit(self.run(parser.parse_args()))

    def terminate(self, *args):
        self.terminated = True
        self.on_terminate(*args)

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

    def add_custom_arguments(self, parser):
        pass

    def setup(self, **kwargs):
        pass

    def loop(self):
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
