import logging
import logging.config
from logging.handlers import RotatingFileHandler

import click

# from rich.logging import RichHandler

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

DEPRECATED_PARAMETERS = {
    "-v": "--console-log-threshold or --file-log-threshold",
    "--verbose": "--console-log-threshold or --file-log-threshold",
    "-q": "--console-log-threshold or --file-log-threshold",
    "--quiet": "--console-log-threshold or --file-log-threshold",
    "-lp": "--log-file",
    "--log-path": "--log-file",
    "-ln": "--log-file",
    "--log-name": "--log-file",
}


def handle_deprecated_args(input_args):
    for current_arg in input_args:
        if current_arg in DEPRECATED_PARAMETERS.keys():
            substitute = DEPRECATED_PARAMETERS[current_arg]
            logger.error(
                f"[red]Argument {current_arg} is deprecated. Please use {substitute} instead.[/red]"
            )


# TODO Remove this method and expose _logging_setup as logging_setup
def logging_setup(
    console_log_threshold=logging.INFO,
    file_log_threshold=logging.DEBUG,
    log_file_name: str = "demisto_sdk_debug_log.log",
    log_file: str = "./demisto_sdk_debug_log.log",
) -> logging.Logger:
    """Init logger object for logging in demisto-sdk
        For more info - https://docs.python.org/3/library/logging.html

    Args:
        quiet(bool): Whether to output a quiet response.
        log_path(str): Path to save log of all levels. Defaults to ".".
        log_file_name(str): Basename of file to save logs to. Defaults to "demisto_sdk_debug_log.log".

    Returns:
        logging.Logger: logger object
    """
    # TODO Translate to the input params of _logging_setup
    return _logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file=log_file,
    )


def _logging_setup(
    console_log_threshold=logging.INFO,
    file_log_threshold=logging.DEBUG,
    log_file: str = "./demisto_sdk_debug_log.log",
) -> logging.Logger:
    """Init logger object for logging in demisto-sdk
        For more info - https://docs.python.org/3/library/logging.html

    Args:
        console_log_threshold(int): Minimum console log threshold. Defaults to logging.INFO
        file_log_threshold(int): Minimum console log threshold. Defaults to logging.INFO
        log_file(str): Path to the log file. Defaults to "./demisto_sdk_debug_log.log".

    Returns:
        logging.Logger: logger object
    """

    # console_handler = RichHandler(
    console_handler = logging.StreamHandler(
        # level=console_log_threshold,
        # rich_tracebacks=True,
    )
    console_handler.set_name("console-handler")
    console_handler.setLevel(console_log_threshold)
    console_formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt=DATE_FORMAT,
    )
    console_handler.setFormatter(fmt=console_formatter)

    file_handler = RotatingFileHandler(
        filename=log_file,
        mode="a",
        maxBytes=1048576,
        backupCount=10,
    )
    file_handler.set_name("file-handler")
    file_handler.setLevel(file_log_threshold)
    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] - [%(threadName)s] - [%(levelname)s] - %(message)s",
        datefmt=DATE_FORMAT,
    )
    file_handler.setFormatter(fmt=file_formatter)

    logging.basicConfig(
        handlers=[console_handler, file_handler],
        level=min(console_handler.level, file_handler.level),
    )

    ret_value: logging.Logger = logging.getLogger("demisto-sdk")
    while ret_value.handlers:
        ret_value.removeHandler(ret_value.handlers[0])
    ret_value.addHandler(console_handler)
    ret_value.addHandler(file_handler)
    ret_value.level = min(console_handler.level, file_handler.level)
    set_propagate(ret_value, False)

    return ret_value


def set_propagate(logger_to_update: logging.Logger, propagate: bool = False):
    previos_propagate = logger_to_update.propagate
    print(f"*** logger.set_propagate, {previos_propagate=}, {propagate=}")
    logger_to_update.propagate = propagate


# logger: logging.Logger = logging_setup()
logging_setup()
logger = logging.getLogger("demisto-sdk")


def debug_color(msg, color: str):
    logger.debug(f"[{color}]{msg}[/{color}]")


def info_color(msg, color: str):
    logger.info(f"[{color}]{msg}[/{color}]")


def secho_and_info(message, fg="white"):
    click.secho(message, fg=fg)
    logger.info(f"[{fg}]{message}[/{fg}]")


def print_and_info(msg):
    print(f"{msg}")
    logger.info(f"{msg}")


# Python program to print
# colored text and background
class Colors:
    """Colors class:reset all colors with colors.reset; two
    sub classes fg for foreground
    and bg for background; use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
    underline, reverse, strike through,
    and invisible work with the main class i.e. colors.bold"""

    reset = "\033[0m"
    bold = "\033[01m"
    disable = "\033[02m"
    underline = "\033[04m"
    reverse = "\033[07m"
    strikethrough = "\033[09m"
    invisible = "\033[08m"

    class Fg:
        """Forgrownd"""

        black = "\033[30m"
        red = "\033[31m"
        green = "\033[32m"
        orange = "\033[33m"
        blue = "\033[34m"
        purple = "\033[35m"
        cyan = "\033[36m"
        lightgrey = "\033[37m"
        darkgrey = "\033[90m"
        lightred = "\033[91m"
        lightgreen = "\033[92m"
        yellow = "\033[93m"
        lightblue = "\033[94m"
        pink = "\033[95m"
        lightcyan = "\033[96m"

    class Bg:
        """Backgrownd"""

        black = "\033[40m"
        red = "\033[41m"
        green = "\033[42m"
        orange = "\033[43m"
        blue = "\033[44m"
        purple = "\033[45m"
        cyan = "\033[46m"
