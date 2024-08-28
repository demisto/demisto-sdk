import functools
import os
import re
from pathlib import Path
from typing import Callable, List

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    KNOWN_FILE_STATUSES,
    PACKS_PACK_META_FILE_NAME,
    TESTS_AND_DOC_DIRECTORIES,
    FileType,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    filter_packagify_changes,
    find_type,
    get_pack_name,
    has_remote_configured,
    is_origin_content_repo,
    run_command,
)
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager


@functools.lru_cache()
def git_path() -> str:
    git_path = run_command("git rev-parse --show-toplevel")
    return git_path.replace("\n", "")


@functools.lru_cache()
def get_current_working_branch() -> str:
    branches = run_command("git branch")
    branch_name_reg = re.search(r"\* (.*)", branches)
    if branch_name_reg:
        return branch_name_reg.group(1)

    return ""


def get_changed_files(
    from_branch: str = DEMISTO_GIT_PRIMARY_BRANCH, filter_results: Callable = None
):
    temp_files = run_command(f"git diff --name-status {from_branch}").split("\n")
    files: List = []
    for file in temp_files:
        if file:
            temp_file_data = {"status": file[0]}
            if file.lower().startswith("r"):
                file = file.split("\t")
                temp_file_data["name"] = file[2]
            else:
                temp_file_data["name"] = file[2:]
            files.append(temp_file_data)

    if filter_results:
        filter(filter_results, files)

    return files


# """ ################################### Validate Git Tools and filtering #################################### """


def add_origin(branch_name, prev_ver):
    # If git base not provided - check against origin/prev_ver unless using release branch
    if "/" not in prev_ver and not (
        branch_name.startswith("20.") or branch_name.startswith("21.")
    ):
        prev_ver = f"{DEMISTO_GIT_UPSTREAM}/" + prev_ver
    return prev_ver


def filter_staged_only(
    modified_files, added_files, old_format_files, changed_meta_files
):
    """The function gets sets of files which were changed in the current branch and filters
    out only the files that were changed in the current commit"""
    all_changed_files = run_command("git diff --name-only --staged").split()
    formatted_changed_files = set()

    for changed_file in all_changed_files:
        if find_type(changed_file) in [FileType.POWERSHELL_FILE, FileType.PYTHON_FILE]:
            changed_file = os.path.splitext(changed_file)[0] + ".yml"
        formatted_changed_files.add(changed_file)

    modified_files = modified_files.intersection(formatted_changed_files)
    added_files = added_files.intersection(formatted_changed_files)
    old_format_files = old_format_files.intersection(formatted_changed_files)
    changed_meta_files = changed_meta_files.intersection(formatted_changed_files)
    return modified_files, added_files, old_format_files, changed_meta_files


