import logging
import logging.config
import os.path
from logging.handlers import RotatingFileHandler
from pathlib import Path

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH

logger: logging.Logger = logging.getLogger("demisto-sdk")

CONSOLE_HANDLER = "console-handler"
FILE_HANDLER = "file-handler"

LOG_FILE_NAME: str = "demisto_sdk_debug.log"

LOG_FILE_PATH: Path = CONTENT_PATH / LOG_FILE_NAME
current_log_file_path: Path = LOG_FILE_PATH

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

DEPRECATED_PARAMETERS = {
    "-v": "--console-log-threshold or --file-log-threshold",
    "-vv": "--console-log-threshold or --file-log-threshold",
    "-vvv": "--console-log-threshold or --file-log-threshold",
    "--verbose": "--console-log-threshold or --file-log-threshold",
    "-q": "--console-log-threshold or --file-log-threshold",
    "--quiet": "--console-log-threshold or --file-log-threshold",
    "-ln": "--log-path",
    "--log-name": "--log-path",
    "no_logging": "--console-log-threshold or --file-log-threshold",
}


def handle_deprecated_args(input_args):
    for current_arg in input_args:
        if current_arg in DEPRECATED_PARAMETERS.keys():
            substitute = DEPRECATED_PARAMETERS[current_arg]
            logging.getLogger("demisto-sdk").error(
                f"[red]Argument {current_arg} is deprecated. Please use {substitute} instead.[/red]"
            )


escapes = {
    "[bold]": "\033[01m",
    "[disable]": "\033[02m",
    "[underline]": "\033[04m",
    "[reverse]": "\033[07m",
    "[strikethrough]": "\033[09m",
    "[invisible]": "\033[08m",
    "[/bold]": "\033[0m",
    "[/disable]": "\033[0m",
    "[/underline]": "\033[0m",
    "[/reverse]": "\033[0m",
    "[/strikethrough]": "\033[0m",
    "[/invisible]": "\033[0m",
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


def get_handler_by_name(logger: logging.Logger, handler_name: str):
    for current_handler in logger.handlers:
        if current_handler.get_name == handler_name:
            return current_handler
    return None


def set_demisto_logger(demisto_logger: logging.Logger):
    global logger
    logger = demisto_logger


def logging_setup(
    console_log_threshold=logging.INFO,
    file_log_threshold=logging.DEBUG,
    log_file_path=LOG_FILE_PATH,
) -> logging.Logger:
    """Init logger object for logging in demisto-sdk
        For more info - https://docs.python.org/3/library/logging.html

    Args:
        console_log_threshold(int): Minimum console log threshold. Defaults to logging.INFO
        file_log_threshold(int): Minimum console log threshold. Defaults to logging.INFO

    Returns:
        logging.Logger: logger object
    """

    global logger

    console_handler = logging.StreamHandler()
    console_handler.set_name(CONSOLE_HANDLER)
    console_handler.setLevel(
        console_log_threshold if console_log_threshold else logging.INFO
    )

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

    global current_log_file_path
    if custom_log_path := os.getenv("DEMISTO_SDK_LOG_FILE_PATH"):
        current_log_file_path = Path(custom_log_path)
    else:
        current_log_file_path = log_file_path or LOG_FILE_PATH
        if Path(current_log_file_path).is_dir():
            current_log_file_path = current_log_file_path / LOG_FILE_NAME
    file_handler = RotatingFileHandler(
        filename=current_log_file_path,
        mode="a",
        maxBytes=1048576,
        backupCount=10,
    )
    file_handler.set_name(FILE_HANDLER)
    file_handler.setLevel(file_log_threshold if file_log_threshold else logging.DEBUG)

    class NoColorFileFormatter(logging.Formatter):
        def __init__(
            self,
        ):
            super().__init__(
                fmt="[%(asctime)s] - [%(threadName)s] - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s",
                datefmt=DATE_FORMAT,
            )

        def format(self, record):
            message = logging.Formatter.format(self, record)
            message = self.replace_escapes(message)
            return message

        def replace_escapes(self, message):
            for key in escapes:
                message = message.replace(key, "")
            return message

    file_formatter = NoColorFileFormatter()
    file_handler.setFormatter(fmt=file_formatter)

    logging.basicConfig(
        handlers=[console_handler, file_handler],
        level=min(console_handler.level, file_handler.level),
    )

    root_logger: logging.Logger = logging.getLogger("")
    set_demisto_handlers_to_logger(root_logger, console_handler, file_handler)

    demisto_logger: logging.Logger = logging.getLogger("demisto-sdk")
    set_demisto_handlers_to_logger(demisto_logger, console_handler, file_handler)
    demisto_logger.propagate = False

    set_demisto_logger(demisto_logger)

    return demisto_logger


def set_demisto_handlers_to_logger(
    logger: logging.Logger, console_handler, file_handler
):
    while logger.handlers:
        logger.removeHandler(logger.handlers[0])
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.level = min(console_handler.level, file_handler.level)


def get_log_file() -> Path:
    return current_log_file_path
