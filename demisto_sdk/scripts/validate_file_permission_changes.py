from pathlib import Path
from typing import Any, Dict, List

import typer
from git import Blob

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()


@main.command(help="Validate that file modes were not changed")
def validate_changed_files_permissions(
    changed_files: List[Path] = typer.Argument(
        default=None,
        help="The files to check, e.g. dir/f1 f2 f3.py",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    ci: bool = typer.Option(envvar="CI", default=False),
) -> None:
    """
    Validate whether the file mode was modified. Exit code 0 if no files
    modes were modified, 1 otherwise.

    Args:
    - `changed_files` (``List[Path]``): The files to check, e.g. 'test/f1 f2 f3.py'.
    - `ci` (``bool``): Whether we're in a CI environment or not.
    """

    exit_code = 0

    logging_setup()
    git_util = GitUtil.from_content_path()

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
            result[
                str(changed_file.absolute())
            ] = git_util.has_file_permissions_changed(
                file_path=str(changed_file), ci=ci
            )

        for filename, (is_changed, old_permission, new_permission) in result.items():
            if is_changed:
                logger.error(
                    f"File '{filename}' permission was changed from {old_permission} to {new_permission}"
                )
                msg = get_revert_permission_message(Path(filename), new_permission)
                logger.info(msg)
                exit_code = 1
    else:
        logger.info("No changed files supplied. Terminating...")

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
