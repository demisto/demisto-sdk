import functools
import logging  # noqa: TID251 # Required for propagation handling.
import os
import platform
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional, Union

import loguru  # noqa: TID251 # This is the only place where we allow it
import typer

from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_LOG_FILE_PATH,
    DEMISTO_SDK_LOG_FILE_SIZE,
    DEMISTO_SDK_LOG_NO_COLORS,
    DEMISTO_SDK_LOG_NOTIFY_PATH,
    DEMISTO_SDK_LOGGING_SET,
    LOG_FILE_NAME,
    LOGS_DIR,
)
from demisto_sdk.commands.common.string_to_bool import (
    string_to_bool,  # See the comment in string_to_bool's implementation
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message} @ {file}:{line} (function)"
)
CONSOLE_FORMAT = "{message}"

DEFAULT_FILE_THRESHOLD = "DEBUG"
DEFAULT_CONSOLE_THRESHOLD = "INFO"

DEFAULT_FILE_SIZE = 1 * (1024**2)  # 1 MB
DEFAULT_FILE_COUNT = 10

LOGURU_DIAGNOSE = "LOGURU_DIAGNOSE"

logger = loguru.logger  # all SDK modules should import from this file, not from loguru
logger.disable(None)  # enabled at setup_logging()


class PropagateHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        logging.getLogger(record.name).handle(record)


def _setup_neo4j_logger():
    import logging  # noqa: TID251 # special case, to control the neo4j logging

    neo4j_log = logging.getLogger("neo4j")
    neo4j_log.setLevel(logging.CRITICAL)


def calculate_log_size() -> int:
    if env_var := os.getenv(DEMISTO_SDK_LOG_FILE_SIZE):
        try:
            return int(env_var)

        except (TypeError, ValueError):
            logger.warning(
                f"non-integer log-size value ({env_var}). Defaulting to {DEFAULT_FILE_SIZE}B."
            )
    return DEFAULT_FILE_SIZE


def calculate_rentation() -> int:
    if env_var := os.getenv("DEMISTO_SDK_LOG_FILE_COUNT"):
        try:
            return int(env_var)
        except (TypeError, ValueError):
            logger.warning(
                f"non-integer value for the log file count ({env_var}). Defaulting to {DEFAULT_FILE_COUNT}"
            )
    return DEFAULT_FILE_COUNT


def calculate_log_dir(path_input: Optional[Union[Path, str]]) -> Path:
    if raw_path := path_input or os.getenv(DEMISTO_SDK_LOG_FILE_PATH):
        path = Path(raw_path).resolve()
        if path.exists():
            if path.is_dir():
                return path

            if path.is_file():
                logger.warning(
                    f"Log file path '{path}' is a file. Logs will be saved in its containing folder ({path.parent.name})"
                )
                return path.parent
            raise ValueError(
                f"path {path} is neither a valid directory nor a valid file path"
            )
        else:  # does not exist, assume it's a directory
            path.mkdir(parents=True)
            return path
    else:
        return LOGS_DIR


