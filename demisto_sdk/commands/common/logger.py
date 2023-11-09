import itertools
import logging
import logging.config
import os.path
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional, Union

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.tools import parse_int_or_default, string_to_bool

logger: logging.Logger = logging.getLogger("demisto-sdk")

neo4j_log = logging.getLogger("neo4j")
neo4j_log.setLevel(logging.WARNING)

CONSOLE_HANDLER = "console-handler"
FILE_HANDLER = "file-handler"

LOG_FILE_NAME: str = "demisto_sdk_debug.log"
log_file_name_notified = False

LOG_FILE_PATH: Path = CONTENT_PATH / LOG_FILE_NAME
current_log_file_path: Path = LOG_FILE_PATH

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
DEMISTO_SDK_LOG_FILE_SIZE = parse_int_or_default(
    os.getenv("DEMISTO_SDK_LOG_FILE_SIZE"), 1_048_576  # 1MB
)
DEMISTO_SDK_LOG_FILE_COUNT = parse_int_or_default(
    os.getenv("DEMISTO_SDK_LOG_FILE_COUNT"), 10
)

FILE_LOG_RECORD_FORMAT = "[%(asctime)s] - [%(threadName)s] - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s"

if os.getenv("CI"):
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


def get_handler_by_name(logger: logging.Logger, handler_name: str):
    return next(
        (
            current_handler
            for current_handler in logger.handlers
            if current_handler.get_name == handler_name
        ),
        None,
    )


def set_demisto_logger(demisto_logger: logging.Logger):
    global logger
    logger = demisto_logger


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
    log_file_path: Optional[Union[str, Path]] = LOG_FILE_PATH,
) -> logging.Logger:
    """Init logger object for logging in demisto-sdk
        For more info - https://docs.python.org/3/library/logging.html

    Args:
        console_log_threshold: Minimum console log threshold. Defaults to logging.INFO
        file_log_threshold: Minimum console log threshold. Defaults to logging.INFO
        log_file_path: Path to log file. Defaults to LOG_FILE_PATH

    Returns:
        logging.Logger: logger object
    """

    if not hasattr(logging.getLoggerClass(), "success"):
        _add_logging_level("SUCCESS", SUCCESS_LEVEL)

    global logger
    global current_log_file_path
    global log_file_name_notified

    console_handler = logging.StreamHandler()
    console_handler.set_name(CONSOLE_HANDLER)
    console_handler.setLevel(console_log_threshold or logging.INFO)

    if custom_log_path := os.getenv("DEMISTO_SDK_LOG_FILE_PATH"):
        current_log_file_path = Path(custom_log_path)
    else:
        current_log_file_path = Path(log_file_path or LOG_FILE_PATH)
        if current_log_file_path.is_dir():
            current_log_file_path = current_log_file_path / LOG_FILE_NAME
    file_handler = RotatingFileHandler(
        filename=current_log_file_path,
        mode="a",
        maxBytes=DEMISTO_SDK_LOG_FILE_SIZE,
        backupCount=DEMISTO_SDK_LOG_FILE_COUNT,
    )
    file_handler.set_name(FILE_HANDLER)
    file_handler.setLevel(file_log_threshold or logging.DEBUG)

    if string_to_bool(os.getenv("DEMISTO_SDK_LOG_NO_COLORS", "False")):
        console_handler.setFormatter(fmt=NoColorFileFormatter())
    else:
        console_handler.setFormatter(fmt=ColorConsoleFormatter())

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

    demisto_logger.debug(f"Python version: {sys.version}")
    demisto_logger.debug(f"Working dir: {os.getcwd()}")
    import platform

    demisto_logger.debug(f"Platform: {platform.system()}")

    if not log_file_name_notified:
        if string_to_bool(os.getenv("DEMISTO_SDK_LOG_NOTIFY_PATH", "True")):
            demisto_logger.info(
                f"[yellow]Log file location: {current_log_file_path}[/yellow]"
            )
        log_file_name_notified = True

    logger = demisto_logger

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
