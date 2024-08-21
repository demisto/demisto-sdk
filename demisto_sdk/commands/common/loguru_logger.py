import os
import platform
import sys
from pathlib import Path
from typing import Optional, Union

from loguru import logger

from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_LOG_FILE_PATH,
    DEMISTO_SDK_LOG_FILE_SIZE,
    DEMISTO_SDK_LOG_NO_COLORS,
    DEMISTO_SDK_LOG_NOTIFY_PATH,
    LOGS_DIR,
)
from demisto_sdk.commands.common.tools import string_to_bool


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


LOG_FILE_NAME = "demisto_sdk_debug.log"


def calculate_log_dir(
    path_input: Optional[Union[Path, str]],
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


def setup_logger_colors():
    logger.info("Setting up loguru colors")  # TODO remove

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
    **kwargs,  # TODO remove skip_log_file_creation
) -> None:
    setup_logger_colors()
    logger.warning("logging_setup called")  # TODO remove

    if string_to_bool(os.getenv("DEMISTO_SDK_LOGGING_SET"), False):
        logger.warning("Skipping logging setup as it has already been performed")
        return

    logger.remove()  # Removes all handlers
    logger.add(
        sys.stdout,
        colorize=string_to_bool(os.getenv(DEMISTO_SDK_LOG_NO_COLORS), True),
        backtrace=True,  # TODO
        level=console_log_threshold,
    )

    log_path = calculate_log_dir(log_file_path) / LOG_FILE_NAME
    logger.add(  # file handler
        log_path,
        rotation=calculate_log_size(),
        retention=calculate_rentation(),
        colorize=False,
        # backtrace=True,  # TODO
        level=file_log_threshold,
    )
    if string_to_bool(os.getenv(DEMISTO_SDK_LOG_NOTIFY_PATH), True):
        logger.info(f"[yellow]Log file location: {log_path}[/yellow]")

    logger.debug(f"Platform: {platform.system()}")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Working directory: {Path.cwd()}")
    os.environ["DEMISTO_SDK_LOGGING_SET"] = "true"
    logger.success("logging_setup finished")  # TODO remove
