import itertools
import logging
import logging.config
import os.path
import platform
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional, Union

# NOTE: Do not add internal imports here, as it may cause circular imports.
from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_LOG_FILE_COUNT,
    DEMISTO_SDK_LOG_FILE_PATH,
    DEMISTO_SDK_LOG_FILE_SIZE,
    DEMISTO_SDK_LOG_NO_COLORS,
    DEMISTO_SDK_LOG_NOTIFY_PATH,
    LOG_FILE_NAME,
    LOGS_DIR,
    STRING_TO_BOOL_MAP,
)

logger: logging.Logger = logging.getLogger("demisto-sdk")


def environment_variable_to_bool(
    variable_name: str, default_value: bool = False
) -> bool:
    """
    Check if the environment variable is set and is a valid boolean value.
    If it is not set or is not a valid boolean value, return the default value.

    Args:
        variable_name (str): The name of the environment variable.
        default_value (bool): A default value to return if the environment variable is not set or is invalid.

    Returns:
        bool: The environment variable value if it is set and is a valid boolean value, otherwise the default value.
    """
    env_var = os.getenv(variable_name)

    if not env_var:
        return default_value

    if isinstance(env_var, str) and env_var.casefold() in STRING_TO_BOOL_MAP:
        return STRING_TO_BOOL_MAP[env_var.casefold()]

    else:
        logger.warning(
            f"'{variable_name}' environment variable is set to '{env_var}', "
            f"which is not a valid value. Default value '{default_value}' will be used."
        )
        return default_value


def environment_variable_to_int(variable_name: str, default_value: int) -> int:
    """
    Check if the environment variable is set and is a valid integer value.
    If it is not set or is not a valid integer value, return the default value.

    Args:
        variable_name (str): The name of the environment variable.
        default_value (int): A default value to return if the environment variable is not set or is invalid.

    Returns:
        int: The environment variable value if it is set and is a valid integer value, otherwise the default value.
    """
    env_var = os.getenv(variable_name)

    if not env_var:
        return default_value

    try:
        return int(env_var)

    except ValueError:
        logger.warning(
            f"'{variable_name}' environment variable is set to '{env_var}', "
            f"which is not a valid integer value. Default value '{default_value}' will be used."
        )

        return default_value


neo4j_log = logging.getLogger("neo4j")
neo4j_log.setLevel(logging.CRITICAL)

CONSOLE_HANDLER = "console-handler"
FILE_HANDLER = "file-handler"

LOG_FILE_PATH: Optional[Path] = None
LOG_FILE_PATH_PRINT = environment_variable_to_bool(
    DEMISTO_SDK_LOG_NOTIFY_PATH, default_value=True
)

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

DEPRECATED_PARAMETERS = {
    "-v": "--console-log-threshold or --file-log-threshold",
    "-vv": "--console-log-threshold or --file-log-threshold",
    "-vvv": "--console-log-threshold or --file-log-threshold",
    "--verbose": "--console-log-threshold or --file-log-threshold",
    "-q": "--console-log-threshold or --file-log-threshold",
    "--quiet": "--console-log-threshold or --file-log-threshold",
    "--console_log_threshold": "--console-log-threshold",
    "--file_log_threshold": "--file-log-threshold",
    "-ln": "--log-file-path",
    "--log-name": "--log-file-path",
    "--log_file_path": "--log-file-path",
    "no_logging": "--console-log-threshold or --file-log-threshold",
}

SUCCESS_LEVEL: int = 25
LOG_FILE_SIZE = environment_variable_to_int(DEMISTO_SDK_LOG_FILE_SIZE, 1_048_576)  # 1MB
LOG_FILE_COUNT = environment_variable_to_int(DEMISTO_SDK_LOG_FILE_COUNT, 10)

FILE_LOG_RECORD_FORMAT = "[%(asctime)s] - [%(threadName)s] - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s"

