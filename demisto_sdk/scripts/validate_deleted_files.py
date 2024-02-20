import os
from pathlib import Path
from typing import List, Set

import typer

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    FileType_ALLOWED_TO_DELETE,
)
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import find_type


def is_file_allowed_to_be_deleted_by_file_type(file_path: Path) -> bool:
    """
    Validate if a file is allowed to be deleted by its type.

    Args:
        file_path: the path of the file
    """
    try:
        file_content = File.read_from_git_path(
            file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH
        )
    except FileNotFoundError:
        logger.warning(
            f"Could not find {file_path} in remote branch {DEMISTO_GIT_UPSTREAM}/{DEMISTO_GIT_PRIMARY_BRANCH}"
        )
        logger.debug(
            f"Retrieving {file_path} content from local branch {DEMISTO_GIT_PRIMARY_BRANCH}"
        )
        file_content = File.read_from_git_path(
            file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH, from_remote=False
        )
    except FileReadError as error:
        logger.warning(
            f"Could not read file {file_path} from git, error: {error}\ntrying to read {file_path} from github"
        )
        file_content = File.read_from_github_api(
            str(file_path),
            tag=DEMISTO_GIT_PRIMARY_BRANCH,
            verify_ssl=True if os.getenv("CI") else False,
        )

    if file_type := find_type(str(file_path), file_content):
        return file_type in FileType_ALLOWED_TO_DELETE

    return True


def get_forbidden_deleted_files(protected_dirs: Set[str]) -> List[str]:
    """
    Returns all the file paths which cannot be deleted
    """
    git_util = GitUtil.from_content_path()
    deleted_files = git_util.deleted_files(DEMISTO_GIT_PRIMARY_BRANCH)

    deleted_files_in_protected_dirs = [
        file_path
        for file_path in deleted_files
        if set(file_path.absolute().parts).intersection(protected_dirs)
    ]

    return [
        str(file_path)
        for file_path in deleted_files_in_protected_dirs
        if not is_file_allowed_to_be_deleted_by_file_type(file_path)
    ]


main = typer.Typer(pretty_exceptions_enable=False)


@main.command()
def validate_forbidden_deleted_files(
    ctx: typer.Context,
    protected_dirs: str = typer.Option(
        "",
        "--protected-dirs",
        help="a comma separated list of protected directories that files cannot be deleted from them",
    ),
):
    if not protected_dirs:
        raise ValueError("--protected-dirs must be provided")
    try:
        if forbidden_deleted_files := get_forbidden_deleted_files(
            set(protected_dirs.split(","))
        ):
            logger.error(
                f'The following file(s) {", ".join(forbidden_deleted_files)} cannot be deleted, restore them'
            )
            raise SystemExit(1)
    except Exception as error:
        logger.error(
            f"Unexpected error occurred while validating deleted files {error}"
        )
        raise


# if __name__ == "__main__":
#     SystemExit(main())
