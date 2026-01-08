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
from demisto_sdk.commands.validate.initializer import handle_private_repo_deleted_files


def is_file_allowed_to_be_deleted_by_file_type(file_path: Path) -> bool:
    """
    Validate if a file is allowed to be deleted by its type.

    Args:
        file_path: the path of the file
    """
    logger.info(f"Checking if file is allowed to be deleted: {file_path}")
    try:
        logger.info(f"Attempting to read {file_path} from remote branch {DEMISTO_GIT_UPSTREAM}/{DEMISTO_GIT_PRIMARY_BRANCH}")
        file_content = File.read_from_git_path(
            file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH
        )
        logger.info(f"Successfully read {file_path} from remote branch")
    except (FileReadError, FileNotFoundError) as remote_error:
        logger.info(
            f"Could not retrieve {file_path} in remote branch {DEMISTO_GIT_UPSTREAM}/{DEMISTO_GIT_PRIMARY_BRANCH}, error: {remote_error}"
        )
        logger.info(
            f"Retrieving {file_path} content from local branch {DEMISTO_GIT_PRIMARY_BRANCH}"
        )
        try:
            file_content = File.read_from_git_path(
                file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH, from_remote=False
            )
            logger.info(f"Successfully read {file_path} from local branch")
        except (FileReadError, FileNotFoundError) as error:
            logger.info(
                f"Could not read file {file_path} from local git, error: {error}"
            )
            logger.info(f"Attempting to read {file_path} from GitHub API")
            file_content = File.read_from_github_api(
                str(file_path),
                tag=DEMISTO_GIT_PRIMARY_BRANCH,
                verify_ssl=True if os.getenv("CI") else False,
            )
            logger.info(f"Successfully read {file_path} from GitHub API")
    
    is_silent = check_if_content_item_is_silent(file_content)
    logger.info(f"File {file_path} is_silent: {is_silent}")
    
    if file_type := find_type(str(file_path), file_content):
        logger.info(f"File {file_path} detected type: {file_type}")
        is_allowed = file_type in FileType_ALLOWED_TO_DELETE or is_silent
        logger.info(f"File {file_path} type {file_type} is {'ALLOWED' if is_allowed else 'NOT ALLOWED'} to be deleted (in FileType_ALLOWED_TO_DELETE: {file_type in FileType_ALLOWED_TO_DELETE})")
        return is_allowed
    
    logger.info(f"File {file_path} has no detected type, allowing deletion by default")
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
    logger.info(f"Starting get_forbidden_deleted_files with protected_dirs: {protected_dirs}")
    
    logger.info("Initializing GitUtil from content path")
    git_util = GitUtil.from_content_path()
    
    logger.info(f"Getting deleted files from branch: {DEMISTO_GIT_PRIMARY_BRANCH}")
    raw_deleted_files = git_util.deleted_files(DEMISTO_GIT_PRIMARY_BRANCH)
    logger.info(f"Found {len(raw_deleted_files)} raw deleted files: {[str(f) for f in raw_deleted_files]}")
    
    logger.info("Handling private repo deleted files")
    deleted_files = handle_private_repo_deleted_files(
        raw_deleted_files, show_deleted_files=False
    )
    logger.info(f"After handling private repo: {len(deleted_files)} deleted files: {[str(f) for f in deleted_files]}")

    logger.info("Filtering deleted files in protected directories")
    deleted_files_in_protected_dirs = [
        file_path
        for file_path in deleted_files
        if set(file_path.absolute().parts).intersection(protected_dirs)
    ]
    logger.info(f"Found {len(deleted_files_in_protected_dirs)} deleted files in protected dirs: {[str(f) for f in deleted_files_in_protected_dirs]}")

    logger.info("Checking which deleted files are forbidden (not allowed to be deleted)")
    forbidden_files = []
    for file_path in deleted_files_in_protected_dirs:
        logger.info(f"Checking file: {file_path}")
        if not is_file_allowed_to_be_deleted_by_file_type(file_path):
            logger.info(f"File {file_path} is FORBIDDEN to delete")
            forbidden_files.append(str(file_path))
        else:
            logger.info(f"File {file_path} is allowed to delete")
    
    logger.info(f"Total forbidden deleted files: {len(forbidden_files)}: {forbidden_files}")
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
    logger.info("=" * 80)
    logger.info("STARTING VALIDATE_DELETED_FILES HOOK")
    logger.info("=" * 80)
    
    if not protected_dirs:
        logger.error("No protected directories provided")
        raise ValueError("Provide at least one protected dir")
    
    logger.info(f"Protected directories to check: {protected_dirs}")
    logging_setup(calling_function=__name__)
    
    logger.info("Starting validation of forbidden deleted files")
    try:
        forbidden_deleted_files = get_forbidden_deleted_files(set(protected_dirs))
    except Exception as error:
        logger.error(
            f"Unexpected error occurred while validating deleted files: {error}"
        )
        logger.exception("Full traceback:")
        raise

    logger.info(f"Validation complete. Forbidden files count: {len(forbidden_deleted_files)}")
    
    if forbidden_deleted_files:
        logger.error("=" * 80)
        logger.error("VALIDATION FAILED - FORBIDDEN FILES DETECTED")
        logger.error("=" * 80)
        logger.error(
            f'The following file(s) {", ".join(forbidden_deleted_files)} cannot be deleted, restore them'
        )
        raise SystemExit(1)
    
    logger.info("=" * 80)
    logger.info("VALIDATION PASSED - NO FORBIDDEN DELETED FILES")
    logger.info("=" * 80)