def get_modified_and_added_files(
    compare_type,
    prev_ver,
    ignored_errors=dict(),
    no_configuration_prints=False,
    staged=False,
    print_ignored_files=False,
    is_circle=False,
    branch_name=None,
):
    """Get the modified and added files from a specific branch

    Args:
        is_circle (bool): Whether the code runs on circle build.
        print_ignored_files (bool): Whether to print ignored files.
        staged (bool): Whether to return only staged files
        no_configuration_prints (bool): Whether to print additional config prints
        ignored_errors (dict): A dict of ignored errors per file.
        branch_name (str): the branch name
        compare_type (str): whether to run diff with two dots (..) or three (...)
        prev_ver (str): Against which branch to run the comparision - master/last release

    Returns:
        tuple. 3 sets representing modified files, added files and files of old format who have changed.
    """
    if not branch_name:
        branch_name = get_current_working_branch()
    base_validator = BaseValidator(ignored_errors=ignored_errors)
    if not no_configuration_prints:
        if staged:
            logger.info("Collecting staged files only")
        else:
            logger.info("Collecting all committed files")

    prev_ver = add_origin(branch_name, prev_ver)
    # all committed changes of the current branch vs the prev_ver
    all_committed_files_string = run_command(
        f"git diff --name-status {prev_ver}{compare_type}refs/heads/{branch_name}"
    )

    (
        modified_files,
        added_files,
        _,
        old_format_files,
        changed_meta_files,
        ignored_files,
        new_packs,
    ) = filter_changed_files(
        all_committed_files_string, prev_ver, print_ignored_files=print_ignored_files
    )

    if not is_circle:
        remote_configured = has_remote_configured()
        is_origin_demisto = is_origin_content_repo()
        if remote_configured and not is_origin_demisto:
            if not no_configuration_prints:
                logger.info(
                    "Collecting all local changed files from fork against the content master"
                )

            # only changes against prev_ver (without local changes)

            all_changed_files_string = run_command(
                "git diff --name-status upstream/master...HEAD"
            )
            (
                modified_files_from_tag,
                added_files_from_tag,
                _,
                _,
                changed_meta_files_from_tag,
                ignored_files_from_tag,
                new_packs_from_tag,
            ) = filter_changed_files(
                all_changed_files_string, print_ignored_files=print_ignored_files
            )

            # all local non-committed changes and changes against prev_ver
            outer_changes_files_string = run_command(
                "git diff --name-status --no-merges upstream/master...HEAD"
            )
            (
                nc_modified_files,
                nc_added_files,
                nc_deleted_files,
                nc_old_format_files,
                nc_changed_meta_files,
                nc_ignored_files,
                nc_new_packs,
            ) = filter_changed_files(
                outer_changes_files_string, print_ignored_files=print_ignored_files
            )

        else:
            if (
                not is_origin_demisto and not remote_configured
            ) and not no_configuration_prints:
                error_message, error_code = Errors.changes_may_fail_validation()
                base_validator.handle_error(
                    error_message,
                    error_code,
                    file_path="General-Error",
                    warning=True,
                    drop_line=True,
                )

            if not no_configuration_prints and not staged:
                logger.info(
                    "Collecting all local changed files against the content master"
                )

            # only changes against prev_ver (without local changes)
            all_changed_files_string = run_command(f"git diff --name-status {prev_ver}")
            (
                modified_files_from_tag,
                added_files_from_tag,
                _,
                _,
                changed_meta_files_from_tag,
                ignored_files_from_tag,
                new_packs_from_tag,
            ) = filter_changed_files(
                all_changed_files_string, print_ignored_files=print_ignored_files
            )

            # all local non-committed changes and changes against prev_ver
            outer_changes_files_string = run_command(
                "git diff --name-status --no-merges HEAD"
            )
            (
                nc_modified_files,
                nc_added_files,
                nc_deleted_files,
                nc_old_format_files,
                nc_changed_meta_files,
                nc_ignored_files,
                nc_new_packs,
            ) = filter_changed_files(
                outer_changes_files_string, print_ignored_files=print_ignored_files
            )

        old_format_files = old_format_files.union(nc_old_format_files)
        modified_files = modified_files.union(
            modified_files_from_tag.intersection(nc_modified_files)
        )

        added_files = added_files.union(
            added_files_from_tag.intersection(nc_added_files)
        )

        changed_meta_files = changed_meta_files.union(
            changed_meta_files_from_tag.intersection(nc_changed_meta_files)
        )

        ignored_files = ignored_files.union(
            ignored_files_from_tag.intersection(nc_ignored_files)
        )

        new_packs = new_packs.union(new_packs_from_tag.intersection(nc_new_packs))

        modified_files = modified_files - set(nc_deleted_files)
        added_files = added_files - set(nc_deleted_files)
        changed_meta_files = changed_meta_files - set(nc_deleted_files)

    if staged:
        (
            modified_files,
            added_files,
            old_format_files,
            changed_meta_files,
        ) = filter_staged_only(
            modified_files, added_files, old_format_files, changed_meta_files
        )

    modified_packs = (
        get_packs(modified_files)
        .union(get_packs(old_format_files))
        .union(get_packs(added_files))
    )
    return (
        modified_files,
        added_files,
        old_format_files,
        changed_meta_files,
        modified_packs,
        ignored_files,
        new_packs,
    )


