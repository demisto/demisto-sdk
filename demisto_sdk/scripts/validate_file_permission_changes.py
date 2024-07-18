import subprocess
from typing import List

import typer

from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()

HELP_CHANGED_FILES = "The files to check, e.g. dir/f1 f2 f3.py"


def are_files_executable(file_paths: List[str]) -> List[str]:
    """
    Checks whether files have executable bits set or not using `ls -l`.

    Arguments:
    - `file_paths` (``List[str]``): The file paths to check.

    Returns:
    - List of files that have executable bits set.
    """

    # Run the `ls -l` command and capture its output
    result = subprocess.run(["ls", "-l"] + file_paths, capture_output=True, text=True)

    # List to store files with executable permissions
    executable_files = []

    # Iterate over the output lines
    for line in result.stdout.strip().split("\n"):
        # Extract the permission string and the file name
        parts = line.split(maxsplit=8)
        if len(parts) > 8:  # Ensure that the line contains enough parts
            permissions = parts[0]
            file_name = parts[8]

            # permissions[3], permissions[6], and permissions[9] correspond to
            # executable bits for owner, group, and others respectively
            if "x" in permissions[3:10:3]:
                executable_files.append(file_name)

    return executable_files


@main.command(help="Validate that file modes were not changed")
def validate_changed_files_permissions(
    changed_files: List[str] = typer.Argument(
        default=...,
        help=HELP_CHANGED_FILES,
        file_okay=True,
        exists=True,
        dir_okay=False,
    )
) -> None:
    """
    Validate whether the file mode was modified. Exit code 0 if no files
    modes were modified, 1 otherwise.

    Args:
    - `changed_files` (``List[str]``): The files to check, e.g. 'test/f1 f2 f3.py'.
    """

    exit_code = 0

    logging_setup()

    if changed_files:

        logger.debug(
            f"Checking permissions for {len(changed_files)} changed files using `ls -l`..."
        )

        # Get the list of files with executable bits set
        executable_files = are_files_executable(changed_files)

        if executable_files:
            exit_code = 1
            for file in executable_files:
                logger.error(
                    f"File '{file}' has executable bits set. Please revert using command 'chmod -x {file}'"
                )

    raise typer.Exit(code=exit_code)
