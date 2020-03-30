import logging
import os


def logging_setup(verbose: int, quiet: bool, log_path: str) -> logging.Logger:
    """ Init logger object for logging in demisto-sdk
        For more info - https://docs.python.org/3/library/logging.html

    Args:
        verbose(int) verosity level - 1-3
        quiet(bool): Whether to output a quiet response.
        log_path(str): Path to save log of all levels

    Returns:
        logging.Logger: logger object
    """
    if quiet:
        verbose = 0
    logger: logging.Logger = logging.getLogger('demisto-sdk')
    logger.setLevel(logging.DEBUG)
    log_level = logging.getLevelName((6 - 2 * verbose) * 10)
    fmt = logging.Formatter('%(message)s')

    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(fmt)
        logger.addHandler(console_handler)

    # Setting debug log file if in circleci
    if log_path:
        file_handler = logging.FileHandler(filename=os.path.join(log_path, 'lint_debug_log.log'))
        file_handler.setFormatter(fmt)
        file_handler.setLevel(level=logging.DEBUG)
        logger.addHandler(file_handler)

    logger.propagate = False

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
