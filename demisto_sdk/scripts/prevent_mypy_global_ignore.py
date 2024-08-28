import re
from pathlib import Path
from typing import Dict, List, Union

import typer

from demisto_sdk.commands.common.logger import logger, logging_setup

MYPY_GLOBAL_IGNORE_PATTERN = re.compile(r"^#\s*type\s*:\s*ignore.*")
MYPY_DISABLE_ERROR_CODE_PATTERN = re.compile(r"^#\s*mypy:\s*disable-error-code.*")

main = typer.Typer()


def has_global_type_ignore(file_path: Path) -> Union[int, None]:
    """
    Helper function to check whether the input file
    has the global mypy ignore set.

    Args:
    - `file_path` (``Path``): The input Python file path.

    Returns:
    - `int` with the line number where the ignore comment
    was found, `None` if it wasn't found.
    """

    lines = file_path.read_text().splitlines()

    for line_num, line in enumerate(lines):
        if MYPY_GLOBAL_IGNORE_PATTERN.fullmatch(
            line
        ) or MYPY_DISABLE_ERROR_CODE_PATTERN.fullmatch(line):
            return line_num + 1

    return None


@main.command(help="Prevent the changed Python files don't specify global mypy ignore")
def prevent_mypy_global_ignore(
    changed_files: List[Path] = typer.Argument(
        default=...,
        help="The files to check, e.g. /dir/f1.py dir/f2.py f3.py",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """
    Validate whether the Python file has a global mypy type ignore set.
    Exit code 0 if global mypy type ignore is not set, 1 otherwise.

    Args:
    - `changed_files` (``List[Path]``): The files paths to check.
    """

    exit_code = 0

    logging_setup(calling_function=__name__)

    if changed_files:
        result: Dict[str, Union[int, None]] = {}

        for changed_file in changed_files:
            result[str(changed_file.absolute())] = has_global_type_ignore(changed_file)

        logger.debug(f"{result=}")

        for filename, line_number in result.items():
            if line_number:
                logger.error(
                    f"File '{filename}' in line {line_number} sets global mypy ignore. Please remove it."
                )
                exit_code = 1
    else:
        logger.info("No Python changed files supplied. Terminating...")

    raise typer.Exit(code=exit_code)
