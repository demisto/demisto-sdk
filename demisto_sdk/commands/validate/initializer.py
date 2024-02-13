import copy
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    AUTHOR_IMAGE_FILE_NAME,
    DEMISTO_GIT_UPSTREAM,
    DOC_FILES_DIR,
    INTEGRATIONS_DIR,
    MODELING_RULES_DIR,
    PACKS_CONTRIBUTORS_FILE_NAME,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME,
    PACKS_README_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME,
    PARSING_RULES_DIR,
    PLAYBOOKS_DIR,
    RELEASE_NOTES_DIR,
    SCRIPTS_DIR,
    GitStatuses,
    PathLevel,
    RelatedFileType,
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
            get_only_current_file_names=False,
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
            Set[BaseContent]: the set of files that should run.
        """
        content_objects_to_run: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        if self.use_git:
            content_objects_to_run, invalid_content_items = self.get_files_using_git()
        elif self.file_path:
            (
                content_objects_to_run,
                invalid_content_items,
            ) = self.paths_to_basecontent_set(
                set(self.load_files(self.file_path.split(",")))
            )
        elif self.all_files:
            content_dto = ContentDTO.from_path(CONTENT_PATH)
            if not isinstance(content_dto, ContentDTO):
                raise Exception("no content found")
            content_objects_to_run = set(content_dto.packs)
        else:
            self.use_git = (True,)
            self.committed_only = True
            content_objects_to_run, invalid_content_items = self.get_files_using_git()
        content_objects_to_run_with_packs: Set[BaseContent] = self.get_items_from_packs(
            content_objects_to_run
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

    def get_files_using_git(self) -> Tuple[Set[BaseContent], Set[Path]]:
        """Return all files added/changed/deleted.

        Returns:
            Tuple[Set[BaseContent], Set[Path]]: The sets of all the successful and all failed casts to BaseContent from given set of files.
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
        file_by_status_dict.update(
            {new_path: GitStatuses.RENAMED for _, new_path in renamed_files}
        )
        renamed_files = {new_path: old_path for old_path, new_path in renamed_files}
        file_by_status_dict.update(
            {file: GitStatuses.DELETED for file in deleted_files}
        )
        statuses_dict: Dict[Path, Union[GitStatuses, None]] = self.get_items_status(
            file_by_status_dict
        )
        statuses_dict_with_renamed_files_tuple: Dict[
            Union[Path, Tuple[Path, Path]], Union[GitStatuses, None]
        ] = {}
        for path, status in statuses_dict.items():
            if status == GitStatuses.RENAMED:
                statuses_dict_with_renamed_files_tuple[
                    (path, renamed_files[path])
                ] = status
            else:
                statuses_dict_with_renamed_files_tuple[path] = status
        basecontent_with_path_set: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        (
            basecontent_with_path_set,
            invalid_content_items,
        ) = self.git_paths_to_basecontent_set(
            statuses_dict_with_renamed_files_tuple, git_sha=self.prev_ver
        )
        self.connect_related_files(
            basecontent_with_path_set, file_by_status_dict, renamed_files
        )
        return basecontent_with_path_set, invalid_content_items

    def paths_to_basecontent_set(
        self, files_set: Set[str]
    ) -> Tuple[Set[BaseContent], Set[Path]]:

        """Attempting to convert the given paths to a set of BaseContent.

        Args:
            files_set (set): The set of file paths to case into BaseContent.

        Returns:
            Tuple[Set[BaseContent], Set[Path]]: The sets of all the successful and all failed casts to BaseContent from given set of files.
        """
        basecontent_with_path_set: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        related_files_main_items: Set[str] = self.collect_related_files_main_items(
            files_set
        )
        for file_path in related_files_main_items:
            path: Path = Path(file_path)
            try:
                temp_obj = BaseContent.from_path(path, git_sha=None)
                if temp_obj is None:
                    invalid_content_items.add(path)
                else:
                    basecontent_with_path_set.add(temp_obj)
            except InvalidContentItemException:
                invalid_content_items.add(path)
        return basecontent_with_path_set, invalid_content_items

    def git_paths_to_basecontent_set(
        self,
        statuses_dict: Dict[Union[Path, Tuple[Path, Path]], Union[GitStatuses, None]],
        git_sha: Optional[str] = None,
    ) -> Tuple[Set[BaseContent], Set[Path]]:
        """Attempting to convert the given paths to a set of BaseContent based on their git statuses.

        Args:
            files_set (set): The set of file paths to case into BaseContent.

        Returns:
            Tuple[Set[BaseContent], Set[Path]]: The sets of all the successful and all failed casts to BaseContent from given set of files.
        """
        basecontent_with_path_set: Set[BaseContent] = set()
        invalid_content_items: Set[Path] = set()
        for file_path, git_status in statuses_dict.items():
            if git_status == GitStatuses.DELETED:
                continue
            try:
                old_path = file_path
                if isinstance(file_path, tuple):
                    file_path, old_path = file_path
                obj = BaseContent.from_path(file_path)
                if obj:
                    obj.git_status = git_status
                    # Check if the file exists
                    if git_status in (GitStatuses.MODIFIED, GitStatuses.RENAMED):
                        obj.old_base_content_object = BaseContent.from_path(
                            old_path, git_sha=git_sha
                        )
                    else:
                        obj.old_base_content_object = obj.copy(deep=True)
                    if obj.old_base_content_object:
                        obj.old_base_content_object.git_sha = git_sha
                    basecontent_with_path_set.add(obj)
                elif obj is None:
                    invalid_content_items.add(file_path)
            except InvalidContentItemException:
                invalid_content_items.add(file_path)  # type: ignore[arg-type]
        return basecontent_with_path_set, invalid_content_items

    def get_items_status(
        self, file_by_status_dict: Dict[Path, GitStatuses]
    ) -> Dict[Path, Union[GitStatuses, None]]:
        statuses_dict: Dict[Path, Union[GitStatuses, None]] = {}
        for path, git_status in file_by_status_dict.items():
            path_str = str(path)
            if self.is_unrelated_path(path_str):
                continue
            if "Integrations" in path_str or "Scripts" in path_str:
                if path_str.endswith(".yml"):
                    statuses_dict[path] = git_status
                elif self.is_code_file(path, path_str):
                    path = Path(self.obtain_yml_from_code(path_str))
                    if path not in statuses_dict:
                        statuses_dict[path] = git_status
                elif f"_{PACKS_README_FILE_NAME}" in path_str:
                    path = Path(path_str.replace(f"_{PACKS_README_FILE_NAME}", ".yml"))
                    if path not in statuses_dict:
                        statuses_dict[path] = None
                else:
                    path = Path(path.parent / f"{path.parts[-2]}.yml")
                    if path not in statuses_dict:
                        statuses_dict[path] = None
            elif "Playbooks" in path_str:
                if path_str.endswith(".yml"):
                    statuses_dict[path] = git_status
                else:
                    path = self.obtain_playbook_path(path)
                    if path not in statuses_dict:
                        statuses_dict[path] = None
            elif MODELING_RULES_DIR in path_str or PARSING_RULES_DIR in path_str:
                if path.suffix in [".json", ".xif"]:
                    path = Path(
                        path_str.replace(".xif", ".yml").replace("_schema.json", ".yml")
                    )
                    if path not in statuses_dict:
                        statuses_dict[path] = None
                else:
                    statuses_dict[path] = git_status
            elif PACKS_PACK_META_FILE_NAME in path_str:
                statuses_dict[path] = git_status
            elif self.is_pack_item(path_str):
                metadata_path = Path(self.obtain_metadata_path(path))
                if metadata_path not in statuses_dict:
                    statuses_dict[metadata_path] = None
            else:
                statuses_dict[path] = git_status

        return statuses_dict

    def connect_related_files(
        self,
        basecontent_with_path_set: Set[BaseContent],
        statuses_dict: Dict[Path, GitStatuses],
        renamed_files,
    ):
        paths_set = set(statuses_dict.keys())
        for content_item in basecontent_with_path_set:
            content_item_related_files: Dict[
                RelatedFileType, dict
            ] = content_item.get_related_content()
            old_content_item_related_files = (
                content_item.old_base_content_object.get_related_content()
                if content_item.old_base_content_object
                else copy.deepcopy(content_item_related_files)
            )
            if related_paths := (
                self.get_paths_from_dict(content_item_related_files)
            ).intersection(paths_set):
                for related_path in related_paths:
                    if file_type := self.get_type_by_path(related_path):
                        if statuses_dict[related_path] == GitStatuses.RENAMED:
                            content_item_related_files[file_type]["path"] = related_path
                            content_item_related_files[file_type][
                                "git_status"
                            ] = statuses_dict[related_path]
                            old_content_item_related_files[file_type][
                                "path"
                            ] = renamed_files[related_path]
                        elif statuses_dict[related_path] == GitStatuses.ADDED:
                            content_item_related_files[file_type]["path"] = related_path
                            content_item_related_files[file_type][
                                "git_status"
                            ] = statuses_dict[related_path]
                            old_content_item_related_files[file_type]["path"] = None
                        elif statuses_dict[related_path] == GitStatuses.MODIFIED:
                            content_item_related_files[file_type]["path"] = related_path
                            content_item_related_files[file_type][
                                "git_status"
                            ] = statuses_dict[related_path]
                            old_content_item_related_files[file_type][
                                "path"
                            ] = related_path
                        else:
                            content_item_related_files[file_type]["path"] = None
                            content_item_related_files[file_type][
                                "git_status"
                            ] = statuses_dict[related_path]
                            old_content_item_related_files[file_type][
                                "path"
                            ] = related_path
            content_item.related_content = content_item_related_files
            if content_item.old_base_content_object:
                content_item.old_base_content_object.related_content = (
                    old_content_item_related_files
                )

    def get_paths_from_dict(
        self, content_item_related_files: Dict[RelatedFileType, dict]
    ) -> Set[Path]:
        """Return the set of paths obtained from the related_files_dict.

        Args:
            content_item_related_files (Dict[RelatedFileType, dict]): The dictionary of related files related to a certain object.

        Returns:
            Set[Path]: The obtained set of paths.
        """
        files_set = set()
        for related_file in content_item_related_files.values():
            if isinstance(related_file["path"], tuple):
                for path in related_file["path"]:
                    files_set.add(path)
            else:
                files_set.add(related_file["path"])
        return files_set

    def get_type_by_path(self, path: Path) -> Optional[RelatedFileType]:  # type: ignore[return]
        """Retrieve the file type according to its type.

        Args:
            path (Path): The file path to determine its type.

        Returns:
            Optional[RelatedFileType]: The file type if found.
        """
        str_path = str(path)
        if "description" in str_path:
            return RelatedFileType.DESCRIPTION
        elif PACKS_PACK_IGNORE_FILE_NAME in str_path:
            return RelatedFileType.PACK_IGNORE
        elif PACKS_WHITELIST_FILE_NAME in str_path:
            return RelatedFileType.SECRETS_IGNORE
        elif ".xif" in str_path:
            return RelatedFileType.XIF
        elif "_schema" in str_path:
            return RelatedFileType.SCHEMA
        elif "_dark.svg" in str_path:
            return RelatedFileType.DARK_SVG
        elif "_light.svg" in str_path:
            return RelatedFileType.LIGHT_SVG
        elif PACKS_README_FILE_NAME in str_path:
            return RelatedFileType.README
        elif "Author_image" in str_path:
            return RelatedFileType.AUTHOR_IMAGE
        elif ".png" in str_path:
            return RelatedFileType.IMAGE
        elif path.suffix in (".py", "js", "ps1"):
            if "_test" in str_path:
                return RelatedFileType.TEST_CODE
            return RelatedFileType.CODE

    def load_files(self, paths: List[str]) -> Set[str]:
        """Recursively load all files from a given list of paths.

        Args:
            paths (List[str]): _description_

        Returns:
            Set[str]: The set of files obtained from the list of paths.
        """
        loaded_files: Set[str] = set()
        for path in paths:
            file_level = detect_file_level(path)
            if file_level == PathLevel.FILE:
                loaded_files.add(path)
            else:
                if path.endswith("/"):
                    path = path[:-1]
                loaded_files.update(
                    self.load_files(
                        [f"{path}/{sub_path}" for sub_path in os.listdir(path)]
                    )
                )
        return loaded_files

    def collect_related_files_main_items(self, file_paths: Set[str]) -> Set[str]:
        """Convert the given file path to the main item its related to.

        Args:
            file_paths (Set[str]): The set of files to convert.

        Returns:
            Set[str]: The set of the main paths obtained from the given paths set.
        """
        paths_set: Set[str] = set()
        for path in file_paths:
            path_obj = Path(path)
            if self.is_unrelated_path(path):
                continue
            if INTEGRATIONS_DIR in path or SCRIPTS_DIR in path:
                if path.endswith(".yml"):
                    paths_set.add(path)
                elif self.is_code_file(path_obj, path):
                    paths_set.add(self.obtain_yml_from_code(path))
                elif f"_{PACKS_README_FILE_NAME}" in path:
                    path = path.replace(f"_{PACKS_README_FILE_NAME}", ".yml")
                    paths_set.add(path)
                else:
                    path = str(path_obj.parent / f"{path_obj.parts[-2]}.yml")
                    paths_set.add(path)
            elif PLAYBOOKS_DIR in path:
                if path.endswith(".yml"):
                    paths_set.add(path)
                else:
                    paths_set.add(str(self.obtain_playbook_path(path_obj)))
            elif MODELING_RULES_DIR in path or PARSING_RULES_DIR in path:
                path = path.replace(".xif", ".yml").replace("_schema.json", ".yml")
                paths_set.add(path)
            elif PACKS_PACK_META_FILE_NAME in path:
                paths_set.add(path)
            elif self.is_pack_item(path):
                paths_set.add(self.obtain_metadata_path(path_obj))
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
        return any(
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

    def obtain_yml_from_code(self, path: str) -> str:
        """Generate a script / integration yml path from code path.

        Args:
            path (Path): the code path to generate the script / integration yml path from.

        Returns:
            Path: the yml path.
        """
        return (
            path.replace(".py", ".yml").replace(".js", ".yml").replace(".ps1", ".yml")
        )

    def obtain_metadata_path(self, path: Path) -> str:
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
        return path_str
