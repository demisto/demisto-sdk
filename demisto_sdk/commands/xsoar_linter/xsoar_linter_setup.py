from pathlib import Path
from typing import Optional

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.xsoar_linter.xsoar_linter import xsoar_linter_manager


@logging_setup_decorator
def xsoar_linter(
    file_paths: Optional[list[Path]] = typer.Argument(
        None,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help="The paths to run xsoar linter on. May pass multiple paths.",
    ),
):
    """
    Runs the xsoar lint on the given paths.
    """
    return_code = xsoar_linter_manager(
        file_paths,
    )
    if return_code:
        raise typer.Exit(1)
