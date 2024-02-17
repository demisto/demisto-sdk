from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.git_util import GitUtil
from pathlib import Path
from demisto_sdk.commands.common.constants import PACKS_DIR, FileType_ALLOWED_TO_DELETE
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.tools import _get_file_id

GIT_UTIL = GitUtil.from_content_path()


def is_file_allowed_to_be_deleted_by_predefined_types(file_path: Path) -> bool:
    file_path = str(file_path)

    try:
        file_dict = File.read_from_git_path(file_path)
    except FileReadError as error:
        logger.warning(f'Could not read file {file_path} from git, error: {error}\ntrying to read {file_path} from github')
        file_dict = File.read_from_github_api(file_path, verify_ssl=False)

    file_type = find_type(file_path, file_dict)
    return file_type in FileType_ALLOWED_TO_DELETE or not file_type


def is_file_allowed_to_be_deleted(file_path: Path) -> bool:
    """
    Args:
        file_path: The file path.

    Returns: True if the file allowed to be deleted, else False.

    """
    if PACKS_DIR not in file_path.absolute().parts:
        return True

    return is_file_allowed_to_be_deleted_by_predefined_types(file_path)


def was_file_renamed_but_labeled_as_deleted(deleted_file_path, added_files):
    """
    """
    if added_files:
        deleted_file_path = str(deleted_file_path)
        deleted_file_dict = File.read_from_git_path(
            deleted_file_path
        )  # for detecting deleted files
        if deleted_file_type := find_type(deleted_file_path, deleted_file_dict):
            deleted_file_id = _get_file_id(
                deleted_file_type.value, deleted_file_dict
            )
            if deleted_file_id:
                for file in added_files:
                    file = str(file)
                    file_type = find_type(file)
                    if file_type == deleted_file_type:
                        file_dict = File.read_from_local_path(file)
                        if deleted_file_id == _get_file_id(
                            file_type.value, file_dict
                        ):
                            return True
    return False


def validate_deleted_files():
    deleted_files = GIT_UTIL.deleted_files(
        # committed_only=True,
        # staged_only=True,
    )
    added_files = GIT_UTIL.added_files(
        committed_only=True,
        staged_only=True,
    )

    for file_path in deleted_files:
        if not is_file_allowed_to_be_deleted(file_path):
            logger.error(f'file {file_path} cannot be deleted')
            continue
        if was_file_renamed_but_labeled_as_deleted(file_path, added_files) and not is_file_allowed_to_be_deleted_by_predefined_types(file_path):
            logger.error(f'file {file_path} cannot be deleted')


def main():
    try:
        validate_deleted_files()
    except Exception as error:
        logger.error(f'Unexpected error occurred while validating deleted files {error}')
        raise


if __name__ == "__main__":
    SystemExit(main())