def logging_setup(
    calling_function: str,
    console_threshold: str = DEFAULT_CONSOLE_THRESHOLD,
    file_threshold: str = DEFAULT_FILE_THRESHOLD,
    path: Optional[Union[Path, str]] = None,
    initial: bool = False,
    propagate: bool = False,
):
    """
    The initial set up is required since we have code (e.g. get_content_path) that runs in __main__ before the typer/click commands set up the logger.
    In the initial set up there is NO file logging (only console).

    Parameters:
    - calling_function (str): The name of the function invoking the logger setup, included in all logs.
    - console_threshold (str): Log level for console output.
    - file_threshold (str): Log level for file output.
    - path (Union[Path, str], optional): Path for file logs. If None, defaults to the calculated log directory.
    - initial (bool): Indicates if the setup is for the initial configuration (console-only if True).
    - propagate (bool): If True, propagates logs to Python's logging system.

    """
    global logger
    _setup_neo4j_logger()

    logger.remove()  # Removes all pre-existing handlers

    diagnose = string_to_bool(os.getenv(LOGURU_DIAGNOSE, "False"))
    colorize = not string_to_bool(os.getenv(DEMISTO_SDK_LOG_NO_COLORS, "False"))

    if propagate:
        _propagate_logger(console_threshold)
    else:
        logger = logger.opt(
            colors=colorize
        )  # allows using color tags in logs (e.g. logger.info("<blue>foo</blue>"))
        _add_console_logger(
            colorize=colorize, threshold=console_threshold, diagnose=diagnose
        )
        if not initial:
            _add_file_logger(
                log_path=calculate_log_dir(path) / LOG_FILE_NAME,
                threshold=file_threshold,
                diagnose=diagnose,
            )
        os.environ[DEMISTO_SDK_LOGGING_SET] = "true"
    logger.debug(
        f"logger setup: {calling_function=},{console_threshold=},{file_threshold=},{path=},{initial=}"
    )


def _propagate_logger(
    threshold: Optional[str],
):
    """
    Adds a PropagateHandler to Loguru's logger to forward logs to Python's logging system.
    """
    logger.add(
        PropagateHandler(),
        format=CONSOLE_FORMAT,
        level=(threshold or DEFAULT_CONSOLE_THRESHOLD),
    )


def _add_file_logger(log_path: Path, threshold: Optional[str], diagnose: bool):
    logger.add(
        log_path,
        format=FILE_FORMAT,
        rotation=calculate_log_size(),
        retention=calculate_rentation(),
        colorize=False,
        diagnose=diagnose,
        level=(threshold or DEFAULT_FILE_THRESHOLD),
    )
    if string_to_bool(os.getenv(DEMISTO_SDK_LOG_NOTIFY_PATH), False) and (
        not os.environ.get(DEMISTO_SDK_LOGGING_SET)
    ):
        logger.info(f"<dim>Log file location: {log_path}</dim>")


def _add_console_logger(colorize: bool, threshold: Optional[str], diagnose: bool):
    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        colorize=colorize,
        diagnose=diagnose,
        level=(threshold or DEFAULT_CONSOLE_THRESHOLD),
    )


def log_system_details():
    logger.debug(f"Platform: {platform.system()}")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Working directory: {Path.cwd()}")


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


def handle_deprecated_args(input_args: Iterable[str]):
    for argument in sorted(set(input_args).intersection(DEPRECATED_PARAMETERS.keys())):
        logger.error(
            f"Argument {argument} is deprecated,"
            f"Use {DEPRECATED_PARAMETERS[argument]} instead."
        )


def logging_setup_decorator(func: Callable):
    @functools.wraps(func)
    def wrapper(ctx: typer.Context, *args, **kwargs):
        # Fetch the parameters directly from context to apply default values if they are None
        console_threshold = ctx.params.get("console_log_threshold") or "INFO"
        file_threshold = ctx.params.get("file_log_threshold") or "DEBUG"

        # Validate the logging levels
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if console_threshold not in valid_levels:
            console_threshold = "INFO"
        if file_threshold not in valid_levels:
            file_threshold = "DEBUG"

        # Set back the validated and default values in both `ctx.params` and `kwargs`
        ctx.params["console_log_threshold"] = console_threshold
        ctx.params["file_log_threshold"] = file_threshold
        kwargs["console_log_threshold"] = console_threshold
        kwargs["file_log_threshold"] = file_threshold

        # Initialize logging with the validated thresholds
        logging_setup(
            console_threshold=console_threshold,
            file_threshold=file_threshold,
            path=kwargs.get("log_file_path", None),
            calling_function=func.__name__,
        )

        # Handle deprecated arguments directly from context args if needed
        handle_deprecated_args(ctx.args if ctx else [])

        # Run the wrapped function
        return func(ctx, *args, **kwargs)

    return wrapper
