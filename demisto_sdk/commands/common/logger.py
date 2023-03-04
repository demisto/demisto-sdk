import logging
import logging.config
from logging.handlers import RotatingFileHandler

# from rich.logging import RichHandler

LOG_FILE: str = "./demisto_sdk_debug.log"

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


escapes = {
    "[bold]": "\033[0m",
    "[disable]": "\033[0m",
    "[underline]": "\033[0m",
    "[reverse]": "\033[0m",
    "[strikethrough]": "\033[0m",
    "[invisible]": "\033[0m",
    "[/bold]": "\033[01m",
    "[/disable]": "\033[02m",
    "[/underline]": "\033[04m",
    "[/reverse]": "\033[07m",
    "[/strikethrough]": "\033[09m",
    "[/invisible]": "\033[08m",
    "[black]": "\033[30m",
    "[red]": "\033[31m",
    "[green]": "\033[32m",
    "[orange]": "\033[33m",
    "[blue]": "\033[34m",
    "[purple]": "\033[35m",
    "[cyan]": "\033[36m",
    "[lightgrey]": "\033[37m",
    "[darkgrey]": "\033[90m",
    "[lightred]": "\033[91m",
    "[lightgreen]": "\033[92m",
    "[yellow]": "\033[93m",
    "[lightblue]": "\033[94m",
    "[pink]": "\033[95m",
    "[lightcyan]": "\033[96m",
    "[/black]": "\033[0m",
    "[/red]": "\033[0m",
    "[/green]": "\033[0m",
    "[/orange]": "\033[0m",
    "[/blue]": "\033[0m",
    "[/purple]": "\033[0m",
    "[/cyan]": "\033[0m",
    "[/lightgrey]": "\033[0m",
    "[/darkgrey]": "\033[0m",
    "[/lightred]": "\033[0m",
    "[/lightgreen]": "\033[0m",
    "[/yellow]": "\033[0m",
    "[/lightblue]": "\033[0m",
    "[/pink]": "\033[0m",
    "[/lightcyan]": "\033[0m",
}


def logging_setup(
    console_log_threshold=logging.INFO,
    file_log_threshold=logging.DEBUG,
) -> logging.Logger:
    """Init logger object for logging in demisto-sdk
        For more info - https://docs.python.org/3/library/logging.html

    Args:
        console_log_threshold(int): Minimum console log threshold. Defaults to logging.INFO
        file_log_threshold(int): Minimum console log threshold. Defaults to logging.INFO

    Returns:
        logging.Logger: logger object
    """

    # console_handler = RichHandler(
    #     level=console_log_threshold,
    #     rich_tracebacks=True,
    # )
    console_handler = logging.StreamHandler()
    console_handler.set_name("console-handler")
    console_handler.setLevel(console_log_threshold)

    class ColorConsoleFormatter(logging.Formatter):
        def __init__(
            self,
        ):
            super().__init__(
                fmt="%(message)s",
                datefmt=DATE_FORMAT,
            )

        def format(self, record):
            message = logging.Formatter.format(self, record)
            message = self.replace_escapes(message)
            return message

        def replace_escapes(self, message):
            for key in escapes:
                message = message.replace(key, escapes[key])
            return message

    console_formatter = ColorConsoleFormatter()
    console_handler.setFormatter(fmt=console_formatter)

    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
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


def get_log_file():
    # TODO Return the actual (if overridden) log file
    return LOG_FILE


def set_propagate(logger_to_update: logging.Logger, propagate: bool = False):
    logger_to_update.propagate = propagate


logging_setup()
logger = logging.getLogger("demisto-sdk")


# Python program to print
# colored text and background
class Colors:
    """Colors class:reset all colors with colors.reset;
    two sub classes fg for foreground
    and bg for background;
    use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.green
    also, the generic bold, disable,
    underline, reverse, strike through,
    and invisible work with the main class
    i.e. colors.bold"""

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
