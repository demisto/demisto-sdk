import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import typer

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup

MYPY_GLOBAL_IGNORE_PATTERN = re.compile(r"^#\s*type\s*:\s*ignore")

main = typer.Typer()


def has_global_type_ignore(file_path: Path) -> Tuple[bool, Union[int, None]]:
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

    lines = file_path.read_text().splitlines()

    for line_num, line in enumerate(lines):
        if MYPY_GLOBAL_IGNORE_PATTERN.match(line):
            return True, line_num + 1

    return False, None


@main.command(help="Validate the changed Python files don't specify global mypy ignore")
def validate_mypy_global_ignore(
    changed_files: List[Path] = typer.Argument(
        default=None,
        help="The files to check, e.g. /dir/f1.py dir/f2.py f3.py",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    ci: bool = typer.Option(envvar="CI", default=False),
) -> None:
    """
    Validate whether the Python file has a global mypy type ignore set.
    Exit code 0 if global mypy type ignore is set, 1 otherwise.

    Args:
    - `changed_files` (``List[Path]``): The files paths to check.
    - `ci` (``bool``): Whether we're in a CI environment or not.
    """

    exit_code = 0

    logging_setup()
    logger.debug(f"Running in CI environment: {ci}")

    logger.debug(f"Input {changed_files=}")

    if not changed_files:
        logger.debug(
            f"Getting changed files from git branch '{DEMISTO_GIT_PRIMARY_BRANCH}'..."
        )
        git_util = GitUtil.from_content_path()
        changed_files = [
            Path(git_util.git_path()) / Path(path)
            for path in git_util.get_all_changed_files(
                DEMISTO_GIT_PRIMARY_BRANCH, include_untracked=True
            )
        ]

    logger.debug(
        f"Iterating over '{changed_files=}' to check for global mypy type ignore..."
    )

    if changed_files:

        result: Dict[str, Any] = {}

        for changed_file in changed_files:
            result[str(changed_file.absolute())] = has_global_type_ignore(changed_file)

        logger.debug(f"{result=}")

        for filename, (has_global_ignore, line_number) in result.items():
            if has_global_ignore:
                logger.error(
                    f"File '{filename}#L{line_number}' sets global mypy ignore. Please remove."
                )
                exit_code = 1
    else:
        logger.info("No Python changed files supplied. Terminating...")

    raise typer.Exit(code=exit_code)
