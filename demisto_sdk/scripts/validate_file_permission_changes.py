import sys
from pathlib import Path
from typing import Any

import typer
from git import Blob

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()


@main.command(help="Validate that file modes were not changed")
def validate_changed_files_permissions() -> None:

    exit_code = 0

    logging_setup()
    git_util = GitUtil.from_content_path()
    changed_files = [
        str(path) for path in git_util.get_all_changed_files(DEMISTO_GIT_PRIMARY_BRANCH)
    ]

    if changed_files:

        logger.debug(
            f"The following changed files were found comparing '{DEMISTO_GIT_PRIMARY_BRANCH}': {', '.join(changed_files)}"
        )

        logger.debug(
            f"Iterating over {len(changed_files)} changed files to check if their permissions flags have changed..."
        )

        result: dict[str, Any] = {}

        for changed_file in changed_files:
            result[changed_file] = git_util.has_file_permissions_changed(changed_file)

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
        message = f"Please revert the file permissions using the command '{cmd}'"
    except IndexError as e:
        logger.warning(f"Unable to get the blob file permissions: {e}")
        message = f"Unable to get the blob file permissions for file '{file_path.absolute()}': {e}"
    finally:
        return message
