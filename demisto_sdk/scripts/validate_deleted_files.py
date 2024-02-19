import os
from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    PACKS_DIR,
    TESTS_DIR,
    UTILS_DIR,
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
    file_path = str(file_path)

    try:
        file_content = File.read_from_git_path(file_path)
    except FileNotFoundError:
        logger.warning(
            f"Could not find {file_path} in remote branch {DEMISTO_GIT_UPSTREAM}/{DEMISTO_GIT_PRIMARY_BRANCH}"
        )
        logger.debug(
            f"Retrieving {file_path} content from local branch {DEMISTO_GIT_PRIMARY_BRANCH}"
        )
        file_content = File.read_from_git_path(file_path, from_remote=False)
    except FileReadError as error:
        logger.warning(
            f"Could not read file {file_path} from git, error: {error}\ntrying to read {file_path} from github"
        )
        file_content = File.read_from_github_api(
            file_path, verify_ssl=True if os.getenv("CI") else False
        )

    if file_type := find_type(file_path, file_content):
        return file_type in FileType_ALLOWED_TO_DELETE

    return True


def is_file_allowed_to_be_deleted(file_path: Path) -> bool:
    """
    Args:
        file_path: The file path.

    Returns: True if the file allowed to be deleted, else False.

    """
    if not set(file_path.absolute().parts).intersection(
        {PACKS_DIR, TESTS_DIR, UTILS_DIR}
    ):
        # if the file is not under Packs/Tests/Utils folder, allow to delete it
        return True

    return is_file_allowed_to_be_deleted_by_file_type(file_path)


def get_forbidden_deleted_files() -> List[str]:
    """
    Returns all the file paths which cannot be deleted
    """
    git_util = GitUtil.from_content_path()
    deleted_files = git_util.deleted_files(DEMISTO_GIT_PRIMARY_BRANCH)

    return [
        str(file_path)
        for file_path in deleted_files
        if not is_file_allowed_to_be_deleted(file_path)
    ]


def main():
    try:
        if forbidden_deleted_files := get_forbidden_deleted_files():
            logger.error(
                f'The following file(s) {", ".join(forbidden_deleted_files)} cannot be deleted, restore them'
            )
            return 1
        return 0
    except Exception as error:
        logger.error(
            f"Unexpected error occurred while validating deleted files {error}"
        )
        raise


if __name__ == "__main__":
    SystemExit(main())
