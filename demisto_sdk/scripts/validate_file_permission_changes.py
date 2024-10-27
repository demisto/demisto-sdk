import os
import stat
from typing import Dict, List

import typer

from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()

HELP_CHANGED_FILES = "The files to check, e.g. dir/f1 f2 f3.py"


def is_executable(file_path: str) -> bool:
    """
    Checks whether a file has executable bits set or not.

    Arguments:
    - `file_path` (``str``): The file path to check.

    Returns:
    - `True` if the file has executable bits set, `False` otherwise.
    """

    # Retrieve the file's status
    file_stat = os.stat(file_path)

    # Check if the file is executable by owner, group, or others
    is_owner_executable = file_stat.st_mode & stat.S_IXUSR
    is_group_executable = file_stat.st_mode & stat.S_IXGRP
    is_other_executable = file_stat.st_mode & stat.S_IXOTH

    if is_owner_executable or is_group_executable or is_other_executable:
        return True
    else:
        return False


@main.command(help="Validate that file modes were not changed")
def validate_changed_files_permissions(
    changed_files: List[str] = typer.Argument(
        default=...,
        help=HELP_CHANGED_FILES,
        file_okay=True,
        exists=True,
        dir_okay=False,
    ),
) -> None:
    """
    Validate whether the file mode was modified. Exit code 0 if no files
    modes were modified, 1 otherwise.

    Args:
    - `changed_files` (``List[str]``): The files to check, e.g. 'test/f1 f2 f3.py'.
    """

    exit_code = 0

    logging_setup(calling_function=__name__)

    if changed_files:
        logger.debug(
            f"Iterating over {len(changed_files)} changed files to check if their permissions flags have changed..."
        )

        result: Dict[str, bool] = {}

        for changed_file in changed_files:
            result[changed_file] = is_executable(changed_file)

        for filename, executable in result.items():
            if executable:
                logger.error(
                    f"File '{filename}' has executable bits set. Please revert using command 'chmod -x {filename}'"
                )
                exit_code = 1

    raise typer.Exit(code=exit_code)
