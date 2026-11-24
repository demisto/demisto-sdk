from pathlib import Path
from typing import Optional

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.xsoar_linter.xsoar_linter import (
    DEFAULT_ENGINE,
    ENGINE_ENV_VAR,
    ENGINES,
    xsoar_linter_manager,
)


@logging_setup_decorator
def xsoar_linter(
    ctx: typer.Context,
    file_paths: Optional[list[Path]] = typer.Argument(
        None,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help="The paths to run xsoar linter on. May pass multiple paths.",
    ),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help="Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.",
    ),
    file_log_threshold: str = typer.Option(
        None, "--file-log-threshold", help="Minimum logging threshold for file output."
    ),
    log_file_path: str = typer.Option(
        None, "--log-file-path", help="Path to save log files."
    ),
    engine: str = typer.Option(
        DEFAULT_ENGINE,
        "--engine",
        envvar=ENGINE_ENV_VAR,
        help=f"The linter engine to use: {' or '.join(ENGINES)}. "
        f"Can also be set with the {ENGINE_ENV_VAR} environment variable.",
    ),
):
    """
    Runs the xsoar lint on the given paths.
    """
    return_code = xsoar_linter_manager(file_paths, engine=engine)
    if return_code:
        raise typer.Exit(1)
