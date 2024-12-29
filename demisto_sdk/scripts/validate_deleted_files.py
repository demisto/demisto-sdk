from __future__ import annotations

import os
from pathlib import Path
from typing import List, Set  # type: ignore[attr-defined]

import typer

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    FileType_ALLOWED_TO_DELETE,
)
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup
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
    except (FileReadError, FileNotFoundError):
        logger.warning(
            f"Could not retrieve {file_path} in remote branch {DEMISTO_GIT_UPSTREAM}/{DEMISTO_GIT_PRIMARY_BRANCH}"
        )
        logger.debug(
            f"Retrieving {file_path} content from local branch {DEMISTO_GIT_PRIMARY_BRANCH}"
        )
        try:
            file_content = File.read_from_git_path(
                file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH, from_remote=False
            )
        except (FileReadError, FileNotFoundError) as error:
            logger.warning(
                f"Could not read file {file_path} from git, error: {error}\ntrying to read {file_path} from github"
            )
            file_content = File.read_from_github_api(
                str(file_path),
                tag=DEMISTO_GIT_PRIMARY_BRANCH,
                verify_ssl=True if os.getenv("CI") else False,
            )
    is_silent = check_if_content_item_is_silent(file_content)
    if file_type := find_type(str(file_path), file_content):
        return True if file_type in FileType_ALLOWED_TO_DELETE or is_silent else False
    return True


def check_if_content_item_is_silent(file_dict):
    if isinstance(file_dict, dict):
        if file_dict.get("issilent"):
            return True
    return False


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


main = typer.Typer(
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@main.command(
    help="Validate that there are not any files deleted from protected directories"
)
def validate_forbidden_deleted_files(
    protected_dirs: List[str],
):
    if not protected_dirs:
        raise ValueError("Provide at least one protected dir")
    logging_setup(calling_function=__name__)
    try:
        forbidden_deleted_files = get_forbidden_deleted_files(set(protected_dirs))
    except Exception as error:
        logger.error(
            f"Unexpected error occurred while validating deleted files {error}"
        )
        raise

    if forbidden_deleted_files:
        logger.error(
            f'The following file(s) {", ".join(forbidden_deleted_files)} cannot be deleted, restore them'
        )
        raise SystemExit(1)
