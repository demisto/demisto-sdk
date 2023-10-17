import os
from typing import Optional, Set, Tuple

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    PathLevel,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    detect_file_level,
    find_type,
    get_file_by_status,
    get_relative_path_from_packs_dir,
    is_old_file_format,
    specify_files_from_directory,
)
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult


class GitInitializer:
    def __init__(
        self,
        use_git=None,
        staged=None,
        is_circle=None,
    ):
        self.staged = staged
        self.use_git = use_git
        self.is_circle = is_circle

    def validate_git_installed(self):
        """Initialize git util.
        """
        try:
            self.git_util = Content.git_util()
            self.branch_name = self.git_util.get_current_git_branch_or_hash()
        except (InvalidGitRepositoryError, TypeError):
            # if we are using git - fail the validation by raising the exception.
            if self.use_git:
                raise
            # if we are not using git - simply move on.
            else:
                logger.info("Unable to connect to git")
                self.git_util = None  # type: ignore[assignment]
                self.branch_name = ""

    def setup_prev_ver(self, prev_ver: Optional[str]):
        """Calculate the prev_ver to set

        Args:
            prev_ver (Optional[str]): Previous branch or SHA1 commit to run checks against.

        Returns:
            str: The prev_ver to set.
        """
        # if prev_ver parameter is set, use it
        if prev_ver:
            return prev_ver

        # If git is connected - Use it to get prev_ver
        if self.git_util:
            # If demisto exists in remotes if so set prev_ver as 'demisto/master'
            if self.git_util.check_if_remote_exists("demisto"):
                return "demisto/master"

            # Otherwise, use git to get the primary branch
            _, branch = self.git_util.handle_prev_ver()
            return f"{DEMISTO_GIT_UPSTREAM}/" + branch

        # Default to 'origin/master'
        return f"{DEMISTO_GIT_UPSTREAM}/master"

    def set_prev_ver(self, prev_ver: Optional[str]):
        """Setting up the prev_ver parameter

        Args:
            prev_ver (Optional[str]): Previous branch or SHA1 commit to run checks against.
        """
        if prev_ver and not prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
            prev_ver = f"{DEMISTO_GIT_UPSTREAM}/" + prev_ver
        self.prev_ver = self.setup_prev_ver(prev_ver)

    def collect_files_to_run(self, file_path: str) -> Tuple[Set, Set, Set, Set]:
        """Collecting the files to validate

        Args:
            file_path (str): A comma separated list of file paths to filter to only specified paths.

        Returns:
            Tuple[Set, Set, Set, Set]: The modified files, added files, old format files, and deleted files sets.
        """

        (
            modified_files,
            added_files,
        ) = self.get_changed_files_from_git()

        (modified_files, added_files, old_format_files) = self.get_old_format_files(
            modified_files, added_files
        )

        # filter to only specified paths if given
        if file_path:
            (
                modified_files,
                added_files,
                old_format_files,
            ) = self.specify_files_by_status(
                modified_files, added_files, old_format_files, file_path
            )

        deleted_files = self.git_util.deleted_files(
            prev_ver=self.prev_ver,
            committed_only=self.is_circle,
            staged_only=self.staged,
        )

        return (
            modified_files,
            added_files,
            old_format_files,
            deleted_files,
        )

    def get_old_format_files(self, modified_files: set, added_files: set) -> Tuple[Set, Set, Set]:
        """Filter the given sets into old format files, modified, and added files sets.

        Args:
            modified_files (set): The set of the modified files paths
            added_files (set): The set of the added files paths

        Returns:
            Tuple[Set, Set, Set]: The modified files, added files, and the old format files sets.
        """
        old_format_modified_files, modified_files = self.filter_old_format(
            modified_files
        )
        old_format_added_files, added_files = self.filter_old_format(added_files)
        old_format_files: set = old_format_modified_files.union(old_format_added_files)
        return modified_files, added_files, old_format_files

    def filter_old_format(self, files_set: set) -> Tuple[Set, Set]:
        """Split the given set into sets of old and new format files.

        Args:
            files_set (set): The set to filter

        Returns:
            Tuple[Set, Set]: The old and the new format files sets.
        """
        old_format_files = set()
        new_format_files = set()
        for file_path in files_set:
            file_type = find_type(file_path)
            if is_old_file_format(file_path, file_type):
                old_format_files.add(file_path)
            else:
                new_format_files.add(file_path)
        return old_format_files, new_format_files

    def setup_git_params(self,):
        """Setting up the git relevant params"""
        self.branch_name = (
            self.git_util.get_current_git_branch_or_hash()
            if (self.git_util and not self.branch_name)
            else self.branch_name
        )

        # check remote validity
        if "/" in self.prev_ver and not self.git_util.check_if_remote_exists(
            self.prev_ver
        ):
            non_existing_remote = self.prev_ver.split("/")[0]
            logger.info(
                f"[red]Could not find remote {non_existing_remote} reverting to "
                f"{str(self.git_util.repo.remote())}[/red]"
            )
            self.prev_ver = self.prev_ver.replace(
                non_existing_remote, str(self.git_util.repo.remote())
            )

        # if running on release branch check against last release.
        if self.branch_name.startswith("21.") or self.branch_name.startswith("22."):
            self.skip_pack_rn_validation = True
            self.prev_ver = os.environ.get("GIT_SHA1")
            self.is_circle = True

            # when running against git while on release branch - show errors but don't fail the validation
            self.always_valid = True

        # On main or master don't check RN
        elif self.branch_name in ["master", "main", DEMISTO_GIT_PRIMARY_BRANCH]:
            return ValidationResult(
                error_code="BA107",
                is_valid=False,
                message="Running on master branch while using git is ill advised.\nrun: 'git checkout -b NEW_BRANCH_NAME' and rerun the command.",
                file_path="",
            )
        return ValidationResult(
            error_code="BA107", is_valid=True, message="", file_path=""
        )

    def print_git_config(self):
        """Printing the git configurations - all the relevant flags.
        """
        logger.info(
            f"\n[cyan]================= Running validation on branch {self.branch_name} =================[/cyan]"
        )
        logger.info(f"Validating against {self.prev_ver}")

        if self.branch_name in [
            self.prev_ver,
            self.prev_ver.replace(f"{DEMISTO_GIT_UPSTREAM}/", ""),
        ]:  # pragma: no cover
            logger.info("Running only on last commit")

        elif self.is_circle:
            logger.info("Running only on committed files")

        elif self.staged:
            logger.info("Running only on staged files")

        else:
            logger.info("Running on committed and staged files")

    def get_changed_files_from_git(self) -> Tuple[Set, Set]:
        """Get the added and modified files.

        Returns:
            - The modified files (including the renamed files)
            - The added files
        """

        (
            modified_files,
            added_files,
            renamed_files,
        ) = self.get_unfiltered_changed_files_from_git()

        modified_files = modified_files.union(renamed_files)

        return (
            modified_files,
            added_files,
        )

    def get_unfiltered_changed_files_from_git(self) -> Tuple[Set, Set, Set]:
        """
        Get the added and modified before file filtration to only relevant files

        Returns:
            3 sets:
            - The unfiltered modified files
            - The unfiltered added files
            - The unfiltered renamed files
        """
        # get files from git by status identification against prev-ver
        modified_files = self.git_util.modified_files(
            prev_ver=self.prev_ver,
            committed_only=self.is_circle,
            staged_only=self.staged,
            debug=True,
        )
        added_files = self.git_util.added_files(
            prev_ver=self.prev_ver,
            committed_only=self.is_circle,
            staged_only=self.staged,
            debug=True,
        )
        renamed_files = self.git_util.renamed_files(
            prev_ver=self.prev_ver,
            committed_only=self.is_circle,
            staged_only=self.staged,
            debug=True,
            get_only_current_file_names=True,
        )

        return modified_files, added_files, renamed_files

    def specify_files_by_status(
        self,
        modified_files: Set,
        added_files: Set,
        old_format_files: Set,
        file_path: str,
    ) -> Tuple[Set, Set, Set]:
        """Filter the files identified from git to only specified files.

        Args:
            modified_files(Set): A set of modified and renamed files.
            added_files(Set): A set of added files.
            old_format_files(Set): A set of old format files.

        Returns:
            Tuple[Set, Set, Set]. 3 sets for modified, added an old format files where the only files that
            appear are the ones specified by the 'file_path' ValidateManager parameter
        """
        filtered_modified_files: Set = set()
        filtered_added_files: Set = set()
        filtered_old_format: Set = set()

        for path in file_path.split(","):
            path = get_relative_path_from_packs_dir(path)
            file_level = detect_file_level(path)
            if file_level == PathLevel.FILE:
                temp_modified, temp_added, temp_old_format = get_file_by_status(
                    modified_files, old_format_files, path
                )
                filtered_modified_files = filtered_modified_files.union(temp_modified)
                filtered_added_files = filtered_added_files.union(temp_added)
                filtered_old_format = filtered_old_format.union(temp_old_format)

            else:
                filtered_modified_files = filtered_modified_files.union(
                    specify_files_from_directory(modified_files, path)
                )
                filtered_added_files = filtered_added_files.union(
                    specify_files_from_directory(added_files, path)
                )
                filtered_old_format = filtered_old_format.union(
                    specify_files_from_directory(old_format_files, path)
                )

        return filtered_modified_files, filtered_added_files, filtered_old_format
