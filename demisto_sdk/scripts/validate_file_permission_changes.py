import sys
from pathlib import Path
from typing import Any, Dict, List

import typer
from git import Blob

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()


def str_to_bool(s: str) -> bool:
    """
    Helper function to convert a string input to a boolean.

    Args:
    - `s` (``str``): The string to convert.

    Returns:
    - `bool` representation of a string.
    """

    return s.lower() in ("yes", "true", "t", "1")


def split_files(files_str: str) -> List[str]:
    """
    Helper function to return a `list` of `str`
    from an input string.

    Args:
    - `files_str` (``str``): The input string.

    Returns:
    - `List[str]` containing a list of strings.
    """

    return files_str.split()


@main.command(help="Validate that file modes were not changed")
def validate_changed_files_permissions(
    changed_files: List[str] = typer.Argument(
        default=None, help="The files to check, e.g. f1 f2 f3.py", callback=split_files
    ),
    ci: bool = typer.Argument(
        default=False,
        help="Whether we're running in a CI environment or not, e.g. 'true'",
        callback=str_to_bool,
    ),
) -> None:
    """
    Validate whether the file mode was modified. Exit code 0 if no files
    modes were modified, 1 otherwise.

    Args:
    - `changed_files` (``List[str]``): The files to check, e.g. 'test/f1 f2 f3.py'.
    - `ci` (``bool``): Whether we're running in a CI environment or not. Default is False.
    """

    exit_code = 0

    logging_setup()
    git_util = GitUtil.from_content_path()

    if changed_files:
        logger.debug(f"Got {changed_files:=} as input...")
    else:
        logger.info(
            f"Getting changed files from git branch '{DEMISTO_GIT_PRIMARY_BRANCH}'..."
        )
        changed_files = [
            str(path)
            for path in git_util.get_all_changed_files(DEMISTO_GIT_PRIMARY_BRANCH)
        ]

    logger.info(f"Running on {changed_files:=}...")

    if changed_files:

        logger.debug(
            f"The following changed files were found comparing '{DEMISTO_GIT_PRIMARY_BRANCH}': {', '.join(changed_files)}"
        )

        logger.debug(
            f"Iterating over {len(changed_files)} changed files to check if their permissions flags have changed..."
        )

        result: Dict[str, Any] = {}

        for changed_file in changed_files:
            result[changed_file] = git_util.has_file_permissions_changed(
                file_path=changed_file, ci=ci
            )

        for filename, (is_changed, old_permission, new_permission) in result.items():
            if is_changed:
                logger.error(
                    f"File '{filename}' permission was changed from {old_permission} to {new_permission}"
                )
                msg = get_revert_permission_message(Path(filename), new_permission)
                logger.info(msg)
                exit_code = 1

    sys.exit(exit_code)


def get_revert_permission_message(file_path: Path, new_permission: str) -> str:
    """
    Helper method that returns an output message explaining
    to the user how to revert the file permissions.

    Args:
    - `file_path` (``Path``): The path to the file.
    - `new_permission` ((`str``)): The new permission bits.

    Returns:
    - `str` with a message how to revert the permission changes.
    """

    try:
        if new_permission == oct(Blob.file_mode)[2:]:
            cmd = f"chmod +x {file_path.absolute()}'"
        elif new_permission == oct(Blob.executable_mode)[2:]:
            cmd = f"chmod -x {file_path.absolute()}'"
        else:
            cmd = f"chmod +||- {file_path.absolute()}"
        message = f"Please revert the file permissions using the command '{cmd}'"
    except IndexError as e:
        logger.warning(f"Unable to get the blob file permissions: {e}")
        message = f"Unable to get the blob file permissions for file '{file_path.absolute()}': {e}"
    finally:
        return message
