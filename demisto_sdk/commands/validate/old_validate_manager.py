import os
from concurrent.futures._base import Future, as_completed
from configparser import ConfigParser
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

import pebble
from git import GitCommandError, InvalidGitRepositoryError
from packaging import version

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    AUTHOR_IMAGE_FILE_NAME,
    CONTENT_ENTITIES_DIRS,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    GENERIC_FIELDS_DIR,
    GENERIC_TYPES_DIR,
    IGNORED_PACK_NAMES,
    LISTS_DIR,
    LOG_FILE_NAME,
    OLDEST_SUPPORTED_VERSION,
    PACK_METADATA_REQUIRE_RN_FIELDS,
    PACKS_DIR,
    PACKS_PACK_META_FILE_NAME,
    SKIP_RELEASE_NOTES_FOR_TYPES,
    VALIDATION_USING_GIT_IGNORABLE_DATA,
    XSIAM_DASHBOARDS_DIR,
    FileType,
    FileType_ALLOWED_TO_DELETE,
    PathLevel,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.content_constant_paths import (
    CONTENT_PATH,
    DEFAULT_ID_SET_PATH,
)
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.errors import (
    FOUND_FILES_AND_ERRORS,
    FOUND_FILES_AND_IGNORED_ERRORS,
    PRESET_ERROR_TO_CHECK,
    PRESET_ERROR_TO_IGNORE,
    Errors,
    get_all_error_codes,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.author_image import (
    AuthorImageValidator,
)
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.hook_validations.classifier import ClassifierValidator
from demisto_sdk.commands.common.hook_validations.conf_json import ConfJsonValidator
from demisto_sdk.commands.common.hook_validations.correlation_rule import (
    CorrelationRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.dashboard import DashboardValidator
from demisto_sdk.commands.common.hook_validations.deprecation import (
    DeprecationValidator,
)
from demisto_sdk.commands.common.hook_validations.description import (
    DescriptionValidator,
)
from demisto_sdk.commands.common.hook_validations.generic_definition import (
    GenericDefinitionValidator,
)
from demisto_sdk.commands.common.hook_validations.generic_field import (
    GenericFieldValidator,
)
from demisto_sdk.commands.common.hook_validations.generic_module import (
    GenericModuleValidator,
)
from demisto_sdk.commands.common.hook_validations.generic_type import (
    GenericTypeValidator,
)
from demisto_sdk.commands.common.hook_validations.graph_validator import GraphValidator
from demisto_sdk.commands.common.hook_validations.id import IDSetValidations
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.incident_field import (
    IncidentFieldValidator,
)
from demisto_sdk.commands.common.hook_validations.incident_type import (
    IncidentTypeValidator,
)
from demisto_sdk.commands.common.hook_validations.indicator_field import (
    IndicatorFieldValidator,
)
from demisto_sdk.commands.common.hook_validations.integration import (
    IntegrationValidator,
)
from demisto_sdk.commands.common.hook_validations.job import JobValidator
from demisto_sdk.commands.common.hook_validations.layout import (
    LayoutsContainerValidator,
    LayoutValidator,
)
from demisto_sdk.commands.common.hook_validations.layout_rule import LayoutRuleValidator
from demisto_sdk.commands.common.hook_validations.lists import ListsValidator
from demisto_sdk.commands.common.hook_validations.mapper import MapperValidator
from demisto_sdk.commands.common.hook_validations.modeling_rule import (
    ModelingRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.pack_unique_files import (
    PackUniqueFilesValidator,
)
from demisto_sdk.commands.common.hook_validations.parsing_rule import (
    ParsingRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator
from demisto_sdk.commands.common.hook_validations.pre_process_rule import (
    PreProcessRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.python_file import PythonFileValidator
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.hook_validations.release_notes import (
    ReleaseNotesValidator,
)
from demisto_sdk.commands.common.hook_validations.release_notes_config import (
    ReleaseNotesConfigValidator,
)
from demisto_sdk.commands.common.hook_validations.report import ReportValidator
from demisto_sdk.commands.common.hook_validations.reputation import ReputationValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.hook_validations.test_playbook import (
    TestPlaybookValidator,
)
from demisto_sdk.commands.common.hook_validations.triggers import TriggersValidator
from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator
from demisto_sdk.commands.common.hook_validations.wizard import WizardValidator
from demisto_sdk.commands.common.hook_validations.xdrc_templates import (
    XDRCTemplatesValidator,
)
from demisto_sdk.commands.common.hook_validations.xsiam_dashboard import (
    XSIAMDashboardValidator,
)
from demisto_sdk.commands.common.hook_validations.xsiam_report import (
    XSIAMReportValidator,
)
from demisto_sdk.commands.common.hook_validations.xsoar_config_json import (
    XSOARConfigJsonValidator,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    _get_file_id,
    detect_file_level,
    find_type,
    get_api_module_dependencies_from_graph,
    get_api_module_ids,
    get_file,
    get_file_by_status,
    get_pack_ignore_content,
    get_pack_name,
    get_pack_names_from_files,
    get_relative_path_from_packs_dir,
    get_remote_file,
    get_yaml,
    is_file_in_pack,
    open_id_set_file,
    run_command_os,
    specify_files_from_directory,
)
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator

SKIPPED_FILES = [
    "CommonServerUserPython.py",
    "demistomock.py",
    "DemistoClassApiModule.py",
]


class OldValidateManager:
    def __init__(
        self,
        is_backward_check=True,
        prev_ver=None,
        use_git=False,
        only_committed_files=False,
        print_ignored_files=False,
        skip_conf_json=True,
        validate_graph=False,
        validate_id_set=False,
        file_path=None,
        validate_all=False,
        is_external_repo=False,
        skip_pack_rn_validation=False,
        print_ignored_errors=False,
        silence_init_prints=False,
        no_docker_checks=False,
        skip_dependencies=False,
        id_set_path=None,
        staged=False,
        create_id_set=False,
        json_file_path=None,
        skip_schema_check=False,
        debug_git=False,
        include_untracked=False,
        pykwalify_logs=False,
        check_is_unskipped=True,
        quiet_bc=False,
        multiprocessing=True,
        specific_validations=None,
    ):
        # General configuration
        self.skip_docker_checks = False
        self.no_configuration_prints = silence_init_prints
        self.skip_conf_json = skip_conf_json
        self.is_backward_check = is_backward_check
        self.is_circle = only_committed_files
        self.validate_all = validate_all
        self.use_git = use_git
        self.skip_pack_rn_validation = skip_pack_rn_validation
        self.print_ignored_files = print_ignored_files
        self.print_ignored_errors = print_ignored_errors
        self.skip_dependencies = skip_dependencies or not use_git
        self.skip_id_set_creation = not create_id_set or skip_dependencies
        self.validate_graph = validate_graph
        self.compare_type = "..."
        self.staged = staged
        self.skip_schema_check = skip_schema_check
        self.debug_git = debug_git
        self.include_untracked = include_untracked
        self.pykwalify_logs = pykwalify_logs
        self.quiet_bc = quiet_bc
        self.check_is_unskipped = check_is_unskipped
        self.conf_json_data = {}
        self.run_with_multiprocessing = multiprocessing
        self.packs_with_mp_change = set()
        self.is_possible_validate_readme = (
            self.is_node_exist() or ReadMeValidator.is_docker_available()
        )

        if json_file_path:
            self.json_file_path = (
                os.path.join(json_file_path, "validate_outputs.json")
                if os.path.isdir(json_file_path)
                else json_file_path
            )
        else:
            self.json_file_path = ""

        self.specific_validations = specific_validations
        if specific_validations:
            self.specific_validations = specific_validations.split(",")

        # Class constants
        self.handle_error = BaseValidator(json_file_path=json_file_path).handle_error
        self.should_run_validation = BaseValidator(
            specific_validations=specific_validations
        ).should_run_validation
        self.file_path = file_path
        self.id_set_path = id_set_path or DEFAULT_ID_SET_PATH
        # create the id_set only once per run.
        self.id_set_file = self.get_id_set_file(
            self.skip_id_set_creation, self.id_set_path
        )

        self.id_set_validations = (
            IDSetValidations(
                is_circle=self.is_circle,
                configuration=Configuration(),
                ignored_errors=None,
                id_set_file=self.id_set_file,
                json_file_path=json_file_path,
                specific_validations=self.specific_validations,
            )
            if validate_id_set
            else None
        )

        self.deprecation_validator = DeprecationValidator(id_set_file=self.id_set_file)

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

        if prev_ver and not prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
            self.prev_ver = self.setup_prev_ver(f"{DEMISTO_GIT_UPSTREAM}/" + prev_ver)
        else:
            self.prev_ver = self.setup_prev_ver(prev_ver)

        self.check_only_schema = False
        self.always_valid = False
        self.ignored_files = set()
        self.new_packs = set()
        self.skipped_file_types = (
            FileType.CHANGELOG,
            FileType.DOC_IMAGE,
            FileType.MODELING_RULE_SCHEMA,
            FileType.XSIAM_REPORT_IMAGE,
            FileType.PIPFILE,
            FileType.PIPFILE_LOCK,
            FileType.TXT,
            FileType.JAVASCRIPT_FILE,
            FileType.POWERSHELL_FILE,
            FileType.PYLINTRC,
            FileType.SECRET_IGNORE,
            FileType.LICENSE,
            FileType.UNIFIED_YML,
            FileType.PACK_IGNORE,
            FileType.INI,
            FileType.PEM,
            FileType.METADATA,
            FileType.VULTURE_WHITELIST,
            FileType.CASE_LAYOUT_RULE,
            FileType.CASE_LAYOUT,
            FileType.CASE_FIELD,
            FileType.AGENTIX_ACTION,
            FileType.AGENTIX_AGENT,
        )

        self.is_external_repo = is_external_repo
        if is_external_repo:
            if not self.no_configuration_prints:
                logger.info("Running in a private repository")
            self.skip_conf_json = True

        self.print_percent = False
        self.completion_percentage = 0

        if validate_all:
            # No need to check docker images on build branch hence we do not check on -a mode
            # also do not skip id set creation unless the flag is up
            self.skip_docker_checks = True
            self.skip_pack_rn_validation = True
            self.print_percent = (
                not self.run_with_multiprocessing
            )  # the Multiprocessing will mismatch the percent
            self.check_is_unskipped = False

        if no_docker_checks:
            self.skip_docker_checks = True

        if self.skip_conf_json:
            self.check_is_unskipped = False

        if not self.skip_conf_json:
            self.conf_json_validator = ConfJsonValidator(
                specific_validations=self.specific_validations
            )
            self.conf_json_data = self.conf_json_validator.conf_data

    def is_node_exist(self) -> bool:
        """Check if node interpreter exists.
        Returns:
            bool: True if node exist, else False
        """
        # Check node exist
        content_path = CONTENT_PATH
        stdout, stderr, exit_code = run_command_os("node -v", cwd=content_path)  # type: ignore
        if exit_code:
            return False
        return True

    def print_final_report(self, valid):
        if self.print_ignored_errors:
            self.print_ignored_files_report()
            self.print_ignored_errors_report()

        if valid:
            logger.info("\n<green>The files are valid</green>")
            return 0

        else:
            all_failing_files = "\n".join(set(FOUND_FILES_AND_ERRORS))
            logger.info(
                f"\n<red>=========== Found errors in the following files ===========\n\n{all_failing_files}</red>\n"
            )

            if self.always_valid:
                logger.info(
                    "<yellow>Found the errors above, but not failing build</yellow>"
                )
                return 0

            logger.info(
                "<red>The files were found as invalid, the exact error message can be located above</red>"
            )
            return 1

    def run_validation(self):
        """Initiates validation in accordance with mode (i,g,a)"""
        if self.validate_all:
            is_valid = self.run_validation_on_all_packs()
        elif self.use_git:
            is_valid = self.run_validation_using_git()
        elif self.file_path:
            is_valid = self.run_validation_on_specific_files()
        else:
            # default validate to -g --post-commit
            self.use_git = True
            self.is_circle = True
            is_valid = self.run_validation_using_git()
        return self.print_final_report(is_valid)

    def run_validation_on_specific_files(self):
        """Run validations only on specific files"""
        files_validation_result = set()
        if self.use_git:
            self.setup_git_params()
        files_to_validate = self.file_path.split(",")

        for path in files_to_validate:
            error_ignore_list = self.get_error_ignore_list(get_pack_name(path))
            file_level = detect_file_level(path)

            if file_level == PathLevel.FILE:
                logger.info(
                    f"\n<cyan>================= Validating file {path} =================</cyan>"
                )
                files_validation_result.add(
                    self.run_validations_on_file(path, error_ignore_list)
                )

            elif file_level == PathLevel.CONTENT_ENTITY_DIR:
                logger.info(
                    f"\n<cyan>================= Validating content directory {path} =================</cyan>"
                )
                files_validation_result.add(
                    self.run_validation_on_content_entities(path, error_ignore_list)
                )

            elif file_level == PathLevel.CONTENT_GENERIC_ENTITY_DIR:
                logger.info(
                    f"\n<cyan>================= Validating content directory {path} =================</cyan>"
                )
                files_validation_result.add(
                    self.run_validation_on_generic_entities(path, error_ignore_list)
                )

            elif file_level == PathLevel.PACK:
                logger.info(
                    f"\n<cyan>================= Validating pack {path} =================</cyan>"
                )
                files_validation_result.add(self.run_validations_on_pack(path)[0])

            else:
                logger.info(
                    f"\n<cyan>================= Validating package {path} =================</cyan>"
                )
                files_validation_result.add(
                    self.run_validation_on_package(path, error_ignore_list)
                )

        if self.validate_graph:
            logger.info(
                "\n<cyan>================= Validating graph =================</cyan>"
            )
            with GraphValidator(
                specific_validations=self.specific_validations,
                input_files=files_to_validate,
                include_optional_deps=True,
            ) as graph_validator:
                files_validation_result.add(graph_validator.is_valid_content_graph())

        return all(files_validation_result)

    def wait_futures_complete(self, futures_list: List[Future], done_fn: Callable):
        """Wait for all futures to complete, Raise exception if occurred.
        Args:
            futures_list: futures to wait for.
            done_fn: Function to run on result.
        Raises:
            Exception: Raise caught exception for further cleanups.
        """
        for future in as_completed(futures_list):
            try:
                result = future.result()
                done_fn(result[0], result[1])
            except Exception as e:
                logger.info(
                    f"<red>An error occurred while tried to collect result, Error: {e}</red>"
                )
                raise

    def run_validation_on_all_packs(self):
        """Runs validations on all files in all packs in repo (-a option)

        Returns:
            bool. true if all files are valid, false otherwise.
        """
        logger.info(
            "\n<cyan>================= Validating all files =================</cyan>"
        )
        all_packs_valid = set()

        if not self.skip_conf_json:
            all_packs_valid.add(self.conf_json_validator.is_valid_conf_json())

        count = 1
        # Filter non-pack files that might exist locally (e.g, .DS_STORE on MacOS)
        all_packs = list(
            filter(
                os.path.isdir,
                [os.path.join(PACKS_DIR, p) for p in os.listdir(PACKS_DIR)],
            )
        )
        num_of_packs = len(all_packs)
        all_packs.sort(key=str.lower)

        ReadMeValidator.add_node_env_vars()
        if self.is_possible_validate_readme:
            with ReadMeValidator.start_mdx_server(handle_error=self.handle_error):
                return self.validate_packs(
                    all_packs, all_packs_valid, count, num_of_packs
                )
        else:
            return self.validate_packs(all_packs, all_packs_valid, count, num_of_packs)

    def validate_packs(
        self, all_packs: list, all_packs_valid: set, count: int, num_of_packs: int
    ) -> bool:
        if self.run_with_multiprocessing:
            with pebble.ProcessPool(max_workers=cpu_count()) as executor:
                futures = []
                for pack_path in all_packs:
                    futures.append(
                        executor.schedule(
                            self.run_validations_on_pack, args=(pack_path,)
                        )
                    )
                self.wait_futures_complete(
                    futures_list=futures,
                    done_fn=lambda x, y: (
                        all_packs_valid.add(x),  # type: ignore
                        FOUND_FILES_AND_ERRORS.extend(y),  # type: ignore[func-returns-value]
                    ),
                )
        else:
            for pack_path in all_packs:
                self.completion_percentage = format((count / num_of_packs) * 100, ".2f")  # type: ignore
                all_packs_valid.add(self.run_validations_on_pack(pack_path)[0])
                count += 1
        if self.validate_graph:
            logger.info(
                "\n<cyan>================= Validating graph =================</cyan>"
            )
            specific_validations_list = (
                self.specific_validations if self.specific_validations else []
            )
            with GraphValidator(
                specific_validations=self.specific_validations,
                include_optional_deps=(
                    True if "GR103" in specific_validations_list else False
                ),
            ) as graph_validator:
                all_packs_valid.add(graph_validator.is_valid_content_graph())

        return all(all_packs_valid)

    def run_validations_on_pack(self, pack_path, skip_files: Optional[Set[str]] = None):
        """Runs validation on all files in given pack. (i,g,a)

        Args:
            pack_path: the path to the pack.
            skip_files: a list of files to skip.

        Returns:
            bool. true if all files in pack are valid, false otherwise.
        """
        if not skip_files:
            skip_files = set()

        pack_entities_validation_results = set()
        pack_error_ignore_list = self.get_error_ignore_list(Path(pack_path).name)

        pack_entities_validation_results.add(
            self.validate_pack_unique_files(pack_path, pack_error_ignore_list)
        )

        for content_dir in os.listdir(pack_path):
            content_entity_path = os.path.join(pack_path, content_dir)
            if content_entity_path not in skip_files:
                if content_dir in CONTENT_ENTITIES_DIRS:
                    pack_entities_validation_results.add(
                        self.run_validation_on_content_entities(
                            content_entity_path, pack_error_ignore_list
                        )
                    )
                else:
                    self.ignored_files.add(content_entity_path)

        return all(pack_entities_validation_results), FOUND_FILES_AND_ERRORS

    def run_validation_on_content_entities(
        self, content_entity_dir_path, pack_error_ignore_list
    ):
        """Gets non-pack folder and runs validation within it (Scripts, Integrations...)

        Returns:
            bool. true if all files in directory are valid, false otherwise.
        """
        content_entities_validation_results = set()
        if content_entity_dir_path.endswith(
            GENERIC_FIELDS_DIR
        ) or content_entity_dir_path.endswith(GENERIC_TYPES_DIR):
            for dir_name in os.listdir(content_entity_dir_path):
                dir_path = os.path.join(content_entity_dir_path, dir_name)
                if not Path(dir_path).is_file():
                    # should be only directories (not files) in generic types/fields directory
                    content_entities_validation_results.add(
                        self.run_validation_on_generic_entities(
                            dir_path, pack_error_ignore_list
                        )
                    )
                else:
                    self.ignored_files.add(dir_path)
        else:
            for file_name in os.listdir(content_entity_dir_path):
                file_path = os.path.join(content_entity_dir_path, file_name)
                if Path(file_path).is_file():
                    if (
                        file_path.endswith(".json")
                        or file_path.endswith(".yml")
                        or file_path.endswith(".md")
                        or (
                            content_entity_dir_path.endswith(XSIAM_DASHBOARDS_DIR)
                            and file_path.endswith(".png")
                        )
                    ):
                        content_entities_validation_results.add(
                            self.run_validations_on_file(
                                file_path, pack_error_ignore_list
                            )
                        )
                    else:
                        self.ignored_files.add(file_path)

                else:
                    content_entities_validation_results.add(
                        self.run_validation_on_package(
                            file_path, pack_error_ignore_list
                        )
                    )

        return all(content_entities_validation_results)

    @staticmethod
    def should_validate_xsiam_content(package_path):
        parent_name = Path(package_path).stem
        dir_name = Path(package_path).parent.stem
        return (
            parent_name in {"XSIAMDashboards", "XSIAMReports"}
            or dir_name == "XDRCTemplates"
        )

    def run_validation_on_package(self, package_path, pack_error_ignore_list):
        package_entities_validation_results = set()
        for file_name in os.listdir(package_path):
            file_path = os.path.join(package_path, file_name)
            package_entities_validation_results.add(
                self.run_validations_on_file(file_path, pack_error_ignore_list)
            )

        return all(package_entities_validation_results)

    def run_validation_on_generic_entities(self, dir_path, pack_error_ignore_list):
        """
        Gets a generic content entity directory (i.e a sub-directory of GenericTypes or GenericFields)
        and runs validation within it.

        Returns:
            bool. true if all files in directory are valid, false otherwise.
        """
        package_entities_validation_results = set()

        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)
            if file_path.endswith(".json"):  # generic types/fields are jsons
                package_entities_validation_results.add(
                    self.run_validations_on_file(file_path, pack_error_ignore_list)
                )
            else:
                self.ignored_files.add(file_path)

        return all(package_entities_validation_results)

    @error_codes("BA114")
    def is_valid_pack_name(self, file_path, old_file_path, ignored_errors):
        """
        Valid pack name is currently considered to be a new pack name or an existing pack.
        If pack name is changed, will return `False`.
        """
        if not old_file_path:
            return True
        original_pack_name = get_pack_name(old_file_path)
        new_pack_name = get_pack_name(file_path)
        if original_pack_name != new_pack_name:
            error_message, error_code = Errors.changed_pack_name(original_pack_name)
            if self.handle_error(
                error_message=error_message,
                error_code=error_code,
                file_path=file_path,
                drop_line=True,
                ignored_errors=ignored_errors,
            ):
                return False
        return True

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
            if self.handle_error(
                error_message=error_message,
                error_code=error_code,
                file_path=file_path,
                drop_line=True,
                ignored_errors=ignored_errors,
            ):
                return False

        return True

    def is_skipped_file(self, file_path: str) -> bool:
        """check whether the file in the given file_path is in the 'SKIPPED_FILES' list.

        Args:
            file_path: the file on which to run.

        Returns:
            bool. true if file is in SKIPPED_FILES list, false otherwise.
        """
        path = Path(file_path)
        return (
            path.name in SKIPPED_FILES + [LOG_FILE_NAME]
            or (
                path.name == "CommonServerPython.py"
                and path.parent.parent.name != "Base"
            )
            or (LISTS_DIR in path.parts[-3:] and path.name.endswith("_data.json"))
        )

    # flake8: noqa: C901
    def run_validations_on_file(
        self,
        file_path,
        pack_error_ignore_list,
        is_modified=False,
        old_file_path=None,
        modified_files=None,
        added_files=None,
    ):
        """Choose a validator to run for a single file. (i)

        Args:
            modified_files: A set of modified files - used for RN validation
            added_files: A set of added files - used for RN validation
            old_file_path: The old file path for renamed files
            pack_error_ignore_list: A dictionary of all pack ignored errors
            file_path: the file on which to run.
            is_modified: whether the file is modified or added.

        Returns:
            bool. true if file is valid, false otherwise.
        """
        if not self.is_valid_pack_name(
            file_path, old_file_path, pack_error_ignore_list
        ):
            return False
        file_type = find_type(file_path)

        is_added_file = file_path in added_files if added_files else False
        if file_type == FileType.MODELING_RULE_TEST_DATA:
            file_path = file_path.replace("_testdata.json", ".yml")
        if file_path.endswith(".xif"):
            file_path = file_path.replace(".xif", ".yml")
        if (
            file_type in self.skipped_file_types
            or self.is_skipped_file(file_path)
            or (
                self.use_git
                and self.git_util
                and self.git_util._is_file_git_ignored(file_path)
            )
            or detect_file_level(file_path)
            in (PathLevel.PACKAGE, PathLevel.CONTENT_ENTITY_DIR)
        ):
            self.ignored_files.add(file_path)
            return True
        elif not self.is_valid_file_type(file_type, file_path, pack_error_ignore_list):
            return False

        if file_type == FileType.XSOAR_CONFIG:
            xsoar_config_validator = XSOARConfigJsonValidator(
                file_path,
                specific_validations=self.specific_validations,
                ignored_errors=pack_error_ignore_list,
            )
            return xsoar_config_validator.is_valid_xsoar_config_file()

        if not self.check_only_schema:
            # if file_type = None, it means BA102 was ignored in an external repo.
            validation_print = f"\nValidating {file_path} as {file_type.value if file_type else 'unknown-file'}"
            if self.print_percent:
                if FOUND_FILES_AND_ERRORS:
                    validation_print += f" <red>[{self.completion_percentage}%]</red>"
                else:
                    validation_print += (
                        f" <green>[{self.completion_percentage}%]</green>"
                    )

            logger.info(validation_print)

        structure_validator = StructureValidator(
            file_path,
            predefined_scheme=file_type,
            ignored_errors=pack_error_ignore_list,
            tag=self.prev_ver,
            old_file_path=old_file_path,
            branch_name=self.branch_name,
            is_new_file=not is_modified,
            json_file_path=self.json_file_path,
            skip_schema_check=self.skip_schema_check,
            pykwalify_logs=self.pykwalify_logs,
            quiet_bc=self.quiet_bc,
            specific_validations=self.specific_validations,
        )

        # schema validation
        if file_type not in {
            FileType.TEST_PLAYBOOK,
            FileType.TEST_SCRIPT,
            FileType.DESCRIPTION,
        }:
            if not structure_validator.is_valid_file():
                return False

        # Passed schema validation
        # if only schema validation is required - stop check here
        if self.check_only_schema:
            return True

        # id_set validation
        if self.id_set_validations and not self.id_set_validations.is_file_valid_in_set(
            file_path, file_type, pack_error_ignore_list
        ):
            return False

        # conf.json validation
        valid_in_conf = True
        if self.check_is_unskipped and file_type in {
            FileType.INTEGRATION,
            FileType.SCRIPT,
            FileType.BETA_INTEGRATION,
        }:
            if not self.conf_json_validator.is_valid_file_in_conf_json(
                structure_validator.current_file,
                file_type,
                file_path,
                pack_error_ignore_list,
            ):
                valid_in_conf = False

        # test playbooks and test scripts are using the same validation.
        if file_type in {FileType.TEST_PLAYBOOK, FileType.TEST_SCRIPT}:
            return self.validate_test_playbook(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.RELEASE_NOTES:
            if not self.skip_pack_rn_validation:
                return self.validate_release_notes(
                    file_path,
                    added_files,
                    modified_files,
                    pack_error_ignore_list,
                )
            else:
                logger.info("<yellow>Skipping release notes validation</yellow>")

        elif file_type == FileType.RELEASE_NOTES_CONFIG:
            return self.validate_release_notes_config(file_path, pack_error_ignore_list)

        elif file_type == FileType.DESCRIPTION:
            return self.validate_description(file_path, pack_error_ignore_list)

        elif file_type == FileType.README:
            if not self.is_possible_validate_readme:
                error_message, error_code = Errors.error_uninstall_node()
                if self.handle_error(
                    error_message=error_message,
                    error_code=error_code,
                    file_path=file_path,
                    ignored_errors=pack_error_ignore_list,
                ):
                    return False
            if not self.validate_all:
                ReadMeValidator.add_node_env_vars()
                if (
                    not ReadMeValidator.are_modules_installed_for_verify(
                        CONTENT_PATH  # type: ignore
                    )
                    and not ReadMeValidator.is_docker_available()
                ):  # shows warning message
                    return True
                with ReadMeValidator.start_mdx_server(handle_error=self.handle_error):
                    return self.validate_readme(file_path, pack_error_ignore_list)
            return self.validate_readme(file_path, pack_error_ignore_list)

        elif file_type == FileType.REPORT:
            return self.validate_report(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.PLAYBOOK:
            return self.validate_playbook(
                structure_validator, pack_error_ignore_list, file_type, is_modified
            )

        elif file_type == FileType.INTEGRATION:
            return all(
                [
                    self.validate_integration(
                        structure_validator,
                        pack_error_ignore_list,
                        is_modified,
                        file_type,
                    ),
                    valid_in_conf,
                ]
            )

        elif file_type == FileType.SCRIPT:
            return all(
                [
                    self.validate_script(
                        structure_validator,
                        pack_error_ignore_list,
                        is_modified,
                        file_type,
                    ),
                    valid_in_conf,
                ]
            )
        elif file_type == FileType.PYTHON_FILE:
            return self.validate_python_file(file_path, pack_error_ignore_list)

        elif file_type == FileType.BETA_INTEGRATION:
            return self.validate_beta_integration(
                structure_validator, pack_error_ignore_list
            )

        # Validate only images of packs
        elif file_type == FileType.IMAGE:
            return self.validate_image(file_path, pack_error_ignore_list)

        elif file_type == FileType.AUTHOR_IMAGE:
            return self.validate_author_image(file_path, pack_error_ignore_list)

        elif file_type == FileType.INCIDENT_FIELD:
            return self.validate_incident_field(
                structure_validator, pack_error_ignore_list, is_modified, is_added_file
            )

        elif file_type == FileType.INDICATOR_FIELD:
            return self.validate_indicator_field(
                structure_validator, pack_error_ignore_list, is_modified, is_added_file
            )

        elif file_type == FileType.REPUTATION:
            return self.validate_reputation(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.LAYOUT:
            return self.validate_layout(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.LAYOUTS_CONTAINER:
            return self.validate_layoutscontainer(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.PRE_PROCESS_RULES:
            return self.validate_pre_process_rule(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.LISTS:
            return self.validate_lists(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.DASHBOARD:
            return self.validate_dashboard(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.INCIDENT_TYPE:
            return self.validate_incident_type(
                structure_validator, pack_error_ignore_list, is_modified
            )

        elif file_type == FileType.MAPPER:
            return self.validate_mapper(
                structure_validator, pack_error_ignore_list, is_modified
            )

        elif file_type in (FileType.OLD_CLASSIFIER, FileType.CLASSIFIER):
            return self.validate_classifier(
                structure_validator, pack_error_ignore_list, file_type
            )

        elif file_type == FileType.WIDGET:
            return self.validate_widget(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.TRIGGER:
            return self.validate_triggers(structure_validator, pack_error_ignore_list)

        elif file_type in (
            FileType.PARSING_RULE,
            FileType.PARSING_RULE_XIF,
        ):
            return self.validate_parsing_rule(
                structure_validator, pack_error_ignore_list
            )

        elif file_type in (
            FileType.MODELING_RULE,
            FileType.MODELING_RULE_XIF,
            FileType.MODELING_RULE_TEST_DATA,
            FileType.ASSETS_MODELING_RULE,
            FileType.ASSETS_MODELING_RULE_XIF,
            FileType.MODELING_RULE_TEST_DATA,
        ):
            logger.info(f"Validating {file_type.value} file: {file_path}")
            if self.validate_all:
                file_name = Path(file_path).name
                error_ignore_list = pack_error_ignore_list.copy()
                error_ignore_list.setdefault(file_name, [])
                error_ignore_list.get(file_name).append("MR104")
                return self.validate_modeling_rule(
                    structure_validator, error_ignore_list
                )
            return self.validate_modeling_rule(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.CORRELATION_RULE:
            return self.validate_correlation_rule(
                structure_validator, pack_error_ignore_list
            )

        elif file_type in {FileType.XSIAM_DASHBOARD, FileType.XSIAM_DASHBOARD_IMAGE}:
            return self.validate_xsiam_dashboard(
                structure_validator, pack_error_ignore_list
            )

        elif file_type in {FileType.XDRC_TEMPLATE, FileType.XDRC_TEMPLATE_YML}:
            return self.validate_xdrc_templates(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.XSIAM_REPORT:
            return self.validate_xsiam_report(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.WIZARD:
            return self.validate_wizard(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.GENERIC_FIELD:
            return self.validate_generic_field(
                structure_validator, pack_error_ignore_list, is_added_file
            )

        elif file_type == FileType.GENERIC_TYPE:
            return self.validate_generic_type(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.GENERIC_MODULE:
            return self.validate_generic_module(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.GENERIC_DEFINITION:
            return self.validate_generic_definition(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.JOB:
            return self.validate_job(structure_validator, pack_error_ignore_list)

        elif file_type == FileType.LAYOUT_RULE:
            return self.validate_layout_rules(
                structure_validator, pack_error_ignore_list
            )

        elif file_type == FileType.CONTRIBUTORS:
            # This is temporarily - need to add a proper contributors validations
            return True

        elif file_type == FileType.CONF_JSON and not self.skip_conf_json:
            return self.validate_conf_json()

        else:
            return self.file_type_not_supported(
                file_type, file_path, pack_error_ignore_list
            )
        return True

    @error_codes("BA102")
    def file_type_not_supported(
        self, file_type: FileType, file_path: str, ignored_errors: dict
    ):
        error_message, error_code = Errors.file_type_not_supported(file_type, file_path)
        if self.handle_error(
            error_message=error_message,
            error_code=error_code,
            file_path=file_path,
            ignored_errors=ignored_errors,
        ):
            return False
        return True

    def specify_files_by_status(
        self, modified_files: Set, added_files: Set, old_format_files: Set
    ) -> Tuple[Set, Set, Set]:
        """Filter the files identified from git to only specified files.

        Args:
            modified_files(Set): A set of modified and renamed files.
            added_files(Set): A set of added files.
            old_format_files(Set): A set of old format files.

        Returns:
            Tuple[Set, Set, Set]. 3 sets for modified, added an old format files where the only files that
            appear are the ones specified by the 'file_path' OldValidateManager parameter
        """
        filtered_modified_files: Set = set()
        filtered_added_files: Set = set()
        filtered_old_format: Set = set()

        if isinstance(self.file_path, str):
            file_path = self.file_path.split(",")

        for path in file_path:
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

    def run_validation_using_git(self):
        """Runs validation on only changed packs/files (g)"""
        valid_git_setup = self.setup_git_params()
        if not self.no_configuration_prints:
            self.print_git_config()

        (
            modified_files,
            added_files,
            changed_meta_files,
            old_format_files,
            valid_types,
        ) = self.get_changed_files_from_git()

        # filter to only specified paths if given
        if self.file_path:
            (
                modified_files,
                added_files,
                old_format_files,
            ) = self.specify_files_by_status(
                modified_files, added_files, old_format_files
            )
        deleted_files = self.git_util.deleted_files(
            prev_ver=self.prev_ver,
            committed_only=self.is_circle,
            staged_only=self.staged,
            include_untracked=self.include_untracked,
        )

        validation_results = {valid_git_setup, valid_types}

        validation_results.add(
            self.validate_modified_files(modified_files | old_format_files)
        )
        validation_results.add(self.validate_added_files(added_files, modified_files))
        validation_results.add(
            self.validate_changed_packs_unique_files(
                modified_files, added_files, old_format_files, changed_meta_files
            )
        )
        validation_results.add(self.validate_deleted_files(deleted_files, added_files))
        logger.debug("*** after adding validate_deleted_files")

        logger.debug(
            f"*** Before ifs, {old_format_files=}, {self.skip_pack_rn_validation=}"
        )
        if old_format_files:
            logger.info(
                "\n<cyan>================= Running validation on old format files =================</cyan>"
            )
            validation_results.add(self.validate_no_old_format(old_format_files))
            logger.debug("added validate_no_old_format")

        if not self.skip_pack_rn_validation:
            logger.debug("adding validate_no_duplicated_release_notes")
            validation_results.add(
                self.validate_no_duplicated_release_notes(added_files)
            )
            logger.debug("added validate_no_duplicated_release_notes")

        all_files_set = list(
            set().union(
                modified_files, added_files, old_format_files, changed_meta_files
            )
        )
        if self.validate_graph:
            logger.info(
                "\n<cyan>================= Validating graph =================</cyan>"
            )
            if all_files_set:
                with GraphValidator(
                    specific_validations=self.specific_validations,
                    git_files=all_files_set,
                    include_optional_deps=True,
                ) as graph_validator:
                    validation_results.add(graph_validator.is_valid_content_graph())
                    validation_results.add(
                        self.validate_no_missing_release_notes(
                            modified_files,
                            old_format_files,
                            added_files,
                            graph_validator,
                        )
                    )

        if self.packs_with_mp_change:
            logger.info(
                "\n<cyan>================= Running validation on Marketplace Changed Packs =================</cyan>"
            )
            logger.debug(
                f"Found marketplace change in the following packs: {self.packs_with_mp_change}"
            )

            for mp_changed_metadata_pack in self.packs_with_mp_change:
                # Running validation on the whole pack, excluding files that were already checked.
                validation_results.add(
                    self.run_validations_on_pack(
                        mp_changed_metadata_pack, skip_files=set(all_files_set)
                    )[0]
                )

            logger.debug("Finished validating marketplace changed packs.")

        return all(validation_results)

    """ ######################################## Unique Validations ####################################### """

    def validate_description(self, file_path, pack_error_ignore_list):
        description_validator = DescriptionValidator(
            file_path,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        return description_validator.is_valid_file()

    def validate_readme(self, file_path, pack_error_ignore_list):
        readme_validator = ReadMeValidator(
            file_path,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        return readme_validator.is_valid_file()

    def validate_python_file(self, file_path, pack_error_ignore_list):
        python_file_validator = PythonFileValidator(
            file_path,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        return python_file_validator.is_valid_file()

    def validate_test_playbook(self, structure_validator, pack_error_ignore_list):
        test_playbook_validator = TestPlaybookValidator(
            structure_validator=structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return test_playbook_validator.is_valid_test_playbook(validate_rn=False)

    @error_codes("RN108")
    def validate_no_release_notes_for_new_pack(
        self, pack_name, file_path, ignored_errors
    ):
        if pack_name in self.new_packs:
            error_message, error_code = Errors.added_release_notes_for_new_pack(
                pack_name
            )
            if self.handle_error(
                error_message=error_message,
                error_code=error_code,
                file_path=file_path,
                ignored_errors=ignored_errors,
            ):
                return False
        return True

    def validate_release_notes(
        self,
        file_path,
        added_files,
        modified_files,
        pack_error_ignore_list,
    ):
        pack_name = get_pack_name(file_path)

        # added new RN to a new pack
        if not self.validate_no_release_notes_for_new_pack(
            pack_name, file_path, pack_error_ignore_list
        ):
            return False

        if pack_name != "NonSupported":
            if not added_files:
                added_files = {file_path}

            release_notes_validator = ReleaseNotesValidator(
                file_path,
                pack_name=pack_name,
                modified_files=modified_files,
                added_files=added_files,
                ignored_errors=pack_error_ignore_list,
                json_file_path=self.json_file_path,
                specific_validations=self.specific_validations,
            )
            return release_notes_validator.is_file_valid()

        return True

    def validate_release_notes_config(
        self, file_path: str, pack_error_ignore_list: list
    ) -> bool:
        """
        Builds validator for RN config file and returns its validation results.
        Args:
            file_path (str): Path to RN config file.
            pack_error_ignore_list (list): Pack error ignore list.

        Returns:
            (bool): Whether RN config file is valid.
        """
        pack_name = get_pack_name(file_path)
        if pack_name == "NonSupported":
            return True
        release_notes_config_validator = ReleaseNotesConfigValidator(
            file_path,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        return release_notes_config_validator.is_file_valid()

    def validate_playbook(
        self, structure_validator, pack_error_ignore_list, file_type, is_modified
    ):
        playbook_validator = PlaybookValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
            validate_all=self.validate_all,
            deprecation_validator=self.deprecation_validator,
        )

        deprecated_result = self.check_and_validate_deprecated(
            file_type=file_type,
            file_path=structure_validator.file_path,
            current_file=playbook_validator.current_file,
            is_modified=True,
            is_backward_check=False,
            validator=playbook_validator,
        )
        if deprecated_result is not None:
            return deprecated_result

        return playbook_validator.is_valid_playbook(
            validate_rn=False, id_set_file=self.id_set_file, is_modified=is_modified
        )

    def validate_integration(
        self, structure_validator, pack_error_ignore_list, is_modified, file_type
    ):
        integration_validator = IntegrationValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            skip_docker_check=self.skip_docker_checks,
            json_file_path=self.json_file_path,
            validate_all=self.validate_all,
            deprecation_validator=self.deprecation_validator,
            using_git=self.use_git,
        )

        deprecated_result = self.check_and_validate_deprecated(
            file_type=file_type,
            file_path=structure_validator.file_path,
            current_file=integration_validator.current_file,
            is_modified=is_modified,
            is_backward_check=self.is_backward_check,
            validator=integration_validator,
        )
        if deprecated_result is not None:
            return deprecated_result
        if is_modified and self.is_backward_check:
            return all(
                [
                    integration_validator.is_valid_file(
                        validate_rn=False,
                        skip_test_conf=self.skip_conf_json,
                        check_is_unskipped=self.check_is_unskipped,
                        conf_json_data=self.conf_json_data,
                        is_modified=is_modified,
                    ),
                    integration_validator.is_backward_compatible(),
                ]
            )
        else:
            return integration_validator.is_valid_file(
                validate_rn=False,
                skip_test_conf=self.skip_conf_json,
                check_is_unskipped=self.check_is_unskipped,
                conf_json_data=self.conf_json_data,
            )

    def validate_script(
        self, structure_validator, pack_error_ignore_list, is_modified, file_type
    ):
        script_validator = ScriptValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            skip_docker_check=self.skip_docker_checks,
            json_file_path=self.json_file_path,
            validate_all=self.validate_all,
            deprecation_validator=self.deprecation_validator,
            using_git=self.use_git,
        )

        deprecated_result = self.check_and_validate_deprecated(
            file_type=file_type,
            file_path=structure_validator.file_path,
            current_file=script_validator.current_file,
            is_modified=is_modified,
            is_backward_check=self.is_backward_check,
            validator=script_validator,
        )
        if deprecated_result is not None:
            return deprecated_result

        if is_modified and self.is_backward_check:
            return all(
                [
                    script_validator.is_valid_file(validate_rn=False),
                    script_validator.is_backward_compatible(),
                ]
            )
        else:
            return script_validator.is_valid_file(validate_rn=False)

    def validate_beta_integration(self, structure_validator, pack_error_ignore_list):
        integration_validator = IntegrationValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            skip_docker_check=self.skip_docker_checks,
            json_file_path=self.json_file_path,
            validate_all=self.validate_all,
            using_git=self.use_git,
        )
        return integration_validator.is_valid_beta_integration()

    def validate_image(self, file_path, pack_error_ignore_list):
        pack_name = get_pack_name(file_path)
        if pack_name == "NonSupported":
            return True
        image_validator = ImageValidator(
            file_path,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        return image_validator.is_valid()

    def validate_author_image(self, file_path, pack_error_ignore_list):
        author_image_validator: AuthorImageValidator = AuthorImageValidator(
            file_path,
            ignored_errors=pack_error_ignore_list,
            specific_validations=self.specific_validations,
        )
        return author_image_validator.is_valid()

    def validate_report(self, structure_validator, pack_error_ignore_list):
        report_validator = ReportValidator(
            structure_validator=structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return report_validator.is_valid_file(validate_rn=False)

    def validate_incident_field(
        self, structure_validator, pack_error_ignore_list, is_modified, is_added_file
    ):
        incident_field_validator = IncidentFieldValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
            id_set_file=self.id_set_file,
        )
        if is_modified and self.is_backward_check:
            return all(
                [
                    incident_field_validator.is_valid_file(
                        validate_rn=False,
                        is_new_file=not is_modified,
                        use_git=self.use_git,
                        is_added_file=is_added_file,
                    ),
                    incident_field_validator.is_backward_compatible(),
                ]
            )
        else:
            return incident_field_validator.is_valid_file(
                validate_rn=False,
                is_new_file=not is_modified,
                use_git=self.use_git,
                is_added_file=is_added_file,
            )

    def validate_indicator_field(
        self, structure_validator, pack_error_ignore_list, is_modified, is_added_file
    ):
        indicator_field_validator = IndicatorFieldValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        if is_modified and self.is_backward_check:
            return all(
                [
                    indicator_field_validator.is_valid_file(
                        validate_rn=False,
                        is_new_file=not is_modified,
                        use_git=self.use_git,
                        is_added_file=is_added_file,
                    ),
                    indicator_field_validator.is_backward_compatible(),
                ]
            )
        else:
            return indicator_field_validator.is_valid_file(
                validate_rn=False,
                is_new_file=not is_modified,
                use_git=self.use_git,
                is_added_file=is_added_file,
            )

    def validate_reputation(self, structure_validator, pack_error_ignore_list):
        reputation_validator = ReputationValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return reputation_validator.is_valid_file(validate_rn=False)

    def validate_layout(self, structure_validator, pack_error_ignore_list):
        layout_validator = LayoutValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return layout_validator.is_valid_layout(
            validate_rn=False, id_set_file=self.id_set_file, is_circle=self.is_circle
        )

    def validate_layoutscontainer(self, structure_validator, pack_error_ignore_list):
        layout_validator = LayoutsContainerValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return layout_validator.is_valid_layout(
            validate_rn=False, id_set_file=self.id_set_file, is_circle=self.is_circle
        )

    def validate_pre_process_rule(self, structure_validator, pack_error_ignore_list):
        pre_process_rules_validator = PreProcessRuleValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return pre_process_rules_validator.is_valid_pre_process_rule(
            validate_rn=False, id_set_file=self.id_set_file, is_ci=self.is_circle
        )

    def validate_lists(self, structure_validator, pack_error_ignore_list):
        lists_validator = ListsValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return lists_validator.is_valid_list()

    def validate_dashboard(self, structure_validator, pack_error_ignore_list):
        dashboard_validator = DashboardValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return dashboard_validator.is_valid_dashboard(validate_rn=False)

    def validate_incident_type(
        self, structure_validator, pack_error_ignore_list, is_modified
    ):
        incident_type_validator = IncidentTypeValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        if is_modified and self.is_backward_check:
            return all(
                [
                    incident_type_validator.is_valid_incident_type(validate_rn=False),
                    incident_type_validator.is_backward_compatible(),
                ]
            )
        else:
            return incident_type_validator.is_valid_incident_type(validate_rn=False)

    def validate_mapper(self, structure_validator, pack_error_ignore_list, is_modified):
        mapper_validator = MapperValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        if is_modified and self.is_backward_check:
            return all(
                [
                    mapper_validator.is_valid_mapper(
                        validate_rn=False,
                        id_set_file=self.id_set_file,
                        is_circle=self.is_circle,
                    ),
                    mapper_validator.is_backward_compatible(),
                ]
            )

        return mapper_validator.is_valid_mapper(
            validate_rn=False, id_set_file=self.id_set_file, is_circle=self.is_circle
        )

    def validate_classifier(
        self, structure_validator, pack_error_ignore_list, file_type
    ):
        if file_type == FileType.CLASSIFIER:
            new_classifier_version = True

        else:
            new_classifier_version = False

        classifier_validator = ClassifierValidator(
            structure_validator,
            new_classifier_version=new_classifier_version,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return classifier_validator.is_valid_classifier(
            validate_rn=False, id_set_file=self.id_set_file, is_circle=self.is_circle
        )

    def validate_widget(self, structure_validator, pack_error_ignore_list):
        widget_validator = WidgetValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return widget_validator.is_valid_file(validate_rn=False)

    def validate_triggers(self, structure_validator, pack_error_ignore_list):
        triggers_validator = TriggersValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return triggers_validator.is_valid_file(validate_rn=False)

    def validate_layout_rules(self, structure_validator, pack_error_ignore_list):
        layout_rules_validator = LayoutRuleValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return layout_rules_validator.is_valid_file(validate_rn=False)

    def validate_conf_json(self):
        conf_json_validator = ConfJsonValidator()
        return conf_json_validator.is_valid_conf_json()

    def validate_xsiam_report(self, structure_validator, pack_error_ignore_list):
        xsiam_report_validator = XSIAMReportValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return xsiam_report_validator.is_valid_file(validate_rn=False)

    def validate_xsiam_dashboard(self, structure_validator, pack_error_ignore_list):
        xsiam_dashboard_validator = XSIAMDashboardValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return xsiam_dashboard_validator.is_valid_file(validate_rn=False)

    def validate_xdrc_templates(self, structure_validator, pack_error_ignore_list):
        xdrc_templates_validator = XDRCTemplatesValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return xdrc_templates_validator.is_valid_file(validate_rn=False)

    def validate_parsing_rule(self, structure_validator, pack_error_ignore_list):
        parsing_rule_validator = ParsingRuleValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return parsing_rule_validator.is_valid_file(validate_rn=False)

    def validate_correlation_rule(self, structure_validator, pack_error_ignore_list):
        correlation_rule_validator = CorrelationRuleValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return correlation_rule_validator.is_valid_file(validate_rn=False)

    def validate_modeling_rule(self, structure_validator, pack_error_ignore_list):
        modeling_rule_validator = ModelingRuleValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return modeling_rule_validator.is_valid_file(validate_rn=False)

    def validate_wizard(self, structure_validator, pack_error_ignore_list):
        wizard_validator = WizardValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        return wizard_validator.is_valid_file(
            validate_rn=False, id_set_file=self.id_set_file
        )

    def validate_generic_field(
        self, structure_validator, pack_error_ignore_list, is_added_file
    ):
        generic_field_validator = GenericFieldValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )

        return generic_field_validator.is_valid_file(
            validate_rn=False, is_added_file=is_added_file
        )

    def validate_generic_type(self, structure_validator, pack_error_ignore_list):
        generic_type_validator = GenericTypeValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )

        return generic_type_validator.is_valid_file(validate_rn=False)

    def validate_generic_module(self, structure_validator, pack_error_ignore_list):
        generic_module_validator = GenericModuleValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )

        return generic_module_validator.is_valid_file(validate_rn=False)

    def validate_generic_definition(self, structure_validator, pack_error_ignore_list):
        generic_definition_validator = GenericDefinitionValidator(
            structure_validator,
            ignored_errors=pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )

        return generic_definition_validator.is_valid_file(validate_rn=False)

    def validate_pack_unique_files(
        self, pack_path: str, pack_error_ignore_list: dict, should_version_raise=False
    ) -> bool:
        """
        Runs validations on the following pack files:
        * .secret-ignore: Validates that the file exist and that the file's secrets can be parsed as a list delimited by '\n'
        * .pack-ignore: Validates that the file exists and that all regexes in it can be compiled
        * README.md file: Validates that the file exists and image links are valid
        * 2.pack_metadata.json: Validates that the file exists and that it has a valid structure
        * Author_image.png: Validates that the file isn't empty, dimension of 120*50 and that image size is up to 4kb
        Runs validation on the pack dependencies
        Args:
            should_version_raise: Whether we should check if the version of the metadata was raised
            pack_error_ignore_list: A dictionary of all pack ignored errors
            pack_path: A path to a pack
        """
        files_valid = True
        author_valid = True

        logger.info(f"\nValidating {pack_path} unique pack files")
        pack_unique_files_validator = PackUniqueFilesValidator(
            pack=Path(pack_path).name,
            pack_path=pack_path,
            ignored_errors=pack_error_ignore_list,
            should_version_raise=should_version_raise,
            validate_dependencies=not self.skip_dependencies,
            id_set_path=self.id_set_path,
            private_repo=self.is_external_repo,
            skip_id_set_creation=self.skip_id_set_creation,
            prev_ver=self.prev_ver,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        pack_errors = pack_unique_files_validator.are_valid_files(
            self.id_set_validations
        )
        if pack_errors:
            files_valid = False

        # check author image
        author_image_path = os.path.join(pack_path, AUTHOR_IMAGE_FILE_NAME)
        if Path(author_image_path).exists():
            logger.info("Validating pack author image")
            author_valid = self.validate_author_image(
                author_image_path, pack_error_ignore_list
            )

        if pack_unique_files_validator.check_metadata_for_marketplace_change():
            self.packs_with_mp_change = self.packs_with_mp_change.union({pack_path})

        return files_valid and author_valid

    def validate_job(self, structure_validator, pack_error_ignore_list):
        job_validator = JobValidator(
            structure_validator,
            pack_error_ignore_list,
            json_file_path=self.json_file_path,
        )
        is_valid = job_validator.is_valid_file()
        if not is_valid:
            job_validator_errors = job_validator.get_errors()
            logger.info(f"<red>{job_validator_errors}</red>")

        return is_valid

    def get_old_file_path(self, file_path):
        """
        Extract the old file path from the given file
        Args:
            file_path: the path to extract the old file path from.
        """
        return file_path[:2] if isinstance(file_path, tuple) else (file_path, file_path)

    def get_all_files_edited_in_pack_ignore(self, modified_files: set) -> set:
        """
        Extract all the files the file paths of files that there pack-ignore section was ignored somehow.
        Args:
            modified_files: The list of modified files.
        """
        all_files = self.git_util.get_all_files()
        all_files_edited_in_pack_ignore: set = set()
        for file_path in modified_files:
            # handle renamed files
            old_file_path, file_path = self.get_old_file_path(file_path)
            if not file_path.endswith(".pack-ignore"):
                continue
            # if the repo does not have remotes, get the .pack-ignore content from the master branch in Github api
            # if the repo is not in remote / file cannot be found from Github api, try to take it from the latest commit on the default branch (usually master/main)
            old_pack_ignore_content = get_remote_file(
                old_file_path, DEMISTO_GIT_PRIMARY_BRANCH
            )
            if (
                isinstance(old_pack_ignore_content, bytes)
                and old_pack_ignore_content.strip() == b""
            ):  # found an empty file in remote
                old_pack_ignore_content = ""
            elif old_pack_ignore_content == {}:  # not found in remote
                logger.debug(
                    f"Could not get {old_file_path} from remote master branch, trying to get it from local branch"
                )
                primary_branch = GitUtil.find_primary_branch(self.git_util.repo)
                _pack_ignore_default_branch_path = f"{primary_branch}:{old_file_path}"
                try:
                    old_pack_ignore_content = (
                        self.git_util.get_local_remote_file_content(
                            _pack_ignore_default_branch_path
                        )
                    )
                except GitCommandError:
                    logger.warning(
                        f"could not retrieve {_pack_ignore_default_branch_path} from {primary_branch} because {primary_branch} is not a valid ref, assuming .pack-ignore is empty"
                    )
                    old_pack_ignore_content = ""

            config = ConfigParser(allow_no_value=True)
            config.read_string(old_pack_ignore_content)
            old_pack_ignore_content = self.get_error_ignore_list(config=config)
            pack_name = get_pack_name(str(file_path))
            file_content = self.get_error_ignore_list(pack_name)
            files_to_test = set()
            for key, value in old_pack_ignore_content.items():
                if not (section_values := file_content.get(key, [])) or not set(
                    section_values
                ) == set(value):
                    files_to_test.add(key)
            for key, value in file_content.items():
                if not (
                    section_values := old_pack_ignore_content.get(key, [])
                ) or not set(section_values) == set(value):
                    files_to_test.add(key)

            all_files_mapper = {
                file.name: str(file)
                for file in all_files
                if is_file_in_pack(file, pack_name)
            }
            for file in files_to_test:
                if file in all_files_mapper:
                    all_files_edited_in_pack_ignore.add(all_files_mapper.get(file))
        return all_files_edited_in_pack_ignore

    def validate_modified_files(self, modified_files):
        logger.info(
            "\n<cyan>================= Running validation on modified files =================</cyan>"
        )
        valid_files = set()
        all_files_edited_in_pack_ignore = self.get_all_files_edited_in_pack_ignore(
            modified_files
        )
        for file_path in modified_files.union(all_files_edited_in_pack_ignore):
            # handle renamed files
            old_file_path, file_path = self.get_old_file_path(file_path)

            pack_name = get_pack_name(file_path)
            valid_files.add(
                self.run_validations_on_file(
                    file_path,
                    self.get_error_ignore_list(pack_name),
                    is_modified=file_path in modified_files,
                    old_file_path=old_file_path,
                )
            )

        return all(valid_files)

    def validate_added_files(self, added_files, modified_files):
        logger.info(
            "\n<cyan>================= Running validation on newly added files =================</cyan>"
        )

        valid_files = set()
        for file_path in added_files:
            pack_name = get_pack_name(file_path)
            valid_files.add(
                self.run_validations_on_file(
                    file_path,
                    self.get_error_ignore_list(pack_name),
                    is_modified=False,
                    modified_files=modified_files,
                    added_files=added_files,
                )
            )
        return all(valid_files)

    @staticmethod
    def should_raise_pack_version(pack: str) -> bool:
        """
        Args:
            pack: The pack name.

        Returns: False if pack is in IGNORED_PACK_NAMES else True.

        """
        return pack not in IGNORED_PACK_NAMES

    @staticmethod
    def is_file_allowed_to_be_deleted(file_path):
        """
        Args:
            file_path: The file path.

        Returns: True if the file allowed to be deleted, else False.

        """
        file_path = str(file_path)
        file_dict = get_remote_file(file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH)
        file_type = find_type(file_path, file_dict)
        return file_type in FileType_ALLOWED_TO_DELETE or not file_type

    @staticmethod
    def was_file_renamed_but_labeled_as_deleted(deleted_file_path, added_files):
        """Check if a file was renamed and not deleted (git false label the file as deleted)
        Args:
            file_path: The file path.

        Returns: True if the file was renamed and not deleted, else False.

        """
        if added_files:
            deleted_file_path = str(deleted_file_path)
            deleted_file_dict = get_remote_file(
                deleted_file_path, tag=DEMISTO_GIT_PRIMARY_BRANCH
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
                            file_dict = get_file(file)
                            if deleted_file_id == _get_file_id(
                                file_type.value, file_dict
                            ):
                                return True
        return False

    @error_codes("BA115")
    def validate_deleted_files(self, deleted_files: set, added_files: set) -> bool:
        logger.info(
            "\n<cyan>================= Checking for prohibited deleted files =================</cyan>"
        )

        is_valid = True
        for file_path in deleted_files:
            file_path = Path(file_path)
            ignored_errors = self.get_error_ignore_list(get_pack_name(str(file_path)))
            if "Packs" not in file_path.absolute().parts:
                # not allowed to delete non-content files
                file_path = str(file_path)
                error_message, error_code = Errors.file_cannot_be_deleted(file_path)
                if self.handle_error(
                    error_message, error_code, file_path, ignored_errors=ignored_errors
                ):
                    is_valid = False

            else:
                if not self.was_file_renamed_but_labeled_as_deleted(
                    file_path, added_files
                ):
                    if not self.is_file_allowed_to_be_deleted(file_path):
                        file_path = str(file_path)
                        error_message, error_code = Errors.file_cannot_be_deleted(
                            file_path
                        )
                        if self.handle_error(
                            error_message,
                            error_code,
                            file_path,
                            ignored_errors=ignored_errors,
                        ):
                            is_valid = False

        return is_valid

    def validate_changed_packs_unique_files(
        self, modified_files, added_files, old_format_files, changed_meta_files
    ):
        logger.info(
            "\n<cyan>================= Running validation on changed pack unique files =================</cyan>"
        )
        valid_pack_files = set()

        added_packs = get_pack_names_from_files(added_files)
        modified_packs = get_pack_names_from_files(modified_files).union(
            get_pack_names_from_files(old_format_files)
        )
        changed_meta_packs = get_pack_names_from_files(changed_meta_files)

        packs_that_should_have_version_raised = (
            self.get_packs_that_should_have_version_raised(
                modified_files, added_files, old_format_files, changed_meta_files
            )
        )

        changed_packs = modified_packs.union(added_packs).union(changed_meta_packs)

        for pack in changed_packs:
            raise_version = False
            pack_path = tools.pack_name_to_path(pack)
            if pack in packs_that_should_have_version_raised:
                raise_version = self.should_raise_pack_version(pack)
            valid_pack_files.add(
                self.validate_pack_unique_files(
                    pack_path,
                    self.get_error_ignore_list(pack),
                    should_version_raise=raise_version,
                )
            )

        return all(valid_pack_files)

    @error_codes("ST106")
    def validate_no_old_format(self, old_format_files):
        """Validate there are no files in the old format (unified yml file for the code and configuration
        for python integration).

        Args:
            old_format_files(set): file names which are in the old format.
        """
        handle_error = True
        for file_path in old_format_files:
            logger.info(f"Validating old-format file {file_path}")
            yaml_data = get_yaml(file_path)
            # we only fail on old format if no toversion (meaning it is latest) or if the ynl is not deprecated.
            if "toversion" not in yaml_data and not yaml_data.get("deprecated"):
                error_message, error_code = Errors.invalid_package_structure()
                ignored_errors = self.get_error_ignore_list(get_pack_name(file_path))
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=file_path,
                    ignored_errors=ignored_errors,
                ):
                    handle_error = False
        return handle_error

    @error_codes("RN105")
    def validate_no_duplicated_release_notes(self, added_files):
        """Validated that among the added files - there are no duplicated RN for the same pack.

        Args:
            added_files(set): The added files

        Returns:
            bool. True if no duplications found, false otherwise
        """
        logger.info(
            "\n<cyan>================= Verifying no duplicated release notes =================</cyan>"
        )
        added_rn = set()
        for file in added_files:
            if find_type(file) == FileType.RELEASE_NOTES:
                pack_name = get_pack_name(file)
                if pack_name not in added_rn:
                    added_rn.add(pack_name)
                else:
                    error_message, error_code = Errors.multiple_release_notes_files()
                    ignored_errors = self.get_error_ignore_list(pack_name)
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=pack_name,
                        ignored_errors=ignored_errors,
                    ):
                        return False

        logger.info("\n<green>No duplicated release notes found.</green>\n")
        return True

    @error_codes("RN106")
    def validate_no_missing_release_notes(
        self, modified_files, old_format_files, added_files, graph_validator
    ):
        """Validate that there are no missing RN for changed files

        Args:
            modified_files (set): a set of modified files.
            old_format_files (set): a set of old format files that were changed.
            added_files (set): a set of files that were added.
            graph_validator : Content graph

        Returns:
            bool. True if no missing RN found, False otherwise
        """
        logger.info(
            "\n<cyan>================= Checking for missing release notes =================</cyan>\n"
        )
        packs_that_should_have_new_rn_api_module_related: set = set()
        # existing packs that have files changed (which are not RN, README nor test files) - should have new RN
        changed_files = modified_files.union(old_format_files).union(added_files)
        packs_that_should_have_new_rn = get_pack_names_from_files(
            changed_files, skip_file_types=SKIP_RELEASE_NOTES_FOR_TYPES
        )
        if API_MODULES_PACK in packs_that_should_have_new_rn:
            api_module_set = get_api_module_ids(changed_files)
            integrations = get_api_module_dependencies_from_graph(
                api_module_set, graph_validator.graph
            )
            packs_that_should_have_new_rn_api_module_related = set(
                map(lambda integration: integration.pack_id, integrations)
            )
            packs_that_should_have_new_rn = packs_that_should_have_new_rn.union(
                packs_that_should_have_new_rn_api_module_related
            )

            # APIModules pack is without a version and should not have RN
            packs_that_should_have_new_rn.remove(API_MODULES_PACK)

        # new packs should not have RN
        packs_that_should_have_new_rn = packs_that_should_have_new_rn - self.new_packs

        packs_that_have_new_rn = self.get_packs_with_added_release_notes(added_files)

        packs_that_have_missing_rn = packs_that_should_have_new_rn.difference(
            packs_that_have_new_rn
        )

        if packs_that_have_missing_rn:
            is_valid = set()
            for pack in packs_that_have_missing_rn:
                # # ignore RN in NonSupported pack
                if "NonSupported" in pack:
                    continue
                ignored_errors_list = self.get_error_ignore_list(pack)
                if pack in packs_that_should_have_new_rn_api_module_related:
                    error_message, error_code = Errors.missing_release_notes_for_pack(
                        API_MODULES_PACK
                    )
                else:
                    error_message, error_code = Errors.missing_release_notes_for_pack(
                        pack
                    )
                if not BaseValidator(
                    ignored_errors=ignored_errors_list,
                    json_file_path=self.json_file_path,
                    specific_validations=self.specific_validations,
                ).handle_error(
                    error_message,
                    error_code,
                    file_path=os.path.join(
                        os.getcwd(), PACKS_DIR, pack, PACKS_PACK_META_FILE_NAME
                    ),
                ):
                    is_valid.add(True)

                else:
                    is_valid.add(False)

            return all(is_valid)

        else:
            logger.info("<green>No missing release notes found.</green>\n")
            return True

    """ ######################################## Git Tools and filtering ####################################### """

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
                f"<red>Could not find remote {non_existing_remote} reverting to "
                f"{str(self.git_util.repo.remote())}</red>"
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
            if self.handle_error(
                error_message,
                error_code,
                file_path="General",
                warning=(not self.is_external_repo or self.is_circle),
                drop_line=True,
            ):
                return False
        return True

    def print_git_config(self):
        logger.info(
            f"\n<cyan>================= Running validation on branch {self.branch_name} =================</cyan>"
        )
        if not self.no_configuration_prints:
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
                        logger.info(f"<yellow>ignoring file {file_path}</yellow>")
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
            file_type, file_path, self.get_error_ignore_list(get_pack_name(file_path))
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
            FileType.ASSETS_MODELING_RULE_XIF,
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
            logger.info(f"<yellow>ignoring file {file_path}</yellow>")
        self.ignored_files.add(file_path)

    """ ######################################## Validate Tools ############################################### """

    @staticmethod
    def create_ignored_errors_list(errors_to_check):
        """Creating a list of errors without the errors in the errors_to_check list"""
        ignored_error_list = []
        all_errors = get_all_error_codes()
        for error_code in all_errors:
            error_type = error_code[:2]
            if error_code not in errors_to_check and error_type not in errors_to_check:
                ignored_error_list.append(error_code)

        return ignored_error_list

    def add_ignored_errors_to_list(self, config, section, key, ignored_errors_list):
        if key == "ignore":
            ignored_errors_list.extend(str(config[section][key]).split(","))

        if key in PRESET_ERROR_TO_IGNORE:
            ignored_errors_list.extend(PRESET_ERROR_TO_IGNORE.get(key))

        if key in PRESET_ERROR_TO_CHECK:
            ignored_errors_list.extend(
                self.create_ignored_errors_list(PRESET_ERROR_TO_CHECK.get(key))
            )

    def get_error_ignore_list(self, pack_name="", config=None):
        ignored_errors_list: dict = {}
        if pack_name:
            config = get_pack_ignore_content(pack_name)
        if config:
            # create file specific ignored errors list
            for section in filter(
                lambda section: section.startswith("file:"), config.sections()
            ):
                file_name = section[len("file:") :]
                ignored_errors_list[file_name] = []
                for key in config[section]:
                    self.add_ignored_errors_to_list(
                        config, section, key, ignored_errors_list[file_name]
                    )

        return ignored_errors_list

    @staticmethod
    def is_old_file_format(file_path: str, file_type: FileType) -> bool:
        """Check if the file is an old format file or new format file
        Args:
            file_path (str): The file path
            file_type (FileType): The file type
        Returns:
            bool: True if the given file is in old format. Otherwise, return False.
        """
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

    @staticmethod
    def get_packs_with_added_release_notes(added_files):
        added_rn = set()
        for file in added_files:
            if find_type(path=file) == FileType.RELEASE_NOTES:
                added_rn.add(get_pack_name(file))

        return added_rn

    def print_ignored_errors_report(self):
        all_ignored_errors = "\n".join(FOUND_FILES_AND_IGNORED_ERRORS)
        logger.info(
            f"\n<yellow>=========== Found ignored errors "
            f"in the following files ===========\n\n{all_ignored_errors}</yellow>"
        )

    def print_ignored_files_report(self):
        all_ignored_files = "\n".join(list(self.ignored_files))
        logger.info(
            f"\n<yellow>=========== Ignored the following files ===========\n\n{all_ignored_files}</yellow>"
        )

    def get_packs_that_should_have_version_raised(
        self, modified_files, added_files, old_format_files, changed_meta_files
    ):
        # modified packs (where the change is not test-playbook, test-script, readme, metadata file, release notes or
        # doc/author images)
        all_modified_files = modified_files.union(old_format_files)
        modified_packs_that_should_have_version_raised = get_pack_names_from_files(
            all_modified_files,
            skip_file_types={
                FileType.RELEASE_NOTES,
                FileType.README,
                FileType.TEST_PLAYBOOK,
                FileType.TEST_SCRIPT,
                FileType.DOC_IMAGE,
                FileType.AUTHOR_IMAGE,
                FileType.CONTRIBUTORS,
                FileType.PACK_IGNORE,
            },
        )
        if changed_meta_files:
            modified_packs_that_should_have_version_raised = (
                modified_packs_that_should_have_version_raised.union(
                    get_pack_names_from_files(
                        self.get_changed_meta_files_that_should_have_version_raised(
                            changed_meta_files
                        )
                    )
                )
            )

        # also existing packs with added files which are not test-playbook, test-script readme or release notes
        # should have their version raised
        modified_packs_that_should_have_version_raised = (
            modified_packs_that_should_have_version_raised.union(
                get_pack_names_from_files(
                    added_files,
                    skip_file_types={
                        FileType.RELEASE_NOTES,
                        FileType.README,
                        FileType.TEST_PLAYBOOK,
                        FileType.TEST_SCRIPT,
                        FileType.DOC_IMAGE,
                        FileType.AUTHOR_IMAGE,
                        FileType.CONTRIBUTORS,
                    },
                )
                - self.new_packs
            )
        )

        return modified_packs_that_should_have_version_raised

    @staticmethod
    def get_packs(changed_files):
        packs = set()
        for changed_file in changed_files:
            if isinstance(changed_file, tuple):
                changed_file = changed_file[1]
            pack = get_pack_name(changed_file)
            if pack:
                packs.add(pack)

        return packs

    def get_id_set_file(self, skip_id_set_creation, id_set_path):
        """

        Args:
            skip_id_set_creation (bool): whether should skip id set validation or not
            this will also determine whether a new id_set can be created by validate.
            id_set_path (str): id_set.json path file

        Returns:
            str: is_set file path
        """
        id_set = {}
        if not Path(id_set_path).is_file():
            if not skip_id_set_creation:
                id_set, _, _ = IDSetCreator(print_logs=False).create_id_set()

        else:
            id_set = open_id_set_file(id_set_path)

        if not id_set and not self.no_configuration_prints:
            error_message, error_code = Errors.no_id_set_file()
            self.handle_error(
                error_message,
                error_code,
                file_path=os.path.join(os.getcwd(), id_set_path),
                warning=True,
            )

        return id_set

    def check_and_validate_deprecated(
        self,
        file_type,
        file_path,
        current_file,
        is_modified,
        is_backward_check,
        validator,
    ):
        """If file is deprecated, validate it. Return None otherwise.

        Files with 'deprecated: true' or 'toversion < OLDEST_SUPPORTED_VERSION' fields are considered deprecated.

        Args:
            file_type: (FileType) Type of file to validate.
            file_path: (str) file path to validate.
            current_file: (dict) file in json format to validate.
            is_modified: (boolean) for whether the file was modified.
            is_backward_check: (boolean) for whether to preform backwards compatibility validation.
            validator: (ContentEntityValidator) validator object to run backwards compatibility validation from.

        Returns:
            True if current_file is deprecated and valid.
            False if current_file is deprecated and invalid.
            None if current_file is not deprecated.
        """
        is_deprecated = current_file.get("deprecated")

        toversion_is_old = "toversion" in current_file and version.parse(
            current_file.get("toversion", DEFAULT_CONTENT_ITEM_TO_VERSION)
        ) < version.parse(OLDEST_SUPPORTED_VERSION)

        if is_deprecated or toversion_is_old:
            logger.info(f"Validating deprecated file: {file_path}")

            is_valid_as_deprecated = True
            if hasattr(validator, "is_valid_as_deprecated"):
                is_valid_as_deprecated = validator.is_valid_as_deprecated()

            if is_modified and is_backward_check:
                return all([is_valid_as_deprecated, validator.is_backward_compatible()])

            self.ignored_files.add(file_path)
            if self.print_ignored_files:
                logger.info(f"Skipping validation for: {file_path}")

            return is_valid_as_deprecated
        return None

    def get_changed_meta_files_that_should_have_version_raised(
        self, changed_meta_files
    ):
        """
        Check if specified fields have changed in each meta_file to determine if it should have its version raised.

        Args:
            changed_meta_files (set): set of file paths of the changed meta files.

        Returns:
            set: A set containing file paths of meta_files that should have their version raised.
        """
        changed_meta_files_that_should_have_version_raised = set()
        for file_path in changed_meta_files:
            old_meta_file_content = get_remote_file(file_path, tag=self.prev_ver)
            with open(file_path) as f:
                current_meta_file_content = json.load(f)
            if any(
                current_meta_file_content.get(field) != old_meta_file_content.get(field)
                for field in PACK_METADATA_REQUIRE_RN_FIELDS
            ):
                changed_meta_files_that_should_have_version_raised.add(file_path)
        return changed_meta_files_that_should_have_version_raised