if environment_variable_to_bool("CI"):
    CONSOLE_LOG_RECORD_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
    CONSOLE_LOG_RECORD_FORMAT_SHORT = "[%(asctime)s] [%(levelname)s] "
else:
    CONSOLE_LOG_RECORD_FORMAT = "[%(levelname)s] %(message)s"
    CONSOLE_LOG_RECORD_FORMAT_SHORT = "[%(levelname)s] "


CONSOLE_RECORD_FORMATS = {
    logging.DEBUG: "[lightgrey]%(message)s[/lightgrey]",
    logging.INFO: "[lightgrey]%(message)s[/lightgrey]",
    logging.WARNING: "[yellow]%(message)s[/yellow]",
    logging.ERROR: "[red]%(message)s[/red]",
    logging.CRITICAL: "[red][bold]%(message)s[/bold[/red]",
    SUCCESS_LEVEL: "[green]%(message)s[/green]",
}

NO_COLOR_ESCAPE_CHAR = "\033[0m"

DEMISTO_LOG_ALLOWED_ESCAPES = [  # The order of the list is by priority.
    ("green", 32),
    ("red", 91),
    ("yellow", 93),
    ("cyan", 36),
    ("blue", 34),
    ("orange", 33),
    ("pink", 95),
    ("purple", 35),
    ("black", 30),
    ("invisible", 8),
    ("bold", 1),
    ("disable", 2),
    ("reverse", 7),
    ("strikethrough", 9),
    ("underline", 4),
    ("darkgrey", 90),
    ("darkred", 31),
    ("lightblue", 94),
    ("lightcyan", 96),
    ("lightgreen", 92),
    ("lightgrey", 37),
    ("lightred", 91),
]

DEMISTO_LOG_LOOKUP = dict(  # Convert the list of tuples to a dict
    itertools.chain.from_iterable(  # flatten the list of lists
        map(
            lambda color_to_number: [
                (
                    f"[{color_to_number[0]}]",  # The color key (i.e. [green])
                    f"\033[{color_to_number[1]:>02}m",  # The color escape sequence (i.e. \033[32m)
                ),
                (
                    f"[/{color_to_number[0]}]",  # The color closing key (i.e. [/green])
                    NO_COLOR_ESCAPE_CHAR,  # The color closing escape sequence (i.e. \033[0m)
                ),
            ],
            DEMISTO_LOG_ALLOWED_ESCAPES,
        )
    )
)

DEMISTO_LOGGER_PATTERN = re.compile(
    "|".join(rf"\[(\/)?{key}\]" for key, _ in DEMISTO_LOG_ALLOWED_ESCAPES)
)


def replace_log_coloring_tags(
    text: str, replacements: Optional[Dict[str, str]] = None
) -> str:
    result: List[str] = []
    last_index = 0
    replacements = replacements if replacements is not None else DEMISTO_LOG_LOOKUP

    for match in DEMISTO_LOGGER_PATTERN.finditer(text):
        start, end = match.span()
        result.extend((text[last_index:start], replacements.get(match.group(), "")))
        last_index = end

    result.append(text[last_index:])
    return "".join(result)


def handle_deprecated_args(input_args):
    for current_arg in input_args:
        if current_arg in DEPRECATED_PARAMETERS.keys():
            substitute = DEPRECATED_PARAMETERS[current_arg]
            logging.getLogger("demisto-sdk").error(
                f"[red]Argument {current_arg} is deprecated. Please use {substitute} instead.[/red]"
            )


def get_handler_by_name(_logger: logging.Logger, handler_name: str):
    return next(
        (
            current_handler
            for current_handler in _logger.handlers
            if current_handler.get_name == handler_name
        ),
        None,
    )


