import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    AUTHOR_IMAGE_FILE_NAME,
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    DEPLOYMENT_JSON_FILENAME,
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
    PRIVATE_REPO_STATUS_FILE_CONFIGURATION,
    PRIVATE_REPO_STATUS_FILE_PRIVATE,
    PRIVATE_REPO_STATUS_FILE_TEST_CONF,
    RELEASE_NOTES_DIR,
    SCRIPTS_DIR,
    ExecutionMode,
    FileType,
    GitStatuses,
    MarketplaceVersions,
    PathLevel,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    chdir,
    detect_file_level,
    find_type_by_path,
    get_content_path,
    get_file_by_status,
    get_relative_path_from_packs_dir,
    is_external_repo,
    is_private_content_file,
    specify_files_from_directory,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
    _get_connector_dir,
    _is_connector_path,
)
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import (
    ContentDTO,
)
from demisto_sdk.commands.content_graph.parsers.content_item import (
    InvalidContentItemException,
    NotAContentItemException,
)


def _process_status_file(
    status_file: Path, modified_files: Set, added_files: Set, renamed_files: Set
) -> Tuple[int, int]:
    """
    Process a single status file and update file sets accordingly.

    Args:
        status_file: Path to the status file to process
        modified_files: Set of modified files to update
        added_files: Set of added files to update
        renamed_files: Set of renamed files to update

    Returns:
        Tuple of (modified_count, renamed_count)
    """
    modified_count = 0
    renamed_count = 0

    try:
        if status_file.exists():
            with open(status_file, "r") as f:
                file_statuses = DEFAULT_JSON_HANDLER.load(f)

                for file_path_str, status_info in file_statuses.items():
                    if not file_path_str:
                        continue

                    file_path = Path(file_path_str)

                    # Handle renamed files
                    if (
                        status_info.get("status") == "renamed"
                        and file_path in added_files
                    ):
                        added_files.discard(file_path)
                        old_path = status_info.get("old_path")
                        renamed_files.add((Path(old_path), file_path))  # type: ignore[arg-type]
                        renamed_count += 1
                        continue

                    # Handle modified status
                    if (
                        status_info.get("status") == "modified"
                        and file_path in added_files
                    ):
                        added_files.discard(file_path)
                        modified_files.add(file_path)
                        modified_count += 1

    except DEFAULT_JSON_HANDLER.JSONDecodeError as e:
        logger.warning(f"Invalid JSON format in {status_file}: {str(e)}")
    except Exception as e:
        logger.warning(f"Error processing {status_file}: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)

    return modified_count, renamed_count


def _log_file_changes(
    modified_files: Set, added_files: Set, renamed_files: Set
) -> None:
    """
    Log the final lists of modified, added, and renamed files.

    Args:
        modified_files: Set of modified files
        added_files: Set of added files
        renamed_files: Set of renamed files (tuples of old_path, new_path)
    """
    logger.info(
        "\n######## The final lists after union with the private repositories files:"
    )
    if modified_files:
        logger.info("\n######## Modified files:")
        for file in sorted(modified_files):
            logger.info(f"  - {file}")

    if added_files:
        logger.info("\n######## Added files:")
        for file in sorted(added_files):
            logger.info(f"  - {file}")

    if renamed_files:
        logger.info("\n######## Renamed files:")
        for renamed_tuple in sorted(
            renamed_files,
            key=lambda x: str(x[1]) if isinstance(x, tuple) else str(x),
        ):
            if isinstance(renamed_tuple, tuple) and len(renamed_tuple) == 2:
                old_path, new_path = renamed_tuple
                logger.info(f"  - {old_path} → {new_path}")
            else:
                logger.info(f"  - {renamed_tuple}")


def handle_private_repo_deleted_files(
    deleted_files: Set, show_deleted_files: bool = True
) -> Set:
    """
    Handle deleted files for private repositories by reading status files.

    Args:
        deleted_files (Set): The initial set of deleted files from git.
        show_deleted_files: if print to the logs the deleted files or not.
    Returns:
        Set: The updated set of deleted files including those from status files.
    """
    artifacts_folder = os.getenv("ARTIFACTS_FOLDER", "")
    logs_dir = Path(artifacts_folder) / "logs" if artifacts_folder else Path("logs")

    status_files = [
        logs_dir / PRIVATE_REPO_STATUS_FILE_PRIVATE,
        logs_dir / PRIVATE_REPO_STATUS_FILE_TEST_CONF,
        logs_dir / PRIVATE_REPO_STATUS_FILE_CONFIGURATION,
    ]

    for status_file in status_files:
        try:
            if status_file.exists():
                with open(status_file, "r") as f:
                    file_statuses = DEFAULT_JSON_HANDLER.load(f)
                    deleted_count = 0

                    for file_path_str, status_info in file_statuses.items():
                        if not file_path_str:
                            continue

                        file_path = Path(file_path_str)

                        # Handle deleted files
                        if status_info.get("status") == "deleted":
                            deleted_files.add(file_path)
                            deleted_count += 1

                    if deleted_count > 0:
                        logger.debug(
                            f"Current deleted files count: {len(deleted_files)}"
                        )

        except DEFAULT_JSON_HANDLER.JSONDecodeError as e:
            logger.warning(f"Invalid JSON format in {status_file}: {str(e)}")
        except Exception as e:
            logger.warning(f"Error processing {status_file}: {str(e)}")
            logger.debug("Full traceback:", exc_info=True)
            continue

    # Log files in a more readable format
    if deleted_files and show_deleted_files:
        logger.info("\n######## Deleted files:")
        for file in sorted(deleted_files):
            logger.info(f"  - {file}")

    return deleted_files


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
        handling_private_repositories: bool = False,
        private_content_path: Optional[Path] = None,
    ):
        self.staged = staged
        self.file_path = file_path
        self.committed_only = committed_only
        self.prev_ver = "master" if handling_private_repositories else prev_ver
        self.execution_mode = execution_mode
        self.handling_private_repositories = handling_private_repositories
        self.private_content_path = (
            Path(private_content_path) if private_content_path else None
        )
        self.private_content_files: set[Path] = set()

        # Set environment variable to enable private repo mode when handling private repositories
        if handling_private_repositories:
            os.environ["DEMISTO_SDK_PRIVATE_REPO_MODE"] = "true"

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
        # Skip prev_ver setup when handling private repositories - keep it as-is
        if not self.handling_private_repositories:
            if self.prev_ver and not self.prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
                self.prev_ver = f"{DEMISTO_GIT_UPSTREAM}/{self.prev_ver}"
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

        if self.private_content_path:
            (
                private_modified_files,
                private_added_files,
                private_renamed_files,
            ) = self.get_unfiltered_changed_files_from_git(self.private_content_path)
            self.private_content_files = private_modified_files.union(
                private_added_files
            ).union(private_renamed_files)

            modified_files = modified_files.union(private_modified_files)
            added_files = added_files.union(private_added_files)
            renamed_files = renamed_files.union(private_renamed_files)

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

        if self.private_content_path:
            private_git_util = GitUtil(self.private_content_path)
            private_deleted_files = private_git_util.deleted_files(
                prev_ver=self.prev_ver,
                committed_only=self.committed_only,
                staged_only=self.staged,
            )
            self.private_content_files.update(private_deleted_files)
            deleted_files = deleted_files.union(private_deleted_files)

        # Handle deleted files for private repositories
        if self.handling_private_repositories:
            deleted_files = handle_private_repo_deleted_files(deleted_files)

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

    def get_unfiltered_changed_files_from_git(
        self, repo_path: Optional[Path] = None
    ) -> Tuple[Set, Set, Set]:
        """
        Get the added and modified before file filtration to only relevant files

        Returns:
            3 sets:
            - The unfiltered modified files
            - The unfiltered added files
            - The unfiltered renamed files (Set of tuples: (old_path, new_path))
        """
        git_util = GitUtil(repo_path) if repo_path else self.git_util
        # get files from git by status identification against prev-ver
        modified_files = git_util.modified_files(
            prev_ver=self.prev_ver,
            committed_only=self.committed_only,
            staged_only=self.staged,
            debug=True,
        )
        added_files = git_util.added_files(
            prev_ver=self.prev_ver,
            committed_only=self.committed_only,
            staged_only=self.staged,
            debug=True,
        )
        renamed_files = git_util.renamed_files(
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

    def _collect_git_statuses(
        self,
        path_filter: Optional[Any] = None,
    ) -> Dict[Union[Path, Tuple[Path, Path]], Union[GitStatuses, None]]:
        """Collect git-changed files, build status dict, and optionally filter paths.

        This is the shared logic between ``get_files_using_git`` and
        ``ConnectorAwareInitializer.gather_objects_to_run_on``.

        Args:
            path_filter: Optional callable ``(Path) -> bool``.  When provided,
                only paths for which the callable returns True are kept before
                the expensive parsing step.

        Returns:
            A statuses dict ready to be passed to ``git_paths_to_basecontent_set``.
            Keys are either a single ``Path`` (for modified/added/deleted files)
            or a ``(new_path, old_path)`` tuple (for renamed files).
            Values are ``GitStatuses`` enum members or ``None`` (for implicitly
            collected items like pack_metadata.json).

            Example::

                {
                    Path("Packs/MyPack/Integrations/MyInt/MyInt.yml"): GitStatuses.MODIFIED,
                    Path("Packs/MyPack/pack_metadata.json"): None,
                    (Path("Packs/MyPack/Integrations/New/New.yml"),
                     Path("Packs/MyPack/Integrations/Old/Old.yml")): GitStatuses.RENAMED,
                    Path("connectors/salesforce/connector.yaml"): GitStatuses.ADDED,
                }
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

        # Optional early path filtering to avoid parsing irrelevant files
        if path_filter is not None:
            modified_files = {f for f in modified_files if path_filter(f)}
            added_files = {f for f in added_files if path_filter(f)}
            renamed_files = {
                (old, new) for old, new in renamed_files if path_filter(new)
            }
            deleted_files = {f for f in deleted_files if path_filter(f)}

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
        return statuses_dict_with_renamed_files_tuple

    def get_files_using_git(self) -> Tuple[Set[BaseContent], Set[Path], Set[Path]]:
        """Return all files added/changed/deleted.

        Returns:
            Tuple[Set[BaseContent], Set[Path], Set[Path]]: The sets of all the successful casts, the sets of all failed casts, and the set of non content items.
        """
        statuses_dict_with_renamed_files_tuple = self._collect_git_statuses()
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
                is_private = is_private_content_file(
                    file_path, self.private_content_path
                )
                if is_private and self.private_content_path:
                    chdir_path = self.private_content_path
                else:
                    chdir_path = Path(get_content_path())

                with chdir(chdir_path):
                    temp_obj = BaseContent.from_path(
                        path, git_sha=None, raise_on_exception=True
                    )
                    if temp_obj is None:
                        invalid_content_items.add(path)
                    else:
                        if is_private and self.private_content_path:
                            temp_obj.path_to_read = self.private_content_path / path
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

                if (
                    file_path in self.private_content_files
                    and self.private_content_path
                ):
                    chdir_path = self.private_content_path
                else:
                    chdir_path = Path(get_content_path())

                with chdir(chdir_path):
                    obj = BaseContent.from_path(
                        file_path,
                        raise_on_exception=True,
                    )
                    if obj:
                        if (
                            file_path in self.private_content_files
                            and self.private_content_path
                        ):
                            obj.path_to_read = (
                                Path(self.private_content_path) / file_path
                            )

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
                                    old_path,
                                    git_sha=prev_ver,
                                    raise_on_exception=True,
                                )
                            except (
                                NotAContentItemException,
                                InvalidContentItemException,
                            ):
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

    def handle_private_content_file(self, file):
        if is_private_content_file(file, self.private_content_path):
            if not Path(file).is_absolute():
                file = self.private_content_path / file
            self.private_content_files.add(file)

        return str(file)

    def load_files(self, files: List[str]) -> Set[Path]:
        """Recursively load all files from a given list of paths.

        This method resolves each path to determine if it belongs to the private
        content directory. If a directory exists in both the standard and
        private content locations, the files from both locations are merged.

        Args:
            files (List[str]): A list of file or directory paths (relative or absolute).

        Returns:
            Set[Path]: A unique set of Path objects for all discovered files.
                    Private files are also tracked in `self.private_content_files`.
        """
        loaded_files: Set[Path] = set()

        for file_input in files:
            resolved_file_str = self.handle_private_content_file(file_input)
            file_path = Path(resolved_file_str)

            file_level = detect_file_level(resolved_file_str)

            if file_level in {PathLevel.FILE, PathLevel.PACK}:
                loaded_files.add(file_path)
                continue

            is_in_private = self.private_content_path and file_path.is_relative_to(
                self.private_content_path
            )

            if file_path.exists() and not is_in_private:
                loaded_files.update(p for p in file_path.rglob("*") if p.is_file())

            if self.private_content_path:
                rel_path = get_relative_path_from_packs_dir(resolved_file_str)
                private_dir_obj = self.private_content_path / rel_path

                if private_dir_obj.exists():
                    private_found = {
                        p for p in private_dir_obj.rglob("*") if p.is_file()
                    }

                    loaded_files.update(private_found)
                    self.private_content_files.update(private_found)

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
            elif _is_connector_path(path):
                # Map any connector-related file (handler.yaml, capabilities.yaml, etc.)
                # to the parent connector.yaml to avoid duplicate parsing.
                connector_dir = _get_connector_dir(path)
                paths_set.add(connector_dir / "connector.yaml")
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
        # A path is related if it's under Packs/ or connectors/
        is_content_path = "Packs" in path or "connectors" in path
        if not is_content_path:
            return True
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
                PACKS_VERSION_CONFIG_FILE_NAME,
                DEPLOYMENT_JSON_FILENAME,
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
        return path.suffix in (".py", ".js", ".ps1") and not any(
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


class ConnectorAwareInitializer(Initializer):
    """Extends Initializer with connector-integration cross-discovery.

    When ``--run-connectors-validation`` is used, this initializer replaces the
    standard ``Initializer``.  It:

    1. Runs the normal file-collection flow (supports ``-g``, ``-i``, ``-a``).
    2. Filters the result to only ``Integration`` and ``Connector`` objects.
    3. Applies marketplace / XSOAR-handler filters.
    4. Cross-matches connectors and integrations and expands with missing counterparts.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @staticmethod
    def _is_relevant_path(path: Path) -> bool:
        """Return True if the path is an Integration or Connector item."""
        path_str = str(path)
        return (
            f"/{INTEGRATIONS_DIR}/" in path_str
            or path_str.startswith(f"{INTEGRATIONS_DIR}/")
            or "connectors/" in path_str
        )

    def gather_objects_to_run_on(self) -> Tuple[Set[BaseContent], Set[Path]]:
        """Collect, filter, and cross-match connector and integration objects.

        Overrides the parent ``Initializer.gather_objects_to_run_on`` to:

        1. **Collect** — Use the standard file-collection flow (``-g``, ``-i``,
           or ``-a``) but pre-filter to only Integration and Connector paths
           via ``_is_relevant_path``.
        2. **Post-filter** — Keep only ``Integration`` objects that are in the
           PLATFORM marketplace and not deprecated, and ``Connector`` objects
           that have at least one XSOAR handler.
        3. **Cross-match** — Call ``_cross_match_and_expand`` to link each
           XSOAR handler to its referenced integration (and vice versa),
           expanding with graph-discovered counterparts when needed.

        Returns:
            Tuple of:
            - ``Set[BaseContent]``: The filtered set of ``Integration`` and
              ``Connector`` objects with cross-links populated
              (``handler.related_integration`` and ``integration.related_content``).
            - ``Set[Path]``: Paths that could not be parsed into valid content items.
        """
        # 1. Collect and parse only relevant paths (Integrations + connectors)
        if self.execution_mode == ExecutionMode.USE_GIT:
            statuses = self._collect_git_statuses(path_filter=self._is_relevant_path)
            all_objects, invalid_items, _ = self.git_paths_to_basecontent_set(
                statuses, prev_ver=self.prev_ver
            )
        elif self.execution_mode == ExecutionMode.SPECIFIC_FILES:
            loaded = self.load_files(self.file_path.split(","))
            filtered_paths = {p for p in loaded if self._is_relevant_path(p)}
            all_objects, invalid_items, _ = self.paths_to_basecontent_set(
                filtered_paths
            )
        else:
            # ALL_FILES or fallback -- use parent as-is
            all_objects, invalid_items = super().gather_objects_to_run_on()

        # 2. Post-filter: keep only Integration and Connector objects
        filtered_integrations: Set[Integration] = set()
        filtered_connectors: Set[Connector] = set()
        for obj in all_objects:
            if isinstance(obj, Integration):
                if obj.deprecated:
                    logger.debug(
                        f"Skipping integration '{obj.object_id}' -- deprecated."
                    )
                elif MarketplaceVersions.PLATFORM in obj.marketplaces:
                    filtered_integrations.add(obj)
                else:
                    logger.debug(
                        f"Skipping integration '{obj.object_id}' -- "
                        f"not in PLATFORM marketplace."
                    )
            elif isinstance(obj, Connector):
                if obj.xsoar_handlers:
                    filtered_connectors.add(obj)
                else:
                    logger.debug(
                        f"Skipping connector '{obj.object_id}' -- "
                        f"no XSOAR handlers."
                    )

        # 3. Cross-match and expand with missing counterparts
        filtered = self._cross_match_and_expand(
            filtered_integrations, filtered_connectors
        )

        return filtered, invalid_items

    def _cross_match_and_expand(
        self, integrations: Set[Integration], connectors: Set[Connector]
    ) -> Set[BaseContent]:
        """Orchestrate the 4-phase handler-integration cross-matching.

        Each XSOAR handler inside a ``Connector`` references an integration via
        its ``xsoar_integration_id`` field.  This method resolves those references
        and sets bidirectional cross-links:

        * ``handler.related_integration`` — the ``Integration`` object (1:1).
        * ``integration.related_content`` — the handler back-reference (1:1).

        **Phases**:

        1. *Direct match* — pair handlers with integrations already in the
           working set (no graph access needed).
        2. *Graph-expand connectors* — for integrations that had no handler in
           the working set, search the content graph for connectors that
           reference them and add those connectors.
        3. *Graph-expand integrations* — for handlers that still have no
           integration after phase 2a, search the graph for the referenced
           integration and add it.
        4. *Cleanup* — remove integrations that remain unmatched after all
           expansion phases.

        Example flow::

            Input:  integrations={A, B}, connectors={C1(handler→A)}
            Phase 1:  A ↔ C1.handler  (direct match)
            Phase 2a: B has no handler → graph finds C2(handler→B) → add C2
            Phase 2b: (nothing left unmatched)
            Cleanup:  (nothing to remove)
            Output: {A, B, C1, C2}

        Args:
            integrations: Mutable set of ``Integration`` objects to match and
                potentially expand with graph-discovered integrations.
            connectors: Mutable set of ``Connector`` objects to match and
                potentially expand with graph-discovered connectors.

        Returns:
            The union ``integrations | connectors`` with all cross-links set.
        """
        # Phase 1: Direct matching
        matched_ids, matched_keys = self._direct_match(integrations, connectors)

        # Early exit if everything matched
        unmatched_integrations = {
            i for i in integrations if i.object_id not in matched_ids
        }
        unmatched_handlers = [
            (c, h)
            for c in connectors
            for h in c.xsoar_handlers
            if h.xsoar_integration_id and f"{c.object_id}::{h.id}" not in matched_keys
        ]

        if not unmatched_integrations and not unmatched_handlers:
            logger.debug(
                "All handlers and integrations matched directly, skipping graph."
            )
            return integrations | connectors

        # Phase 2a: Find connectors for unmatched integrations via graph
        self._graph_expand_connectors(unmatched_integrations, connectors, matched_ids)

        # Phase 2b: Find integrations for still-unmatched handlers via graph
        self._graph_expand_integrations(connectors, integrations)

        # Cleanup: Drop integrations that never found a handler
        self._remove_unmatched_integrations(integrations)

        return integrations | connectors

    def _direct_match(
        self, integrations: Set[Integration], connectors: Set[Connector]
    ) -> Tuple[Set[str], Set[str]]:
        """Phase 1: Match handlers to integrations already in the working set.

        For each XSOAR handler that declares an ``xsoar_integration_id``, look
        up the integration in the current *integrations* set.  If found, set the
        bidirectional cross-links:

        * ``handler.related_integration = integration``
        * ``integration.related_content = handler``

        Args:
            integrations: The current set of ``Integration`` objects.
            connectors: The current set of ``Connector`` objects whose handlers
                will be inspected.

        Returns:
            A tuple of ``(matched_integration_ids, matched_handler_keys)`` where
            *matched_integration_ids* contains the ``object_id`` of every
            integration that was paired, and *matched_handler_keys* contains
            composite keys of the form ``"connector_id::handler_id"`` for every
            handler that was paired.
        """
        integration_by_id: Dict[str, Integration] = {
            i.object_id: i for i in integrations
        }

        matched_integration_ids: Set[str] = set()
        matched_handler_keys: Set[str] = set()  # "connector_id::handler_id"

        for connector in connectors:
            for handler in connector.xsoar_handlers:
                int_id = handler.xsoar_integration_id
                if not int_id:
                    continue
                match = integration_by_id.get(int_id)
                if match:
                    handler.related_integration = match
                    match.related_content = handler
                    matched_integration_ids.add(match.object_id)
                    matched_handler_keys.add(f"{connector.object_id}::{handler.id}")
                    logger.debug(
                        f"Matched handler '{handler.id}' (connector "
                        f"'{connector.object_id}') -> integration "
                        f"'{match.object_id}' (direct)."
                    )

        return matched_integration_ids, matched_handler_keys

    def _graph_expand_connectors(
        self,
        unmatched_integrations: Set[Integration],
        connectors: Set[Connector],
        matched_ids: Set[str],
    ) -> None:
        """Phase 2a: Find connectors for integrations that had no direct match.

        For each unmatched integration, search the content graph for connectors
        whose XSOAR handlers reference it.  Found connectors are added to the
        *connectors* set in-place and their handlers are linked to the
        integration.

        Args:
            unmatched_integrations: Integrations from the working set that were
                not paired during Phase 1.
            connectors: Mutable set of connectors — new graph-discovered
                connectors are added here.
            matched_ids: Mutable set of matched integration IDs — updated when
                a graph-discovered connector matches an integration.
        """
        if not unmatched_integrations:
            return

        logger.debug(
            f"Searching graph for connectors referencing unmatched "
            f"integrations: {[i.object_id for i in unmatched_integrations]}"
        )
        existing_connector_ids = {c.object_id for c in connectors}
        for integration in list(unmatched_integrations):
            found_connectors = self._graph_search_connectors(integration.object_id)
            for found_connector in found_connectors:
                if not isinstance(found_connector, Connector):
                    continue
                if found_connector.object_id in existing_connector_ids:
                    continue
                if not found_connector.xsoar_handlers:
                    continue
                for handler in found_connector.xsoar_handlers:
                    if handler.xsoar_integration_id == integration.object_id:
                        handler.related_integration = integration
                        integration.related_content = handler
                        matched_ids.add(integration.object_id)
                        logger.debug(
                            f"Matched handler '{handler.id}' (connector "
                            f"'{found_connector.object_id}') -> integration "
                            f"'{integration.object_id}' (graph)."
                        )
                connectors.add(found_connector)
                existing_connector_ids.add(found_connector.object_id)

    def _graph_expand_integrations(
        self, connectors: Set[Connector], integrations: Set[Integration]
    ) -> None:
        """Phase 2b: Find integrations for handlers that still have no match.

        After Phase 2a, recalculate which handlers are still unmatched.  For
        each, search the content graph for the referenced integration.  Skip
        deprecated integrations and those not in the ``PLATFORM`` marketplace.

        Found integrations are added to the *integrations* set in-place and
        linked to their handler.

        Args:
            connectors: The (possibly expanded) set of connectors whose
                unmatched handlers will be inspected.
            integrations: Mutable set of integrations — new graph-discovered
                integrations are added here.
        """
        unmatched_handlers = [
            (c, h)
            for c in connectors
            for h in c.xsoar_handlers
            if h.xsoar_integration_id and h.related_integration is None
        ]
        if not unmatched_handlers:
            return

        logger.debug(
            f"Searching graph for integrations referenced by unmatched "
            f"handlers: {[(c.object_id, h.id) for c, h in unmatched_handlers]}"
        )
        for connector, handler in unmatched_handlers:
            int_id = handler.xsoar_integration_id
            if not int_id:
                continue
            results = self._graph_search_integration(int_id)
            if results:
                integration = results[0]
                if getattr(integration, "deprecated", False):
                    logger.debug(
                        f"Skipping graph-found integration "
                        f"'{integration.object_id}' -- deprecated."
                    )
                    continue
                if hasattr(integration, "marketplaces") and (
                    MarketplaceVersions.PLATFORM not in integration.marketplaces
                ):
                    logger.debug(
                        f"Skipping graph-found integration "
                        f"'{integration.object_id}' -- not PLATFORM."
                    )
                    continue
                handler.related_integration = integration
                if hasattr(integration, "related_content"):
                    integration.related_content = handler
                integrations.add(integration)
                logger.debug(
                    f"Matched handler '{handler.id}' (connector "
                    f"'{connector.object_id}') -> integration "
                    f"'{integration.object_id}' (graph)."
                )

    @staticmethod
    def _remove_unmatched_integrations(integrations: Set[Integration]) -> None:
        """Cleanup: Remove integrations that have no matching connector handler.

        After all matching phases, any integration whose ``related_content`` is
        ``None`` has no connector handler pointing to it and should be excluded
        from the validation set.

        Args:
            integrations: Mutable set of integrations — unmatched entries are
                removed in-place.
        """
        unmatched_final = {i for i in integrations if i.related_content is None}
        if unmatched_final:
            logger.debug(
                f"Removing {len(unmatched_final)} integration(s) with no matching "
                f"connector handler: {[i.object_id for i in unmatched_final]}"
            )
            integrations -= unmatched_final

    @staticmethod
    def _graph_search_integration(integration_id: str) -> List[Any]:
        """Graph search for an integration by object_id or name."""
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.validate.validators.base_validator import (
            BaseValidator,
        )

        graph = BaseValidator.graph_interface
        if not graph:
            logger.debug("Graph interface not available, skipping graph search.")
            return []
        results = graph.search(
            content_type=ContentType.INTEGRATION,
            object_id=integration_id,
        )
        if not results:
            results = graph.search(
                content_type=ContentType.INTEGRATION,
                name=integration_id,
            )
        return results

    @staticmethod
    def _graph_search_connectors(integration_id: str) -> List[Any]:
        """Graph search for connectors whose XSOAR handlers reference the given integration.

        Searches all connectors in the graph and filters to those with at least
        one XSOAR handler whose ``xsoar_integration_id`` matches.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.validate.validators.base_validator import (
            BaseValidator,
        )

        graph = BaseValidator.graph_interface
        if not graph:
            logger.debug("Graph interface not available, skipping connector search.")
            return []
        all_connectors = graph.search(content_type=ContentType.CONNECTOR)
        return [
            c
            for c in all_connectors
            if hasattr(c, "xsoar_handlers")
            and any(h.xsoar_integration_id == integration_id for h in c.xsoar_handlers)
        ]
