import logging
import os
from datetime import datetime


DEBUG = False


def logging_setup(verbosity=False, logpath=None, logger_name=None):
    logger = logging.getLogger(logger_name)
    logger.removeHandler(logger.handlers.pop())
    log_level = logging.INFO
    fmt = '%(message)s'

    ch = logging.StreamHandler()
    if verbosity:
        log_level = logging.DEBUG
    formatter = logging.Formatter(fmt)
    logger.setLevel(log_level)

    ch.setLevel(level=log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.propagate = False

    if logpath:
        file_handler = logging.FileHandler(
            os.path.join(logpath, f"demisto-sdk-lint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"))

        file_handler.setLevel(logging.DEBUG)

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Python program to print
# colored text and background
class Colors:
    """Colors class:reset all colors with colors.reset; two
    sub classes fg for foreground
    and bg for background; use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
    underline, reverse, strike through,
    and invisible work with the main class i.e. colors.bold"""
    reset = '\033[0m'
    bold = '\033[01m'
    disable = '\033[02m'
    underline = '\033[04m'
    reverse = '\033[07m'
    strikethrough = '\033[09m'
    invisible = '\033[08m'

    class Fg:
        """Forgrownd"""
        black = '\033[30m'
        red = '\033[31m'
        green = '\033[32m'
        orange = '\033[33m'
        blue = '\033[34m'
        purple = '\033[35m'
        cyan = '\033[36m'
        lightgrey = '\033[37m'
        darkgrey = '\033[90m'
        lightred = '\033[91m'
        lightgreen = '\033[92m'
        yellow = '\033[93m'
        lightblue = '\033[94m'
        pink = '\033[95m'
        lightcyan = '\033[96m'

    class Bg:
        """Backgrownd"""
        black = '\033[40m'
        red = '\033[41m'
        green = '\033[42m'
        orange = '\033[43m'
        blue = '\033[44m'
        purple = '\033[45m'
        cyan = '\033[46m'