# flake8: noqa: C901
def filter_changed_files(
    files_string, tag=DEMISTO_GIT_PRIMARY_BRANCH, print_ignored_files=False
):
    """Get lists of the modified files in your branch according to the files string.

    Args:
        files_string (string): String that was calculated by git using `git diff` command.
        tag (string): String of git tag used to update modified files.
        print_ignored_files (bool): should print ignored files.

    Returns:
        Tuple of sets.
    """
    all_files = files_string.split("\n")
    deleted_files = set()
    added_files_list = set()
    modified_files_list = set()
    old_format_files = set()
    changed_meta_files = set()
    ignored_files = set()
    new_packs = set()
    for f in all_files:
        file_data: list = list(filter(None, f.split("\t")))

        if not file_data:
            continue

        file_status = file_data[0]
        file_path = file_data[1]

        if file_status.lower().startswith("r"):
            file_status = "r"
            file_path = file_data[2]
        path = Path(
            file_path
        )  # added as a quick-fix, not replacing in all places even though they'd be prettier.
        try:
            file_type = find_type(file_path)
            # if the file is a code file - change path to
            # the associated yml path to trigger release notes validation.
            if (
                file_status.lower() != "d"
                and file_type in [FileType.POWERSHELL_FILE, FileType.PYTHON_FILE]
                and not (file_path.endswith(("_test.py", ".Tests.ps1")))
            ):
                # naming convention - code file and yml file in packages must have same name.
                file_path = os.path.splitext(file_path)[0] + ".yml"

            # ignore changes in JS files and unit test files.
            elif file_path.endswith((".js", ".py", "ps1")):
                if file_path not in ignored_files:
                    ignored_files.add(file_path)
                    if print_ignored_files:
                        logger.info(
                            f"<yellow>Ignoring file path: {file_path} - code file</yellow>"
                        )
                continue

            # ignore changes in TESTS_DIRECTORIES files.
            elif any(test_dir in file_path for test_dir in TESTS_AND_DOC_DIRECTORIES):
                if file_path not in ignored_files:
                    ignored_files.add(file_path)
                    if print_ignored_files:
                        logger.info(
                            f"<yellow>Ignoring file path: {file_path} - test file</yellow>"
                        )
                continue

            # identify deleted files
            if file_status.lower() == "d" and not file_path.startswith("."):
                deleted_files.add(file_path)

            # ignore directories
            elif not Path(file_path).is_file():
                if print_ignored_files:
                    logger.info(
                        f"<yellow>Ignoring file path: {file_path} - directory</yellow>"
                    )
                continue

            # changes in old scripts and integrations - unified python scripts/integrations
            elif (
                file_status.lower() in ["m", "a", "r"]
                and file_type in [FileType.INTEGRATION, FileType.SCRIPT]
                and OldValidateManager.is_old_file_format(file_path, file_type)
            ):
                old_format_files.add(file_path)
            # identify modified files
            elif (
                file_status.lower() == "m"
                and file_type
                and not path.name.startswith(".")
            ):
                modified_files_list.add(file_path)
            # identify added files
            elif (
                file_status.lower() == "a"
                and file_type
                and not path.name.startswith(".")
            ):
                added_files_list.add(file_path)
            # identify renamed files
            elif file_status.lower().startswith("r") and file_type:
                # if a code file changed, take the associated yml file.
                if file_type in [FileType.POWERSHELL_FILE, FileType.PYTHON_FILE]:
                    modified_files_list.add(file_path)

                else:
                    # file_data[1] = old name, file_data[2] = new name
                    modified_files_list.add((file_data[1], file_data[2]))
            elif file_status.lower() not in KNOWN_FILE_STATUSES:
                logger.error(
                    "<red>{} file status is an unknown one, please check. File status was: {}</red>".format(
                        file_path, file_status
                    )
                )
            # handle meta data file changes
            elif file_path.endswith(PACKS_PACK_META_FILE_NAME):
                if file_status.lower() == "a":
                    new_packs.add(get_pack_name(file_path))
                elif file_status.lower() == "m":
                    changed_meta_files.add(file_path)
            else:
                # pipefile and pipelock files should not enter to ignore_files
                if "Pipfile" not in file_path:
                    if file_path not in ignored_files:
                        ignored_files.add(file_path)
                        if print_ignored_files:
                            logger.info(
                                f"<yellow>Ignoring file path: {file_path} - system file</yellow>",
                            )
                    else:
                        if print_ignored_files:
                            logger.info(
                                f"<yellow>Ignoring file path: {file_path} - system file</yellow>"
                            )

        # handle a case where a file was deleted locally though recognised as added against master.
        except FileNotFoundError:
            if file_path not in ignored_files:
                ignored_files.add(file_path)
                if print_ignored_files:
                    logger.info(
                        f"<yellow>Ignoring file path: {file_path} - File not found</yellow>"
                    )

    modified_files_list, added_files_list, deleted_files = filter_packagify_changes(
        modified_files_list, added_files_list, deleted_files, tag
    )

    return (
        modified_files_list,
        added_files_list,
        deleted_files,
        old_format_files,
        changed_meta_files,
        ignored_files,
        new_packs,
    )


def get_packs(changed_files):
    packs = set()
    for changed_file in changed_files:
        if isinstance(changed_file, tuple):
            changed_file = changed_file[1]
        pack = get_pack_name(changed_file)
        if pack:
            packs.add(pack)

    return packs
