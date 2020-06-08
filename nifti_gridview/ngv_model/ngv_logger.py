import logging
from PySide2 import QtCore
from PySide2.QtCore import QDir
import traceback
import sys


class ngv_logger(logging.Logger):
    logger_name = 'ngv_logger'
    logger = logging.getLogger(logger_name)
    def __init__(self, name=logger_name):
        super(ngv_logger, self).__init__(name)

        logging.basicConfig(format="[%(asctime)-12s-%(levelname)s] %(message)s", filename=QDir.currentPath() +
                                                                                          '/ngv.log',
                            level=logging.DEBUG)

        print(QDir.currentPath())
        sys.excepthook = ngv_logger.exception_hook

    @staticmethod
    def global_log(msg, level=logging.DEBUG, exc_info=None, extra=None, stack_info=False):
        ngv_logger.logger.log(level, msg, exc_info=exc_info, extra=extra, stack_info=stack_info)

    @staticmethod
    def qt_message_handler(mode, context, message):
        if mode == QtCore.QtInfoMsg:
            mode = logging.INFO
        elif mode == QtCore.QtDebugMsg:
            mode = logging.DEBUG
        elif mode == QtCore.QtWarningMsg:
            mode = logging.WARNING
        elif mode == QtCore.QtCriticalMsg:
            mode = logging.CRITICAL
        elif mode == QtCore.QtFatalMsg:
            mode = logging.FATAL
        else:
            mode = logging.DEBUG

        ngv_logger.global_log(mode, message)


    @staticmethod
    def exception_hook(*args):
        ngv_logger.logger.error('Uncaught exception:', exc_info=args)
        traceback.print_tb(args[0])