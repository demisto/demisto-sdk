import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import typer

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.scripts.scripts_common import (
    HELP_CHANGED_FILES,
    is_ci,
    split_files,
)

MYPY_GLOBAL_IGNORE_PATTERN = re.compile(r"^#\s*type\s*:\s*ignore")

main = typer.Typer()


def get_py_files(input_files: List[str]) -> List[str]:
    """
    Helper function to filter a `list` of file `str`
    to return a list of Python files.

    Args:
    - `input_files` (``List[str]``): The input files.

    Returns
    - `List[str]` containing a list of strings of Python files.
    """

    python_files = [file for file in input_files if file.endswith(".py")]

    return python_files


def has_global_type_ignore(file_path_str: str) -> Tuple[bool, Union[int, None]]:
    """
    Helper function to check whether the input file
    has the global mypy ignore set.

    Args:
    - `file_path_str` (``str``): The input Python file.

    Returns:
    - `True` if the file is globally ignored, `False`
    otherwise.
    - `int` with the line number where the ignore comment
    was found, `None` if it wasn't found.
    """

    file_path = Path(file_path_str)

    if not file_path.exists():
        logger.error(f"File '{file_path}' doesn't exist")
        raise typer.Exit(1)

    lines = file_path.read_text().splitlines()

    for line_num, line in enumerate(lines):
        if MYPY_GLOBAL_IGNORE_PATTERN.match(line):
            return True, line_num + 1

    return False, None


@main.command(help="Validate the changed Python files don't specify global mypy ignore")
def validate_mypy_global_ignore(
    changed_files: List[str] = typer.Argument(
        default=None, help=HELP_CHANGED_FILES, callback=split_files
    )
) -> None:
    """
    Validate whether the Python file has a global mypy type ignore set.
    Exit code 0 if global mypy type ignore is set, 1 otherwise.

    Args:
    - `changed_files` (``List[str]``): The files to check, e.g. 'test/f1.py f2.py f3.py'.
    """

    exit_code = 0

    logging_setup()
    git_util = GitUtil.from_content_path()

    ci = is_ci()

    logger.debug(f"Running in CI environment: {ci}")

    if changed_files:
        logger.debug(f"Got {','.join(changed_files)} as input...")
    else:
        logger.debug(
            f"Getting changed files from git branch '{DEMISTO_GIT_PRIMARY_BRANCH}'..."
        )
        changed_files = [
            str(path)
            for path in git_util.get_all_changed_files(DEMISTO_GIT_PRIMARY_BRANCH)
        ]

    py_files = get_py_files(changed_files)
    if py_files:

        logger.debug(
            f"Iterating over {len(py_files)} ({''.join(py_files)}) Python changed files to check if they have global mypy ignore comments..."
        )

        result: Dict[str, Any] = {}

        for changed_file in changed_files:
            result[changed_file] = has_global_type_ignore(changed_file)

        for filename, (has_global_ignore, line_number) in result.items():
            if has_global_ignore:
                logger.error(
                    f"File '{filename}#L{line_number}' sets global mypy ignore. Please remove."
                )
                exit_code = 1
    else:
        logger.info("No Python changed files supplied. Terminating...")

    raise typer.Exit(code=exit_code)