def _add_logging_level(
    level_name: str, level_num: int, method_name: str = None
) -> None:
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.
    `level_name` becomes an attribute of the `logging` module with the value
    `level_num`. `method_name` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `method_name` is not specified, `level_name.lower()` is
    used.
    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present
    Example
    -------
    >>> _add_logging_level('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5
    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError(f"{level_name} already defined in logging module")
    if hasattr(logging, method_name):
        raise AttributeError(f"{method_name} already defined in logging module")
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(f"{method_name} already defined in logger class")

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


class ColorConsoleFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: Optional[str] = CONSOLE_LOG_RECORD_FORMAT,
        datefmt: Optional[str] = DATE_FORMAT,
        short_fmt: Optional[str] = CONSOLE_LOG_RECORD_FORMAT_SHORT,
        record_formats: Optional[Dict[int, str]] = None,
    ):
        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
        )
        self.short_fmt = short_fmt or CONSOLE_LOG_RECORD_FORMAT_SHORT
        self.record_formats = record_formats or CONSOLE_RECORD_FORMATS

    @staticmethod
    def _record_contains_escapes(record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return any(
            not key.startswith("[/]") and key in message for key in DEMISTO_LOG_LOOKUP
        )

    @staticmethod
    def _string_starts_with_escapes(string: str) -> bool:
        message = string.strip()
        return message.startswith("[")

    @staticmethod
    def _record_starts_with_escapes(record: logging.LogRecord) -> bool:
        message = record.getMessage().strip()
        return message.startswith("[")

    @staticmethod
    def _get_start_escapes(record: logging.LogRecord) -> str:
        ret_value = ""

        current_message = record.getMessage()
        while ColorConsoleFormatter._string_starts_with_escapes(current_message):

            # Record starts with escapes - Extract them
            current_escape = current_message[: current_message.find("]") + 1]
            ret_value += current_escape
            current_message = current_message[
                len(current_escape) : current_message.find("]", len(current_escape)) + 1
            ]

        return ret_value

    @staticmethod
    def _insert_into_escapes(record: logging.LogRecord, string: str) -> str:
        if not ColorConsoleFormatter._record_starts_with_escapes(record):
            return string + record.getMessage()

        # Need to "insert" the string into the escapes
        start_escapes = ColorConsoleFormatter._get_start_escapes(record)
        return start_escapes + string + record.getMessage()[len(start_escapes) :]

    def format(self, record):
        if ColorConsoleFormatter._record_contains_escapes(record):
            message = ColorConsoleFormatter._insert_into_escapes(
                record,
                self.short_fmt,
            )
            message = logging.Formatter(message).format(record)
        else:
            log_fmt = self.record_formats.get(record.levelno)
            message = logging.Formatter(log_fmt).format(record)
        message = replace_log_coloring_tags(message)
        return message


class NoColorFileFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: Optional[str] = FILE_LOG_RECORD_FORMAT,
        datefmt: Optional[str] = DATE_FORMAT,
    ):
        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
        )

    def format(self, record):
        message = logging.Formatter.format(self, record)
        message = replace_log_coloring_tags(
            message, {}
        )  # Remove all coloring tags, with supplying empty dict.
        return message


