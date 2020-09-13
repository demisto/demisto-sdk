import copy
from typing import List

from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.unify.unifier import Unifier
from wcmatch.pathlib import Path


def normalize_file_name(file_name: str, file_prefix: str) -> str:
    """Add prefix to file name if not exists.

    Examples:
        1. "hello-world.yml" -> "<prefix>-hello-world.yml"

    Returns:
        str: Normalize file name.
    """
    if file_prefix and not file_name.startswith(f'{file_prefix}-'):
        file_name = f'{file_prefix}-{file_name}'

    return file_name


def unify_handler(source_dir: Path, dest_dir: Path) -> List[Path]:
    """Unify YAMLContentUnfiedObject in destination dir.

    Args:
        source_dir:
        file_type:
        dest_dir: Destination directory.

    Returns:
        List[Path]: List of new created files.
    """
    # Directory configuration - Integrations or Scripts
    unify_dir = SCRIPTS_DIR if SCRIPTS_DIR in source_dir.parts else INTEGRATIONS_DIR
    # Unify step
    unifier = Unifier(input=str(source_dir), dir_name=unify_dir, output=str(dest_dir), force=True)
    created_files: List[str] = unifier.merge_script_package_to_yml()
    # Validate that unify succeed - there is not exception raised in unify module.
    if not created_files:
        raise Exception()

    return [Path(path) for path in created_files]


def split_yaml_4_5_0(source_dir: Path, source_dict: dict) -> List[Path]:
    """Split YAMLContentUnfiedObject in destination dir.

    Args:
        source_dict:
        source_dir:
        file_type:

    Returns:
        List[Path]: List of new created files.

    Notes:
        1. If object contain docker_image_4_5 key with value -> should split to:
            a. <original_file>
            b. <original_file_name>_4_5.yml
    """
    # Directory configuration - Integrations or Scripts
    unify_dir = SCRIPTS_DIR if SCRIPTS_DIR in source_dir.parts else INTEGRATIONS_DIR
    # Split step
    unifier = Unifier(input=str(source_dir), dir_name=unify_dir, output=source_dir, force=True)
    source_dict_copy = copy.deepcopy(source_dict)
    script_values = source_dict if SCRIPTS_DIR in source_dir.parts else source_dict.get('script', {})
    created_files: List[str] = unifier.write_yaml_with_docker(source_dict_copy, source_dict, script_values).keys()
    # Validate that split succeed - there is not exception raised in unify module.
    if not created_files:
        raise Exception()

    return [Path(path) for path in created_files]
