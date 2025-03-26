import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    AUTHOR_IMAGE_FILE_NAME,
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    DOC_FILES_DIR,
    INTEGRATIONS_DIR,
    MODELING_RULES_DIR,
    PACKS_CONTRIBUTORS_FILE_NAME,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME,
    PACKS_README_FILE_NAME,
    PACKS_VERSION_CONFIG_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME,
    PARSING_RULES_DIR,
    PLAYBOOKS_DIR,
    RELEASE_NOTES_DIR,
    SCRIPTS_DIR,
    ExecutionMode,
    FileType,
    GitStatuses,
    PathLevel,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    detect_file_level,
    find_type_by_path,
    get_file_by_status,
    get_relative_path_from_packs_dir,
    is_external_repo,
    specify_files_from_directory,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import (
    ContentDTO,
)
from demisto_sdk.commands.content_graph.parsers.content_item import (
    InvalidContentItemException,
    NotAContentItemException,
)


class Initializer:
    """
    A class for initializing objects to run on based on given flags.
    """

    def __init__(
        self,
        staged=None,
        committed_only=None,
        prev_ver=None,
        file_path=None,
        execution_mode: Optional[ExecutionMode] = None,
    ):
        self.staged = staged
        self.file_path = file_path
        self.committed_only = committed_only
        self.prev_ver = prev_ver
        self.execution_mode = execution_mode

    def validate_git_installed(self):
        """Initialize git util."""
        try:
            self.git_util = Content.git_util()
            self.branch_name = self.git_util.get_current_git_branch_or_hash()
        except (InvalidGitRepositoryError, TypeError):
            # if we are using git - fail the validation by raising the exception.
            if self.execution_mode == ExecutionMode.USE_GIT:
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
                f"<red>Could not find remote {non_existing_remote} reverting to "
                f"{str(self.git_util.repo.remote())}</red>"
            )
            self.prev_ver = self.prev_ver.replace(
                non_existing_remote, str(self.git_util.repo.remote())
            )

        # if running on release branch check against last release.
        if self.branch_name.startswith("21.") or self.branch_name.startswith("22."):
            self.prev_ver = os.environ.get("GIT_SHA1")
            self.committed_only = True

        elif self.branch_name in ["master", "main", DEMISTO_GIT_PRIMARY_BRANCH]:
            self.git_util
            message = "Running on master branch while using git is ill advised.\nrun: 'git checkout -b NEW_BRANCH_NAME' and rerun the command."
            if not is_external_repo() or self.committed_only:
                logger.warning(message)
            else:
                raise Exception(message)

    def print_git_config(self):
        """Printing the git configurations - all the relevant flags."""
        logger.info(
            f"\n<cyan>================= Running on branch {self.branch_name} =================</cyan>"
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
            get_only_current_file_names=False,
        )

        """
        If this command runs on a build triggered by an external contribution PR,
        the relevant modified files may have an "untracked" status in git.
        The following code segment retrieves all relevant untracked files that were changed in the
        external contribution PR. See CIAC-10968 for more info.

        This code snippet ensures that the number of fetched files matches the number of files in
        the contribution_files_relative_paths.txt file. If a discrepancy is found, indicating untracked files,
        it raises a ValueError to halt execution due to a mismatch in file counts.
        See CIAC-12482 for more info.
        """
        if os.getenv("CONTRIB_BRANCH"):
            logger.info(
                "\n<cyan>CONTRIB_BRANCH environment variable found, running validate in contribution flow "
                "on files staged by Utils/update_contribution_pack_in_base_branch.py (Infra repository)</cyan>"
            )
            # Open contribution_files_paths.txt created in Utils/update_contribution_pack_in_base_branch.py (Infra)
            # and read file paths

            with open(
                "contribution_files_relative_paths.txt", "r"
            ) as contribution_file:
                contribution_files_relative_paths_count_lines = len(
                    contribution_file.readlines()
                )

            affected_files = modified_files.union(added_files, renamed_files)
            if contribution_files_relative_paths_count_lines != len(affected_files):
                raise ValueError(
                    "Error: Mismatch in the number of files. The number of fetched files does not match the number"
                    " of files in the contribution_files_relative_paths.txt file."
                    " This indicates that there are untracked files. Unable to proceed."
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

    def gather_objects_to_run_on(
        self,
    ) -> Tuple[Set[BaseContent], Set[Path]]:
        """
        Filter the file that should run according to the given flag (-i/-g/-a).

        Returns:
            Tuple[Set[BaseContent], Set[Path]]: The sets of all the successful casts, and the sets of all failed casts.
        """
        content_objects_to_run: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        non_content_items: Set[Path] = set()
        if self.execution_mode == ExecutionMode.USE_GIT:
            (
                content_objects_to_run,
                invalid_content_items,
                non_content_items,
            ) = self.get_files_using_git()
        elif self.execution_mode == ExecutionMode.SPECIFIC_FILES:
            (
                content_objects_to_run,
                invalid_content_items,
                non_content_items,
            ) = self.paths_to_basecontent_set(
                set(self.load_files(self.file_path.split(",")))
            )
        elif self.execution_mode == ExecutionMode.ALL_FILES:
            logger.info("Running validation on all files.")
            content_dto = ContentDTO.from_path()
            if not isinstance(content_dto, ContentDTO):
                raise Exception("no content found")
            content_objects_to_run = set(content_dto.packs)
        else:
            self.execution_mode = ExecutionMode.USE_GIT
            self.committed_only = True
            (
                content_objects_to_run,
                invalid_content_items,
                non_content_items,
            ) = self.get_files_using_git()

        if self.execution_mode != ExecutionMode.USE_GIT:
            content_objects_to_run_with_packs: Set[BaseContent] = (
                self.get_items_from_packs(content_objects_to_run)
            )
        else:
            content_objects_to_run_with_packs = content_objects_to_run

        for non_content_item in non_content_items:
            logger.warning(
                f"Invalid content path provided: {str(non_content_item)}. Please provide a valid content item or pack path."
            )
        return content_objects_to_run_with_packs, invalid_content_items

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

    def get_files_using_git(self) -> Tuple[Set[BaseContent], Set[Path], Set[Path]]:
        """Return all files added/changed/deleted.

        Returns:
            Tuple[Set[BaseContent], Set[Path], Set[Path]]: The sets of all the successful casts, the sets of all failed casts, and the set of non content items.
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
        file_by_status_dict: Dict[Path, GitStatuses] = {
            file: GitStatuses.MODIFIED for file in modified_files
        }
        file_by_status_dict.update({file: GitStatuses.ADDED for file in added_files})
        # Adding only the new path with the renamed status.
        file_by_status_dict.update(
            {new_path: GitStatuses.RENAMED for _, new_path in renamed_files}
        )
        file_by_status_dict.update(
            {file: GitStatuses.DELETED for file in deleted_files}
        )
        # Keeping a mapping dictionary between the new and the old path.
        renamed_files = {new_path: old_path for old_path, new_path in renamed_files}
        # Calculating the main file for each of changed files and allocate a status for it.
        statuses_dict: Dict[Path, Union[GitStatuses, None]] = self.get_items_status(
            file_by_status_dict
        )
        # Updating the statuses dict with the paths tuple of the renamed files.
        statuses_dict_with_renamed_files_tuple: Dict[
            Union[Path, Tuple[Path, Path]], Union[GitStatuses, None]
        ] = {}
        for path, status in statuses_dict.items():
            if status == GitStatuses.RENAMED:
                statuses_dict_with_renamed_files_tuple[(path, renamed_files[path])] = (
                    status
                )
            else:
                statuses_dict_with_renamed_files_tuple[path] = status
        # Parsing the files.
        basecontent_with_path_set: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        (
            basecontent_with_path_set,
            invalid_content_items,
            non_content_items,
        ) = self.git_paths_to_basecontent_set(
            statuses_dict_with_renamed_files_tuple, prev_ver=self.prev_ver
        )
        return basecontent_with_path_set, invalid_content_items, non_content_items

    def paths_to_basecontent_set(
        self, files_set: Set[Path]
    ) -> Tuple[Set[BaseContent], Set[Path], Set[Path]]:
        """Attempting to convert the given paths to a set of BaseContent.

        Args:
            files_set (Path): The set of file paths to case into BaseContent.

        Returns:
            Tuple[Set[BaseContent], Set[Path], Set[Path]]: The sets of all the successful casts, the sets of all failed casts, and the set of non content items.
        """
        basecontent_with_path_set: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        non_content_items: Set[Path] = set()
        related_files_main_items: Set[Path] = self.collect_related_files_main_items(
            files_set
        )
        for file_path in related_files_main_items:
            path: Path = Path(file_path)
            try:
                temp_obj = BaseContent.from_path(
                    path, git_sha=None, raise_on_exception=True
                )
                if temp_obj is None:
                    invalid_content_items.add(path)
                else:
                    basecontent_with_path_set.add(temp_obj)
            except NotAContentItemException:
                non_content_items.add(file_path)  # type: ignore[arg-type]
            except InvalidContentItemException:
                invalid_content_items.add(file_path)  # type: ignore[arg-type]
        return basecontent_with_path_set, invalid_content_items, non_content_items

    def git_paths_to_basecontent_set(
        self,
        statuses_dict: Dict[Union[Path, Tuple[Path, Path]], Union[GitStatuses, None]],
        prev_ver: Optional[str] = None,
    ) -> Tuple[Set[BaseContent], Set[Path], Set[Path]]:
        """Attempting to convert the given paths to a set of BaseContent based on their git statuses.

        Args:
            files_set (set): The set of file paths to case into BaseContent.

        Returns:
            Tuple[Set[BaseContent], Set[Path], Set[Path]]: The sets of all the successful casts, the sets of all failed casts, and the set of non content items.
        """
        basecontent_with_path_set: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        non_content_items: Set[Path] = set()
        git_util = GitUtil.from_content_path()
        current_git_sha = git_util.get_current_git_branch_or_hash()
        for file_path, git_status in statuses_dict.items():
            if git_status == GitStatuses.DELETED:
                continue
            try:
                old_path = file_path
                if isinstance(file_path, tuple):
                    file_path, old_path = file_path
                obj = BaseContent.from_path(file_path, raise_on_exception=True)
                if obj:
                    obj.git_sha = current_git_sha
                    obj.git_status = git_status
                    # Check if the file exists
                    if (
                        git_status in (GitStatuses.MODIFIED, GitStatuses.RENAMED)
                        or (
                            not git_status  # Always collect the origin version of the metadata.
                            and find_type_by_path(file_path) == FileType.METADATA
                        )
                    ):
                        try:
                            obj.old_base_content_object = BaseContent.from_path(
                                old_path, git_sha=prev_ver, raise_on_exception=True
                            )
                        except (NotAContentItemException, InvalidContentItemException):
                            logger.debug(
                                f"Could not parse the old_base_content_object for {obj.path}, setting a copy of the object as the old_base_content_object."
                            )
                            obj.old_base_content_object = obj.copy(deep=True)
                    else:
                        obj.old_base_content_object = obj.copy(deep=True)
                    if obj.old_base_content_object:
                        obj.old_base_content_object.git_sha = prev_ver
                    basecontent_with_path_set.add(obj)
                elif obj is None:
                    invalid_content_items.add(file_path)
            except NotAContentItemException:
                non_content_items.add(file_path)  # type: ignore[arg-type]
            except InvalidContentItemException:
                invalid_content_items.add(file_path)  # type: ignore[arg-type]
        return basecontent_with_path_set, invalid_content_items, non_content_items

    @staticmethod
    def log_related_files(
        all_files: Set[Path], explicitly_collected_files: Set[Path]
    ) -> None:
        """Log the files that were not explicitly collected in previous steps.

        Args:
            all_files (set): A set of all the files including implicit related files.
            explicitly_collected_files (set): The set of all the explicitly collected files.
        """
        related_files = all_files.difference(explicitly_collected_files)
        if related_files:
            logger.info("Running on related files:")
            logger.info(f"{[str(path) for path in related_files]}")

    def get_items_status(
        self, file_by_status_dict: Dict[Path, GitStatuses]
    ) -> Dict[Path, Union[GitStatuses, None]]:
        """Get the relevant content items given the input files and their statuses.

        Args:
            file_by_status_dict (dict): A dict of all the input files and their git statuses.

        Returns:
            (dict) A dict of all paths to content items and their git statuses.
        """
        statuses_dict: Dict[Path, Union[GitStatuses, None]] = {}
        for path, git_status in file_by_status_dict.items():
            path_str = str(path)
            if self.is_unrelated_path(path_str):
                # If the path is not related to a content item, continue.
                continue
            if f"/{INTEGRATIONS_DIR}/" in path_str or f"/{SCRIPTS_DIR}/" in path_str:
                # If it's an integration or a script obtain the yml file to create the content item.
                if path_str.endswith(".yml"):
                    # File already is the yml.
                    statuses_dict[path] = git_status
                elif self.is_code_file(path, path_str):
                    # File is the code file.
                    path = self.obtain_yml_from_code(path_str)
                    if path not in statuses_dict:
                        if git_status != GitStatuses.RENAMED:
                            statuses_dict[path] = git_status
                        else:
                            statuses_dict[path] = None
                elif f"_{PACKS_README_FILE_NAME}" in path_str:
                    # File is the readme file.
                    path = Path(path_str.replace(f"_{PACKS_README_FILE_NAME}", ".yml"))
                    if path not in statuses_dict:
                        statuses_dict[path] = None
                elif path.parts[-2] not in [{INTEGRATIONS_DIR}, {SCRIPTS_DIR}]:
                    # some nested folder, not related to the main content item.
                    integration_script_index = (
                        path.parts.index(INTEGRATIONS_DIR)
                        if INTEGRATIONS_DIR in path.parts
                        else path.parts.index(SCRIPTS_DIR)
                    )
                    path = Path(
                        os.path.join(*path.parts[: integration_script_index + 2])
                    )
                    path = path / f"{path.parts[-1]}.yml"
                    if path not in statuses_dict:
                        statuses_dict[path] = None
                else:
                    # Otherwise, assume the yml name is the name of the parent directory.
                    path = Path(path.parent / f"{path.parts[-2]}.yml")
                    if path not in statuses_dict:
                        statuses_dict[path] = None
            elif f"/{PLAYBOOKS_DIR }/" in path_str:
                # If it's inside the playbook directory collect the yml.
                if path_str.endswith(".yml"):
                    # File is already the yml.
                    statuses_dict[path] = git_status
                else:
                    # Otherwise obtain the yml path independently.
                    path = self.obtain_playbook_path(path)
                    if path not in statuses_dict and path.suffix == ".yml":
                        statuses_dict[path] = None
            elif MODELING_RULES_DIR in path_str or PARSING_RULES_DIR in path_str:
                # If it's a modeling rule or a parsing rule obtain the yml.
                if path.suffix in [".json", ".xif"]:
                    # If it ends with a .json or a .xif replace the ending to the corresponding yml.
                    path = Path(
                        path_str.replace(".xif", ".yml").replace("_schema.json", ".yml")
                    )
                    if path not in statuses_dict:
                        statuses_dict[path] = None
                else:
                    # Otherwise assume it's already the yml and collect it.
                    statuses_dict[path] = git_status
            elif PACKS_PACK_META_FILE_NAME in path_str:
                # If the file is a pack metadata, collect it.
                statuses_dict[path] = git_status
            elif not self.is_pack_item(path_str):
                # If the file is not a pack item, collect it as well.
                statuses_dict[path] = git_status

            # Always collect the metadata file of the relevant path.
            metadata_path = self.obtain_metadata_path(path)
            if metadata_path not in statuses_dict:
                # If the metadata file was not already collected explicitly, set its status to None.
                statuses_dict[metadata_path] = None

        self.log_related_files(
            set(statuses_dict.keys()), set(file_by_status_dict.keys())
        )
        return statuses_dict

    def load_files(self, files: List[str]) -> Set[Path]:
        """Recursively load all files from a given list of paths.

        Args:
            files (List[str]): The list of paths.

        Returns:
            Set[Path]: The set of files obtained from the list of paths.
        """
        loaded_files: Set[Path] = set()
        for file in files:
            file_level = detect_file_level(file)
            file_obj: Path = Path(file)
            if file_level in [PathLevel.FILE, PathLevel.PACK]:
                loaded_files.add(file_obj)
            else:
                loaded_files.update(
                    {path for path in file_obj.rglob("*") if path.is_file()}
                )
        return loaded_files

    def collect_related_files_main_items(self, file_paths: Set[Path]) -> Set[Path]:
        """Convert the given file path to the main item its related to.

        Args:
            file_paths (Set[Path]): The set of files to convert.

        Returns:
            Set[Path]: The set of the main paths obtained from the given paths set.
        """
        paths_set: Set[Path] = set()
        for path in file_paths:
            path_str = str(path)
            if self.is_unrelated_path(path_str):
                continue
            if f"/{INTEGRATIONS_DIR}/" in path_str or f"/{SCRIPTS_DIR}/" in path_str:
                if path_str.endswith(".yml"):
                    paths_set.add(path)
                elif self.is_code_file(path, path_str):
                    paths_set.add(self.obtain_yml_from_code(path_str))
                elif f"_{PACKS_README_FILE_NAME}" in path_str:
                    path = Path(path_str.replace(f"_{PACKS_README_FILE_NAME}", ".yml"))
                    paths_set.add(path)
                else:
                    paths_set.add(path.parent / f"{path.parts[-2]}.yml")
            elif f"/{PLAYBOOKS_DIR }/" in path_str:
                if path_str.endswith(".yml"):
                    paths_set.add(path)
                else:
                    paths_set.add(self.obtain_playbook_path(path))
            elif MODELING_RULES_DIR in path_str or PARSING_RULES_DIR in path_str:
                path = Path(
                    path_str.replace(".xif", ".yml").replace("_schema.json", ".yml")
                )
                paths_set.add(path)
            elif PACKS_PACK_META_FILE_NAME in path_str:
                paths_set.add(path)
            elif self.is_pack_item(path_str):
                paths_set.add(self.obtain_metadata_path(path))
            else:
                paths_set.add(path)

        return paths_set

    def is_unrelated_path(self, path: str) -> bool:
        """Return whether the given path is an item that should be validated or not.

        Args:
            path (str): The path to check

        Returns:
            bool: True if the item is unrelated. Otherwise, return False.
        """
        return "Packs" not in path or any(
            file in path.lower()
            for file in (
                "commands_example.txt",
                "commands_examples.txt",
                "command_examples.txt",
                "test_data",
                "testdata",
            )
        )

    def is_pack_item(self, path: str) -> bool:
        """whether the given item is related to the pack level or not.

        Args:
            path (str): The path to test

        Returns:
            bool: True if the given path is related to the pack level. Otherwise, return False.
        """
        return any(
            file in path
            for file in (
                PACKS_PACK_IGNORE_FILE_NAME,
                RELEASE_NOTES_DIR,
                PACKS_WHITELIST_FILE_NAME,
                PACKS_README_FILE_NAME,
                AUTHOR_IMAGE_FILE_NAME,
                PACKS_CONTRIBUTORS_FILE_NAME,
                DOC_FILES_DIR,
                PACKS_VERSION_CONFIG_FILE_NAME,
            )
        )

    def is_code_file(self, path: Path, path_str: str) -> bool:
        """Return whether the given path is a integration/script code path.

        Args:
            path (Path): The path as a Pathlib object.
            path_str (str): The path as a string.

        Returns:
            bool: True if the given path is a integration/script code. Otherwise, return False.
        """
        return path.suffix in (".py", "js", "ps1") and not any(
            [
                path_str.endswith("_test.py"),
                path_str.endswith("_test.js"),
                path_str.endswith("_test.ps1"),
            ]
        )

    def obtain_playbook_path(self, path: Path) -> Path:
        """Generate playbook path

        Args:
            path (Path): the path to generate the playbook path from

        Returns:
            Path: the playbook path
        """
        return path.parent / str(path.parts[-1]).replace(
            f"_{PACKS_README_FILE_NAME}", ".yml"
        )

    def obtain_yml_from_code(self, path: str) -> Path:
        """Generate a script / integration yml path from code path.

        Args:
            path (Path): the code path to generate the script / integration yml path from.

        Returns:
            Path: the yml path.
        """
        return Path(
            path.replace(".py", ".yml").replace(".js", ".yml").replace(".ps1", ".yml")
        )

    def obtain_metadata_path(self, path: Path) -> Path:
        """Create a pack_metadata.json path from a given pack related item.

        Args:
            path (Path): The path to generate the pack_metadata.json path from.

        Returns:
            str: The pack_metadata.json path.
        """
        path_str = ""
        for i, part in enumerate(path.parts):
            path_str = f"{path_str}{part}/"
            if part == "Packs":
                path_str = (
                    f"{path_str}{path.parts[i+1]}/{PACKS_PACK_META_FILE_NAME}"
                ).replace("//", "/")
                break
        return Path(path_str)
