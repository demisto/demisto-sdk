import os
from typing import Optional, Set, Tuple

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    PACKS_DIR,
    PACKS_PACK_META_FILE_NAME,
    VALIDATION_USING_GIT_IGNORABLE_DATA,
    FileType,
    PathLevel,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    detect_file_level,
    find_type,
    get_file,
    get_file_by_status,
    get_pack_ignore_content,
    get_pack_name,
    get_relative_path_from_packs_dir,
    specify_files_from_directory,
)
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult


class GitInitializer:
    def __init__(
        self,
        use_git=None,
        staged=None,
        skip_docker_checks=None,
        is_backward_check=None,
        skip_dependencies=None,
        skip_pack_rn_validation=None,
        is_circle=None,
        handle_error=None,
        is_external_repo=None,
        debug_git=None,
        include_untracked=None,
        print_ignored_files=None,
    ):
        self.staged = staged
        self.use_git = use_git
        self.skip_docker_checks = skip_docker_checks
        self.is_backward_check = is_backward_check
        self.skip_dependencies = skip_dependencies
        self.skip_pack_rn_validation = skip_pack_rn_validation
        self.is_circle = is_circle
        self.handle_error = handle_error
        self.is_external_repo = is_external_repo
        self.debug_git = debug_git
        self.include_untracked = include_untracked
        self.ignored_files = set()
        self.print_ignored_files = print_ignored_files
        self.new_packs = set()

    def validate_git_installed(self):
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
        """Setting up the prev_ver parameter"""
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

    def set_prev_ver(self, prev_ver):
        if prev_ver and not prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
            self.prev_ver = self.setup_prev_ver(f"{DEMISTO_GIT_UPSTREAM}/" + prev_ver)
        else:
            self.prev_ver = self.setup_prev_ver(prev_ver)

    def collect_files_to_run(self, file_path):

        (
            modified_files,
            added_files,
            changed_meta_files,
            old_format_files,
            valid_types,
        ) = self.get_changed_files_from_git()

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
            include_untracked=self.include_untracked,
        )

        return (
            modified_files,
            added_files,
            changed_meta_files,
            old_format_files,
            valid_types,
            deleted_files,
        )

    def setup_git_params(self):
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
            self.skip_pack_rn_validation = True
            error_message, error_code = Errors.running_on_master_with_git()
            if self.handle_error:
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path="General",
                    warning=(not self.is_external_repo or self.is_circle),
                    drop_line=True,
                ):
                    return False
            else:
                return ValidationResult(
                error_code="BA107", is_valid=False, message="Running on master branch while using git is ill advised.\nrun: 'git checkout -b NEW_BRANCH_NAME' and rerun the command.",
                file_path=""
                )
        if self.handle_error:
            return True
        else:
            return ValidationResult(
            error_code="BA107", is_valid=True, message="", file_path=""
            )

    def print_git_config(self):
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

        if self.skip_pack_rn_validation:
            logger.info("Skipping release notes validation")

        if self.skip_docker_checks:
            logger.info("Skipping Docker checks")

        if not self.is_backward_check:
            logger.info("Skipping backwards compatibility checks")

        if self.skip_dependencies:
            logger.info("Skipping pack dependencies check")

    def get_changed_files_from_git(self) -> Tuple[Set, Set, Set, Set, bool]:
        """Get the added and modified after file filtration to only relevant files for validate

        Returns:
            - The filtered modified files (including the renamed files)
            - The filtered added files
            - The changed metadata files
            - The modified old-format files (legacy unified python files)
            - Boolean flag that indicates whether all file types are supported
        """

        (
            modified_files,
            added_files,
            renamed_files,
        ) = self.get_unfiltered_changed_files_from_git()

        # filter files only to relevant files
        filtered_modified, old_format_files, _ = self.filter_to_relevant_files(
            modified_files
        )
        filtered_renamed, _, valid_types_renamed = self.filter_to_relevant_files(
            renamed_files
        )
        filtered_modified = filtered_modified.union(filtered_renamed)

        (
            filtered_added,
            old_format_added,
            valid_types_added,
        ) = self.filter_to_relevant_files(added_files)
        old_format_files |= old_format_added

        valid_types = all((valid_types_added, valid_types_renamed))

        # extract metadata files from the recognised changes
        changed_meta = self.pack_metadata_extraction(
            modified_files, added_files, renamed_files
        )
        filtered_changed_meta, old_format_changed, _ = self.filter_to_relevant_files(
            changed_meta, check_metadata_files=True
        )
        old_format_files |= old_format_changed
        return (
            filtered_modified,
            filtered_added,
            filtered_changed_meta,
            old_format_files,
            valid_types,
        )

    """ ######################################## Git Tools and filtering ####################################### """

    def pack_metadata_extraction(self, modified_files, added_files, renamed_files):
        """Extract pack metadata files from the modified and added files

        Return all modified metadata file paths
        and get all newly added packs from the added metadata files."""
        changed_metadata_files = set()
        for path in modified_files.union(renamed_files):
            file_path = str(path[1]) if isinstance(path, tuple) else str(path)

            if file_path.endswith(PACKS_PACK_META_FILE_NAME):
                changed_metadata_files.add(file_path)

        for path in added_files:
            if str(path).endswith(PACKS_PACK_META_FILE_NAME):
                self.new_packs.add(get_pack_name(str(path)))

        return changed_metadata_files

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
            debug=self.debug_git,
            include_untracked=self.include_untracked,
        )
        added_files = self.git_util.added_files(
            prev_ver=self.prev_ver,
            committed_only=self.is_circle,
            staged_only=self.staged,
            debug=self.debug_git,
            include_untracked=self.include_untracked,
        )
        renamed_files = self.git_util.renamed_files(
            prev_ver=self.prev_ver,
            committed_only=self.is_circle,
            staged_only=self.staged,
            debug=self.debug_git,
            include_untracked=self.include_untracked,
            get_only_current_file_names=True,
        )

        return modified_files, added_files, renamed_files

    def filter_to_relevant_files(self, file_set, check_metadata_files=False):
        """Goes over file set and returns only a filtered set of only files relevant for validation"""
        filtered_set: set = set()
        old_format_files: set = set()
        valid_types: set = set()
        for path in file_set:
            old_path = None
            if isinstance(path, tuple):
                file_path = str(path[1])
                old_path = str(path[0])

            else:
                file_path = str(path)

            try:
                (
                    formatted_path,
                    old_path,
                    valid_file_extension,
                ) = self.check_file_relevance_and_format_path(
                    file_path,
                    old_path,
                    old_format_files,
                    check_metadata_files=check_metadata_files,
                )
                valid_types.add(valid_file_extension)
                if formatted_path:
                    if old_path:
                        filtered_set.add((old_path, formatted_path))
                    else:
                        filtered_set.add(formatted_path)

            # handle a case where a file was deleted locally though recognised as added against master.
            except FileNotFoundError:
                if file_path not in self.ignored_files:
                    if self.print_ignored_files:
                        logger.info(f"[yellow]ignoring file {file_path}[/yellow]")
                    self.ignored_files.add(file_path)

        return filtered_set, old_format_files, all(valid_types)

    def check_file_relevance_and_format_path(
        self, file_path, old_path, old_format_files, check_metadata_files=False
    ):
        """
        Determines if a file is relevant for validation and create any modification to the file_path if needed
        :returns a tuple(string, string, bool) where
            - the first element is the path of the file that should be returned, if the file isn't relevant then returns an empty string
            - the second element is the old path in case the file was renamed, if the file wasn't renamed then return an empty string
            - true if the file type is supported OR file type is not supported, but should be ignored, false otherwise
        """
        irrelevant_file_output = "", "", True
        if file_path.split(os.path.sep)[0] in (
            ".gitlab",
            ".circleci",
            ".github",
            ".devcontainer",
            ".vscode",
        ):
            return irrelevant_file_output

        file_type = find_type(file_path)

        if file_type == FileType.CONF_JSON:
            return file_path, "", True

        if file_type == FileType.VULTURE_WHITELIST:
            return irrelevant_file_output

        if self.ignore_files_irrelevant_for_validation(
            file_path, check_metadata_files=check_metadata_files
        ):
            return irrelevant_file_output

        if not self.is_valid_file_type(
            file_type, file_path, get_pack_ignore_content(get_pack_name(file_path))
        ):
            return "", "", False

        # redirect non-test code files to the associated yml file
        if file_type in [
            FileType.PYTHON_FILE,
            FileType.POWERSHELL_FILE,
            FileType.JAVASCRIPT_FILE,
            FileType.XIF_FILE,
            FileType.MODELING_RULE_XIF,
            FileType.PARSING_RULE_XIF,
        ]:
            if not (
                str(file_path).endswith("_test.py")
                or str(file_path).endswith(".Tests.ps1")
                or str(file_path).endswith("_test.js")
            ):
                file_path = (
                    file_path.replace(".py", ".yml")
                    .replace(".ps1", ".yml")
                    .replace(".js", ".yml")
                    .replace(".xif", ".yml")
                )

                if old_path:
                    old_path = (
                        old_path.replace(".py", ".yml")
                        .replace(".ps1", ".yml")
                        .replace(".js", ".yml")
                        .replace(".xif", ".yml")
                    )
            else:
                return irrelevant_file_output

        if file_type == FileType.XDRC_TEMPLATE_YML:
            file_path = file_path.replace(".yml", ".json")

            if old_path:
                old_path = old_path.replace(".yml", ".json")

        # redirect schema file when updating release notes
        if file_type == FileType.MODELING_RULE_SCHEMA:
            file_path = file_path.replace("_schema", "").replace(".json", ".yml")

            if old_path:
                old_path = old_path.replace("_schema", "").replace(".json", ".yml")

        # redirect _testdata.json file to the associated yml file
        if file_type == FileType.MODELING_RULE_TEST_DATA:
            file_path = file_path.replace("_testdata.json", ".yml")

            if old_path:
                old_path = old_path.replace("_testdata.json", ".yml")

        # check for old file format
        if self.is_old_file_format(file_path, file_type):
            old_format_files.add(file_path)
            return irrelevant_file_output

        # if renamed file - return a tuple
        if old_path:
            return file_path, old_path, True

        # else return the file path
        else:
            return file_path, "", True

    def ignore_files_irrelevant_for_validation(
        self, file_path: str, check_metadata_files: bool = False
    ) -> bool:
        """
        Will ignore files that are not in the packs directory, are .txt files or are in the
        VALIDATION_USING_GIT_IGNORABLE_DATA tuple.

        Args:
            file_path: path of file to check if should be ignored.
            check_metadata_files: If True will not ignore metadata files.
        Returns: True if file is ignored, false otherwise
        """

        if PACKS_DIR not in file_path:
            self.ignore_file(file_path)
            return True

        if check_metadata_files and find_type(file_path) == FileType.METADATA:
            return False

        if file_path.endswith(".txt"):
            self.ignore_file(file_path)
            return True

        if any(name in str(file_path) for name in VALIDATION_USING_GIT_IGNORABLE_DATA):
            self.ignore_file(file_path)
            return True
        return False

    def ignore_file(self, file_path: str) -> None:
        if self.print_ignored_files:
            logger.info(f"[yellow]ignoring file {file_path}[/yellow]")
        self.ignored_files.add(file_path)

    """ ######################################## Validate Tools ############################################### """

    @staticmethod
    def is_old_file_format(file_path: str, file_type: FileType):
        if file_type not in {FileType.INTEGRATION, FileType.SCRIPT}:
            return False
        file_yml = get_file(file_path)
        # check for unified integration
        if file_type == FileType.INTEGRATION and file_yml.get("script", {}).get(
            "script", "-"
        ) not in ["-", ""]:
            if file_yml.get("script", {}).get("type", "javascript") != "python":
                return False
            return True

        # check for unified script
        if file_type == FileType.SCRIPT and file_yml.get("script", "-") not in [
            "-",
            "",
        ]:
            if file_yml.get("type", "javascript") != "python":
                return False
            return True
        return False

    @error_codes("BA102,IM110")
    def is_valid_file_type(
        self, file_type: FileType, file_path: str, ignored_errors: dict
    ):
        """
        If a file_type is unsupported, will return `False`.
        """
        if not file_type:
            error_message, error_code = Errors.file_type_not_supported(
                file_type, file_path
            )
            if str(file_path).endswith(".png"):
                error_message, error_code = Errors.invalid_image_name_or_location()
            if self.handle_error:
                if self.handle_error(
                    error_message=error_message,
                    error_code=error_code,
                    file_path=file_path,
                    drop_line=True,
                    ignored_errors=ignored_errors,
                ):
                    return False
            else:
                # to implement: create a validation result version
                return False

        return True

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
