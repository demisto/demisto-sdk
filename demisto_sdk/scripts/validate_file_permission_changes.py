import os
from pathlib import Path
from typing import Any, Dict, List, Union

import typer
from git import Blob

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()

HELP_CHANGED_FILES = "The files to check, e.g. dir/f1 f2 f3.py"
ERROR_IS_CI_INVALID = (
    "Invalid value for CI env var. Expected 'true' or 'false', actual '{env_var_str}'"
)
ERROR_INPUT_FILES_INVALID = "Invalid value for input files: {input}"
CI_ENV_VAR = "CI"


def split_files(files_str: Union[str, List[str]]) -> List[str]:
    """
    Helper function to return a `list` of `str`
    from an input string.

    Args:
    - `files_str` (``str | List[str]``): The input files.

    Returns
    - `List[str]` containing a list of strings.
    """

    if isinstance(files_str, list):
        return files_str
    elif isinstance(files_str, str):
        return files_str.split() if files_str else []
    else:
        raise typer.BadParameter(ERROR_INPUT_FILES_INVALID.format(input=files_str))


def is_ci() -> bool:
    """
    Helper function to detect whether we're running
    in a CI environment. To detect this, we rely on the `CI` env var.

    Returns:
    - `True` if we're in a CI environment, `False` otherwise.
    """

    if os.getenv(CI_ENV_VAR):
        env_var_str = os.getenv(CI_ENV_VAR, "false").lower()
        if env_var_str in {"true", "1", "yes"}:
            return True
        elif env_var_str in {"false", "0", "no"}:
            return False
        else:
            raise typer.BadParameter(
                ERROR_IS_CI_INVALID.format(env_var_str=env_var_str)
            )
    else:
        return False


@main.command(help="Validate that file modes were not changed")
def validate_changed_files_permissions(
    changed_files: List[str] = typer.Argument(
        default=None, help=HELP_CHANGED_FILES, callback=split_files
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

    raise typer.Exit(code=exit_code)


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
            cmd = f"chmod +x {file_path.absolute()}"
        elif new_permission == oct(Blob.executable_mode)[2:]:
            cmd = f"chmod -x {file_path.absolute()}"
        else:
            cmd = f"chmod +||- {file_path.absolute()}"
        message = f"Please revert the file permissions using the command '{cmd}'"
    except IndexError as e:
        logger.warning(f"Unable to get the blob file permissions: {e}")
        message = f"Unable to get the blob file permissions for file '{file_path.absolute()}': {e}"
    finally:
        return message