def logging_setup(
    console_log_threshold: Union[int, str] = logging.INFO,
    file_log_threshold: Union[int, str] = logging.DEBUG,
    log_file_path: Optional[Union[str, Path]] = None,
    skip_log_file_creation: bool = False,
) -> logging.Logger:
    """
    Initialize and configure the logger object for logging in demisto-sdk
    For more info - https://docs.python.org/3/library/logging.html

    Args:
        console_log_threshold (int | str, optional): Minimum console log threshold. Defaults to logging.INFO.
        file_log_threshold(int | str, optional): Minimum console log threshold. Defaults to logging.DEBUG.
        log_file_path (str | Path | None, optional): Path to log file. Defaults to None.
        skip_log_file_creation (bool, optional): Whether to skip log file creation. Defaults to False.

    Returns:
        logging.Logger: logger object
    """
    global LOG_FILE_PATH

    if not hasattr(logging.getLoggerClass(), "success"):
        _add_logging_level("SUCCESS", SUCCESS_LEVEL)

    console_handler = logging.StreamHandler()
    console_handler.set_name(CONSOLE_HANDLER)
    console_handler.setLevel(console_log_threshold or logging.INFO)

    if environment_variable_to_bool(DEMISTO_SDK_LOG_NO_COLORS):
        console_handler.setFormatter(fmt=NoColorFileFormatter())
    else:
        console_handler.setFormatter(fmt=ColorConsoleFormatter())

    log_handlers: List[logging.Handler] = [console_handler]

    # We set up the console handler separately before the file logger is ready, so that we can display log messages
    root_logger: logging.Logger = logging.getLogger("")
    set_demisto_handlers_to_logger(_logger=root_logger, handlers=log_handlers)
    set_demisto_handlers_to_logger(_logger=logger, handlers=log_handlers)
    logger.propagate = False

    if not skip_log_file_creation:
        if log_file_directory_path_str := (
            log_file_path or os.getenv(DEMISTO_SDK_LOG_FILE_PATH)
        ):
            current_log_file_path = Path(log_file_directory_path_str).resolve()

            if current_log_file_path.is_dir():
                final_log_file_path = current_log_file_path / LOG_FILE_NAME

            elif current_log_file_path.is_file():
                logger.warning(
                    f"Log file path '{current_log_file_path}' is a file and not a directory. "
                    f"Log file will be created in parent directory '{current_log_file_path.parent}'."
                )
                final_log_file_path = current_log_file_path.parent / LOG_FILE_NAME

            else:  # Path is neither a file nor a directory
                logger.warning(
                    f"Log file path '{current_log_file_path}' does not exist and will be created."
                )
                current_log_file_path.mkdir(parents=True, exist_ok=True)
                final_log_file_path = current_log_file_path / LOG_FILE_NAME

        else:  # Use default log files path
            log_file_directory_path = LOGS_DIR
            log_file_directory_path.mkdir(
                parents=True, exist_ok=True
            )  # Generate directory if it doesn't exist
            final_log_file_path = log_file_directory_path / LOG_FILE_NAME

        # Update global variable
        LOG_FILE_PATH = final_log_file_path

        file_handler = RotatingFileHandler(
            filename=LOG_FILE_PATH,
            mode="a",
            maxBytes=LOG_FILE_SIZE,
            backupCount=LOG_FILE_COUNT,
        )
        file_handler.set_name(FILE_HANDLER)
        file_handler.setLevel(file_log_threshold or logging.DEBUG)
        file_handler.setFormatter(fmt=NoColorFileFormatter())
        log_handlers.append(file_handler)

    log_level = (
        min(*[handler.level for handler in log_handlers])
        if len(log_handlers) > 1
        else log_handlers[0].level
    )
    logging.basicConfig(
        handlers=log_handlers,
        level=log_level,
    )

    # Set up handlers again, this time with the file handler
    set_demisto_handlers_to_logger(_logger=root_logger, handlers=log_handlers)
    set_demisto_handlers_to_logger(_logger=logger, handlers=log_handlers)

    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Working dir: {Path.cwd()}")
    logger.debug(f"Platform: {platform.system()}")

    if LOG_FILE_PATH_PRINT and not skip_log_file_creation:
        logger.info(f"[yellow]Log file location: {LOG_FILE_PATH}[/yellow]")

    return logger


def set_demisto_handlers_to_logger(
    _logger: logging.Logger, handlers: List[logging.Handler]
):
    if not handlers:
        return

    while _logger.handlers:
        _logger.removeHandler(_logger.handlers[0])

    for handler in handlers:
        _logger.addHandler(handler)

    log_level = (
        min(*[handler.level for handler in handlers])
        if len(handlers) > 1
        else handlers[0].level
    )
    _logger.level = log_level
