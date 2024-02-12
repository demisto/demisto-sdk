import os
from pathlib import Path
from typing import List, Optional, Set, Tuple

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_UPSTREAM,
    GitStatuses,
    PathLevel,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    detect_file_level,
    get_file_by_status,
    get_relative_path_from_packs_dir,
    specify_files_from_directory,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import (
    ContentDTO,
)
from demisto_sdk.commands.content_graph.parsers.content_item import (
    InvalidContentItemException,
)


class Initializer:
    """
    A class for initializing objects to run on based on given flags.
    """

    def __init__(
        self,
        use_git=False,
        staged=None,
        committed_only=None,
        prev_ver=None,
        file_path=None,
        all_files=False,
    ):
        self.staged = staged
        self.use_git = use_git
        self.file_path = file_path
        self.all_files = all_files
        self.committed_only = committed_only
        self.prev_ver = prev_ver

    def validate_git_installed(self):
        """Initialize git util."""
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

    def setup_prev_ver(self, prev_ver: Optional[str]) -> str:
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

    def set_prev_ver(self):
        """Setting up the prev_ver parameter

        Args:
            prev_ver (Optional[str]): Previous branch or SHA1 commit to run checks against.
        """
        if self.prev_ver and not self.prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
            self.prev_ver = f"{DEMISTO_GIT_UPSTREAM}/" + self.prev_ver
        self.prev_ver = self.setup_prev_ver(self.prev_ver)

    def collect_files_to_run(self, file_path: str) -> Tuple[Set, Set, Set, Set]:
        """Collecting the files to run on divided to modified, added, and deleted.

        Args:
            file_path (str): A comma separated list of file paths to filter to only specified paths.

        Returns:
            Tuple[Set, Set, Set, Set]: The modified, added, renamed, and deleted files sets.
        """

        (
            modified_files,
            added_files,
            renamed_files,
        ) = self.get_unfiltered_changed_files_from_git()

        # filter to only specified paths if given
        if file_path:
            (modified_files, added_files, renamed_files) = self.specify_files_by_status(
                modified_files, added_files, renamed_files, file_path
            )

        deleted_files = self.git_util.deleted_files(
            prev_ver=self.prev_ver,
            committed_only=self.committed_only,
            staged_only=self.staged,
        )

        return (
            modified_files,
            added_files,
            renamed_files,
            deleted_files,
        )

    def setup_git_params(
        self,
    ):
        """Setting up the git relevant params."""
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
            self.prev_ver = os.environ.get("GIT_SHA1")
            self.committed_only = True

    def print_git_config(self):
        """Printing the git configurations - all the relevant flags."""
        logger.info(
            f"\n[cyan]================= Running on branch {self.branch_name} =================[/cyan]"
        )
        logger.info(f"Running against {self.prev_ver}")

        if self.branch_name in [
            self.prev_ver,
            self.prev_ver.replace(f"{DEMISTO_GIT_UPSTREAM}/", ""),
        ]:  # pragma: no cover
            logger.info("Running only on last commit")

        elif self.committed_only:
            logger.info("Running only on committed files")

        elif self.staged:
            logger.info("Running only on staged files")

        else:
            logger.info("Running on committed and staged files")

    def get_changed_files_from_git(self) -> Tuple[Set, Set, Set]:
        """Get the added and modified files.

        Returns:
            - The modified files (including the renamed files).
            - The renamed files.
            - The added files.
        """

        return self.get_unfiltered_changed_files_from_git()

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
            committed_only=self.committed_only,
            staged_only=self.staged,
            debug=True,
        )
        added_files = self.git_util.added_files(
            prev_ver=self.prev_ver,
            committed_only=self.committed_only,
            staged_only=self.staged,
            debug=True,
        )
        renamed_files = self.git_util.renamed_files(
            prev_ver=self.prev_ver,
            committed_only=self.committed_only,
            staged_only=self.staged,
            debug=True,
            get_only_current_file_names=True,
        )

        return modified_files, added_files, renamed_files

    def specify_files_by_status(
        self,
        modified_files: Set,
        added_files: Set,
        renamed_files: Set,
        file_path: str,
    ) -> Tuple[Set, Set, Set]:
        """Filter the files identified from git to only specified files.

        Args:
            modified_files(Set): A set of modified and renamed files.
            added_files(Set): A set of added files.
            renamed_files(Set): A set of renamed files.
            file_path(str): comma separated list of files.

        Returns:
            Tuple[Set, Set, Set]. 3 sets for modified, added, and renamed files where the only files that
            appear are the ones specified by file_path.
        """
        filtered_modified_files: Set = set()
        filtered_added_files: Set = set()
        filtered_renamed_files: Set = set()

        for path in file_path.split(","):
            path = get_relative_path_from_packs_dir(path)
            file_level = detect_file_level(path)
            if file_level == PathLevel.FILE:
                temp_modified, temp_added, temp_renamed = get_file_by_status(
                    modified_files, None, path, renamed_files=renamed_files
                )
                filtered_modified_files = filtered_modified_files.union(temp_modified)
                filtered_added_files = filtered_added_files.union(temp_added)
                filtered_renamed_files = filtered_renamed_files.union(temp_renamed)

            else:
                filtered_modified_files = filtered_modified_files.union(
                    specify_files_from_directory(modified_files, path)
                )
                filtered_added_files = filtered_added_files.union(
                    specify_files_from_directory(added_files, path)
                )
                filtered_renamed_files = filtered_renamed_files.union(
                    specify_files_from_directory(renamed_files, path)
                )

        return filtered_modified_files, filtered_added_files, filtered_renamed_files

    def gather_objects_to_run_on(self) -> Set[BaseContent]:
        """
        Filter the file that should run according to the given flag (-i/-g/-a).

        Returns:
            Set[BaseContent]: the set of files that should run.
        """
        content_objects_to_run: Set[BaseContent] = set()
        if self.use_git:
            content_objects_to_run = self.get_files_from_git()
        elif self.file_path:
            content_objects_to_run = self.paths_to_basecontent_set(
                set(self.file_path.split(",")), None
            )
        elif self.all_files:
            content_dto = ContentDTO.from_path(CONTENT_PATH)
            if not isinstance(content_dto, ContentDTO):
                raise Exception("no content found")
            content_objects_to_run = set(content_dto.packs)
        else:
            self.use_git = (True,)
            self.committed_only = True
            content_objects_to_run = self.get_files_from_git()
        content_objects_to_run_with_packs: Set[BaseContent] = self.get_items_from_packs(
            content_objects_to_run
        )
        return content_objects_to_run_with_packs

    def get_items_from_packs(
        self, content_objects_to_run: Set[BaseContent]
    ) -> Set[BaseContent]:
        """Gets the packs content items from the Packs objects in the given set if they weren't there before.

        Args:
            content_objects_to_run (Set[BaseContent]): The set of BaseContent items to pick the Pack objects from.

        Returns:
            Set[BaseContent]: The given set unified with the content items from inside the Pack objects.
        """
        content_objects_to_run_with_packs: Set[BaseContent] = set()
        for content_object in content_objects_to_run:
            if isinstance(content_object, Pack):
                for content_item in content_object.content_items:
                    if content_item not in content_objects_to_run:
                        content_objects_to_run_with_packs.add(content_item)
            content_objects_to_run_with_packs.add(content_object)
        return content_objects_to_run_with_packs

    def get_files_from_git(self) -> Set[BaseContent]:
        """Return all files added/changed/deleted.

        Returns:
            Set[BaseContent]: The set of all the files from git successfully casted to BaseContent
        """
        self.validate_git_installed()
        self.set_prev_ver()
        self.setup_git_params()
        self.print_git_config()

        (
            modified_files,
            added_files,
            renamed_files,
            deleted_files,
        ) = self.collect_files_to_run(self.file_path)
        modified_files = self.filter_files(modified_files)
        added_files = self.filter_files(added_files)
        renamed_files = self.filter_files(renamed_files)
        deleted_files = self.filter_files(deleted_files)
        basecontent_with_path_set: Set[BaseContent] = set()
        basecontent_with_path_set = basecontent_with_path_set.union(
            self.paths_to_basecontent_set(
                modified_files, GitStatuses.MODIFIED, git_sha=self.prev_ver
            )
        )
        basecontent_with_path_set = basecontent_with_path_set.union(
            self.paths_to_basecontent_set(
                renamed_files, GitStatuses.RENAMED, git_sha=self.prev_ver
            )
        )
        basecontent_with_path_set = basecontent_with_path_set.union(
            self.paths_to_basecontent_set(
                added_files, GitStatuses.ADDED, git_sha=self.prev_ver
            )
        )
        basecontent_with_path_set = basecontent_with_path_set.union(
            self.paths_to_basecontent_set(
                deleted_files, GitStatuses.DELETED, git_sha=self.prev_ver
            )
        )
        return basecontent_with_path_set

    def paths_to_basecontent_set(
        self, files_set: set, git_status: Optional[str], git_sha: Optional[str] = None
    ) -> Set[BaseContent]:
        """Return a set of all the successful casts to BaseContent from given set of files.

        Args:
            files_set (set): The set of file paths to case into BaseContent.
            git_status (Optional[str]): The git status for the given files (if given).

        Returns:
            Set[BaseContent]: The set of all the successful casts to BaseContent from given set of files.
        """
        basecontent_with_path_set: Set[BaseContent] = set()
        invalid_content_items: List[str] = []
        for file_path in files_set:
            try:
                if git_status == GitStatuses.RENAMED:
                    temp_obj: Optional[BaseContent] = BaseContent.from_path(
                        Path(file_path[0]),
                        git_status=git_status,
                        old_file_path=Path(file_path[1]),
                        git_sha=git_sha,
                    )
                elif git_status == GitStatuses.ADDED:
                    temp_obj = BaseContent.from_path(Path(file_path), git_status)
                else:
                    temp_obj = BaseContent.from_path(
                        Path(file_path), git_status, git_sha=git_sha
                    )
                if temp_obj is None:
                    invalid_content_items.append(file_path)
                else:
                    basecontent_with_path_set.add(temp_obj)
            except InvalidContentItemException:
                invalid_content_items.append(file_path)
        return basecontent_with_path_set

    def filter_files(self, files_set: Set[Path]):
        """Filter out all the files with suffixes that are not supported by BaseContent.

        Args:
            files_set (Set[Path]): The set of paths to filter

        Returns:
            Set: The set of filtered files.
        """
        extensions_list_to_filter = [".png", ".md", ".svg"]
        return set(
            file for file in files_set if file.suffix not in extensions_list_to_filter
        )
