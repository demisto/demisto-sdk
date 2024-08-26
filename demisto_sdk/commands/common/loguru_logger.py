import os
import platform
import sys
from pathlib import Path
from typing import Any, Iterable, Optional, Union

import loguru  # noqa: TID251 # This is the only place where we allow it

from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_LOG_FILE_PATH,
    DEMISTO_SDK_LOG_FILE_SIZE,
    DEMISTO_SDK_LOG_NO_COLORS,
    DEMISTO_SDK_LOG_NOTIFY_PATH,
    DEMISTO_SDK_LOGGING_SET,
    LOG_FILE_NAME,
    LOGS_DIR,
    STRING_TO_BOOL_MAP,
)


def string_to_bool(
    input_: Any,
    default_when_empty: Optional[bool] = None,
) -> bool:
    """Implemented here although duplicates the one under `tools`, to avoid circular imports
    Other (rejected) options to solve this were
        1) import logger in many `tools` methods (redundant logging)
        2) move string_to_bool out of tools (inconsistent)
    """
    try:
        return STRING_TO_BOOL_MAP[str(input_).lower()]
    except (KeyError, TypeError):
        if input_ in ("", None) and default_when_empty is not None:
            return default_when_empty

    raise ValueError(f"cannot convert {input_} to bool")


global logger
logger = loguru.logger  # all SDK modules should import from this file, not from loguru


def setup_neo4j_logger():
    # TODO use
    import logging

    neo4j_log = logging.getLogger("neo4j")
    neo4j_log.setLevel(logging.CRITICAL)


def calculate_log_size() -> str:
    if env_var := os.getenv(DEMISTO_SDK_LOG_FILE_SIZE):
        try:
            return f"{int(env_var)} B"

        except (TypeError, ValueError):
            logger.warning(
                f"Invalid value for DEMISTO_SDK_LOG_FILE_SIZE environment variable: {env_var}. Using default value of '1MB'."
            )
    return "1 MB"


def calculate_rentation() -> int:
    if env_var := os.getenv("DEMISTO_SDK_LOG_FILE_COUNT"):
        try:
            return int(env_var)
        except (TypeError, ValueError):
            logger.warning(
                f"Invalid value for DEMISTO_SDK_LOG_FILE_COUNT environment variable: {env_var}. Using default value of '10'."
            )
    return 10


def calculate_log_dir(
    path_input: Optional[Union[Path, str]], logger: "loguru.Logger"
) -> Path:  # TODO use file name?
    if raw_path := path_input or os.getenv(DEMISTO_SDK_LOG_FILE_PATH):
        path = Path(raw_path).resolve()
        if path.exists():
            if path.is_dir():
                return path

            if path.is_file():
                logger.warning(
                    f"Log file path '{path}' is a file.\n Logs will be saved in its containing folder"
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


def setup_logger_colors(logger: "loguru.Logger"):
    logger.level("DEBUG", color="<fg #D3D3D3>")
    logger.level("INFO", color="<fg #D3D3D3>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<red><bold>")
    logger.level("SUCCESS", color="<green>")


def logging_setup(
    console_log_threshold: str = "INFO",
    file_log_threshold: str = "DEBUG",
    log_file_path: Optional[Union[Path, str]] = None,
    initial: bool = False,
    **kwargs,  # TODO remove skip_log_file_creation
):
    """
    The initial set up is required since we have code (e.g. get_content_path) that runs in __main__ before the typer/click commands set up the logger.
    In the initial set up there is NO file logging (only console)
    """
    global logger

    logger = loguru.logger
    setup_logger_colors(logger)
    logger.info(
        f"{console_log_threshold=},{file_log_threshold=},{log_file_path=},{initial=}"
    )  # TODO remove
    logger.warning("logging_setup called", color="blue")  # TODO remove
    logger.remove()  # Removes all pre-existing handlers

    colorize = string_to_bool(os.getenv(DEMISTO_SDK_LOG_NO_COLORS), True)
    logger = logger.opt(colors=colorize)  # allows using color tags in all logs
    logger.add(
        sys.stdout,
        colorize=colorize,
        backtrace=True,  # TODO
        level=console_log_threshold,
    )
    if os.getenv(DEMISTO_SDK_LOGGING_SET):
        logger.warning("This isn't the first time logging_setup has been called")
    if not initial:
        log_path = calculate_log_dir(log_file_path, logger) / LOG_FILE_NAME
        logger.add(  # file handler
            log_path,
            rotation=calculate_log_size(),
            retention=calculate_rentation(),
            colorize=False,
            # backtrace=True,  # TODO
            level=file_log_threshold,
        )
        if string_to_bool(os.getenv(DEMISTO_SDK_LOG_NOTIFY_PATH), True):
            logger.info(f"<yellow>Log file location: {log_path}</yellow>")

        logger.debug(f"Platform: {platform.system()}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Working directory: {Path.cwd()}")
        os.environ[DEMISTO_SDK_LOGGING_SET] = "true"
        logger.success("logging_setup finished")  # TODO remove


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


def handle_deprecated_args(input_args: Iterable[str], logger: "loguru.Logger"):
    for current_arg in sorted(
        set(input_args).intersection(DEPRECATED_PARAMETERS.keys())
    ):
        logger.error(
            f"<red>Argument {current_arg} is deprecated. Please use {DEPRECATED_PARAMETERS[current_arg]} instead.</red>"
        )
