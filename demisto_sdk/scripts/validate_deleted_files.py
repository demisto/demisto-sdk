from __future__ import annotations

import os
from pathlib import Path
from typing import List, Set  # type: ignore[attr-defined]

import typer

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    FileType_ALLOWED_TO_DELETE,
)
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.validate.initializer import handle_private_repo_deleted_files


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
        try:
            file_content = File.read_from_git_path(
                file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH, from_remote=False
            )
        except (FileReadError, FileNotFoundError):
            file_content = File.read_from_github_api(
                str(file_path),
                tag=DEMISTO_GIT_PRIMARY_BRANCH,
                verify_ssl=True if os.getenv("CI") else False,
            )

    is_silent = check_if_content_item_is_silent(file_content)

    if file_type := find_type(str(file_path), file_content):
        return file_type in FileType_ALLOWED_TO_DELETE or is_silent

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

    # Get deleted files - don't use committed_only to ensure we catch all deletions
    print(f"Getting deleted files with prev_ver={DEMISTO_GIT_PRIMARY_BRANCH}, committed_only=False")
    raw_deleted_files = git_util.deleted_files(
        prev_ver=DEMISTO_GIT_PRIMARY_BRANCH,
        committed_only=False,  # Get both staged and committed to catch all deletions
        staged_only=False,
    )
    print(f"Found {len(raw_deleted_files)} raw deleted files: {sorted([str(f) for f in raw_deleted_files])}")

    deleted_files = handle_private_repo_deleted_files(
        raw_deleted_files, show_deleted_files=False
    )
    print(f"After handle_private_repo_deleted_files: {len(deleted_files)} files: {sorted([str(f) for f in deleted_files])}")

    deleted_files_in_protected_dirs = [
        file_path
        for file_path in deleted_files
        if set(file_path.absolute().parts).intersection(protected_dirs)
    ]
    print(f"Deleted files in protected dirs: {len(deleted_files_in_protected_dirs)} files: {sorted([str(f) for f in deleted_files_in_protected_dirs])}")

    forbidden_files = []
    for file_path in deleted_files_in_protected_dirs:
        print(f"Checking if {file_path} is allowed to be deleted")
        if not is_file_allowed_to_be_deleted_by_file_type(file_path):
            print(f"File {file_path} is FORBIDDEN")
            forbidden_files.append(str(file_path))
        else:
            print(f"File {file_path} is allowed")

    print(f"Total forbidden files: {len(forbidden_files)}: {forbidden_files}")
    return forbidden_files


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
    
    # Use print to ensure output is visible even if pre-commit suppresses logs
    print("=" * 80)
    print("VALIDATE-DELETED-FILES HOOK STARTED")
    print(f"Protected directories: {protected_dirs}")
    print("=" * 80)

    try:
        forbidden_deleted_files = get_forbidden_deleted_files(set(protected_dirs))
    except Exception as error:
        print(f"ERROR: {error}")
        logger.error(
            f"Unexpected error occurred while validating deleted files: {error}"
        )
        logger.exception("Full traceback:")
        raise

    if forbidden_deleted_files:
        print(f'FORBIDDEN DELETIONS FOUND: {", ".join(forbidden_deleted_files)}')
        logger.error(
            f'The following file(s) {", ".join(forbidden_deleted_files)} cannot be deleted, restore them'
        )
        raise SystemExit(1)
    
    print("=" * 80)
    print("VALIDATE-DELETED-FILES HOOK PASSED - No forbidden deletions found")
    print("=" * 80)
