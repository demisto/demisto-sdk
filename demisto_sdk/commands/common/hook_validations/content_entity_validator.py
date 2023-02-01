import logging
import os
import re
from abc import abstractmethod
from distutils.version import LooseVersion
from typing import Optional

import click
from packaging import version

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    ENTITY_NAME_SEPARATORS,
    EXCLUDED_DISPLAY_NAME_WORDS,
    FEATURE_BRANCHES,
    FROM_TO_VERSION_REGEX,
    GENERIC_OBJECTS_OLDEST_SUPPORTED_VERSION,
    OLDEST_SUPPORTED_VERSION,
    FileType,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.hook_validations.structure import (  # noqa:F401
    StructureValidator,
)
from demisto_sdk.commands.common.tools import (
    _get_file_id,
    find_type,
    get_file_displayed_name,
    is_test_config_match,
    run_command,
)
from demisto_sdk.commands.format.format_constants import OLD_FILE_DEFAULT_1_FROMVERSION

json = JSON_Handler()
yaml = YAML_Handler()
logger = logging.getLogger("demisto-sdk")


class ContentEntityValidator(BaseValidator):
    DEFAULT_VERSION = -1

    def __init__(
        self,
        structure_validator: StructureValidator,
        ignored_errors: Optional[dict] = None,
        print_as_warnings: bool = False,
        skip_docker_check: bool = False,
        suppress_print: bool = False,
        json_file_path: Optional[str] = None,
        oldest_supported_version: Optional[str] = None,
    ) -> None:
        super().__init__(
            ignored_errors=ignored_errors,
            print_as_warnings=print_as_warnings,
            suppress_print=suppress_print,
            json_file_path=json_file_path,
            specific_validations=structure_validator.specific_validations,
        )
        self.structure_validator = structure_validator
        self.current_file = structure_validator.current_file
        self.old_file = structure_validator.old_file
        self.file_path = structure_validator.file_path
        self.is_valid = structure_validator.is_valid
        self.skip_docker_check = skip_docker_check
        self.prev_ver = structure_validator.prev_ver
        self.branch_name = structure_validator.branch_name
        self.oldest_supported_version = (
            oldest_supported_version or OLDEST_SUPPORTED_VERSION
        )

    def is_valid_file(self, validate_rn=True):
        tests = [
            self.is_valid_version(),
            self.is_valid_fromversion(),
            self.name_does_not_contain_excluded_word(),
            self.is_there_spaces_in_the_end_of_name(),
            self.is_there_spaces_in_the_end_of_id(),
            self.are_fromversion_and_toversion_in_correct_format(),
            self.are_fromversion_toversion_synchronized(),
        ]

        return all(tests)

    def is_backward_compatible(self):
        if not self.old_file:
            return True

        click.secho(f"Validating backwards compatibility for {self.file_path}")

        is_backward_compatible = [
            self.is_id_not_modified(),
            self.is_valid_fromversion_on_modified(),
        ]

        return all(is_backward_compatible)

    def is_valid_generic_object_file(self):
        tests = [self.is_valid_fromversion_for_generic_objects()]
        return all(tests)

    @abstractmethod
    def is_valid_version(self) -> bool:
        pass

    @error_codes("BC105")
    def is_id_not_modified(self) -> bool:
        """Check if the ID of the file has been changed.

        Returns:
            (bool): Whether the file's ID has been modified or not.
        """
        if not self.old_file:
            return True

        old_version_id = self.structure_validator.get_file_id_from_loaded_file_data(
            self.old_file
        )
        new_file_id = self.structure_validator.get_file_id_from_loaded_file_data(
            self.current_file
        )
        if not (new_file_id == old_version_id):
            error_message, error_code = Errors.file_id_changed(
                old_version_id, new_file_id
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        # True - the id has not changed.
        return True

    @error_codes("BC106")
    def is_valid_fromversion_on_modified(self) -> bool:
        """Check that the fromversion property was not changed on existing Content files.

        Returns:
            (bool): Whether the files' fromversion as been modified or not.
        """
        if not self.old_file:
            return True

        from_version_new = self.current_file.get(
            "fromversion"
        ) or self.current_file.get("fromVersion")
        from_version_old = self.old_file.get("fromversion") or self.old_file.get(
            "fromVersion"
        )

        # if in old file there was no fromversion ,format command will add from version key with 4.1.0
        if not from_version_old and from_version_new == OLD_FILE_DEFAULT_1_FROMVERSION:
            return True

        if from_version_old != from_version_new:
            error_message, error_code = Errors.from_version_modified()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    @error_codes("BA100")
    def _is_valid_version(self) -> bool:
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.current_file.get("version") != self.DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(self.DEFAULT_VERSION)
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                self.is_valid = False
                return False
        return True

    @error_codes("BA111")
    def name_does_not_contain_excluded_word(self) -> bool:
        """
        Checks whether given object contains excluded word.
        Returns:
            (bool) False if display name corresponding to file path contains excluded word, true otherwise.
        """
        name = get_file_displayed_name(self.file_path)
        if not name:
            return True
        lowercase_name = name.lower()
        if any(
            excluded_word in lowercase_name
            for excluded_word in EXCLUDED_DISPLAY_NAME_WORDS
        ):
            error_message, error_code = Errors.entity_name_contains_excluded_word(
                name, EXCLUDED_DISPLAY_NAME_WORDS
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @staticmethod
    def is_release_branch() -> bool:
        """Check if we are working on a release branch.

        Returns:
            (bool): is release branch
        """
        git_util = GitUtil(repo=Content.git())
        main_branch = git_util.handle_prev_ver()[1]
        if not main_branch.startswith("origin"):
            main_branch = "origin/" + main_branch

        diff_string_config_yml = run_command(
            f"git diff {main_branch} .circleci/config.yml"
        )
        if re.search(r'[+-][ ]+CONTENT_VERSION: ".*', diff_string_config_yml):
            return True
        return False

    @staticmethod
    def is_subset_dictionary(new_dict: dict, old_dict: dict) -> bool:
        """Check if the new dictionary is a sub set of the old dictionary.

        Args:
            new_dict (dict): current branch result from _get_command_to_args
            old_dict (dict): master branch result from _get_command_to_args

        Returns:
            bool. Whether the new dictionary is a sub set of the old dictionary.
        """
        for arg, required in old_dict.items():
            if arg not in new_dict.keys():
                return False

            if required != new_dict[arg] and new_dict[arg]:
                return False

        for arg, required in new_dict.items():
            if arg not in old_dict.keys() and required:
                return False
        return True

    @error_codes("BA101")
    def _is_id_equals_name(self, file_type):
        """Validates that the id of a content item matches its name attribute.
         Args:
            file_type (str): the file type. can be 'integration', 'script', 'playbook', 'dashboard'

        Returns:
            bool. Whether the id attribute is equal to the name attribute.
        """

        id_ = _get_file_id(file_type, self.current_file)
        name = self.current_file.get("name", "")
        if id_ != name:
            error_message, error_code = Errors.id_should_equal_name(
                name, id_, self.file_path
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False

        return True

    def _load_conf_file(self):
        with open(CONF_PATH) as data_file:
            return json.load(data_file)

    @error_codes("CJ104,CJ102")
    def are_tests_registered_in_conf_json_file_or_yml_file(
        self, test_playbooks: list
    ) -> bool:
        """
        If the file is a test playbook:
            Validates it is registered in conf.json file
        If the file is an integration:
            Validating it is registered in conf.json file or that the yml file has 'No tests' under 'tests' key
        Args:
            test_playbooks: The yml file's list of test playbooks

        Returns:
            True if all test playbooks are configured in conf.json
        """
        no_tests_explicitly = any(
            test for test in test_playbooks if "no test" in test.lower()
        )
        if no_tests_explicitly:
            return True
        conf_json_tests = self._load_conf_file()["tests"]
        file_type = self.structure_validator.scheme_name
        if not isinstance(file_type, str):
            file_type = file_type.value  # type: ignore

        content_item_id = _get_file_id(file_type, self.current_file)

        # Test playbook case
        if file_type == "testplaybook":
            is_configured_test = any(
                test_config
                for test_config in conf_json_tests
                if is_test_config_match(test_config, test_playbook_id=content_item_id)
            )
            if not is_configured_test:
                missing_test_playbook_configurations = json.dumps(
                    {"playbookID": content_item_id}, indent=4
                )
                missing_integration_configurations = json.dumps(
                    {"integrations": "<integration ID>", "playbookID": content_item_id},
                    indent=4,
                )
                error_message, error_code = Errors.test_playbook_not_configured(
                    content_item_id,
                    missing_test_playbook_configurations,
                    missing_integration_configurations,
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        # Integration case
        elif file_type == "integration":
            # Not stated no tests explicitly and has not tests in yml.
            is_configured_test = any(
                test_config
                for test_config in conf_json_tests
                if is_test_config_match(test_config, integration_id=content_item_id)
            )

            unconfigured_test_playbook_ids = []

            if test_playbooks:
                configured_tests = []
                for test_playbook in test_playbooks:
                    test_config_matches = []
                    for test_config in conf_json_tests:
                        test_config_matches.append(
                            is_test_config_match(
                                test_config,
                                test_playbook_id=test_playbook,
                                integration_id=content_item_id,
                            )
                        )
                    found_match = any(test_config_matches)
                    configured_tests.append(found_match)
                    if not found_match:
                        unconfigured_test_playbook_ids.append(test_playbook)

                is_configured_test = all(configured_tests)

            if not is_configured_test:
                missing_test_playbook_configurations = json.dumps(
                    {
                        "integrations": content_item_id,
                        "playbookID": "<TestPlaybook ID>",
                    },
                    indent=4,
                )
                if unconfigured_test_playbook_ids:
                    missing_test_playbook_configurations = json.dumps(
                        [
                            {
                                "integrations": content_item_id,
                                "playbookID": test_playbook_id,
                            }
                            for test_playbook_id in unconfigured_test_playbook_ids
                        ],
                        indent=4,
                    )

                no_tests_key = yaml.dumps({"tests": ["No tests"]})
                error_message, error_code = Errors.integration_not_registered(
                    self.file_path, missing_test_playbook_configurations, no_tests_key
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        return True

    @error_codes("CJ103")
    def yml_has_test_key(self, test_playbooks: list, file_type: str) -> bool:
        """
        Checks if tests are configured.
        If not: prints an error message according to the file type and return the check result
        Args:
            test_playbooks: The yml file's list of test playbooks
            file_type: The file type, could be an integration or a playbook.

        Returns:
            True if tests are configured (not None and not an empty list) otherwise return False.
        """
        if not test_playbooks:
            error_message, error_code = Errors.no_test_playbook(
                self.file_path, file_type
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any(
            (
                feature_branch_name in self.prev_ver
                or feature_branch_name in self.branch_name
            )
            for feature_branch_name in FEATURE_BRANCHES
        ) or self.file_path.endswith("reputations.json"):
            return False

        return True

    @error_codes("BA117")
    def are_fromversion_and_toversion_in_correct_format(self) -> bool:

        if self.file_path.endswith(".json"):
            from_version = (
                self.current_file.get("fromVersion", "00.00.00") or "00.00.00"
            )
            to_version = self.current_file.get("toVersion", "00.00.00") or "00.00.00"
        elif self.file_path.endswith(".yml"):
            from_version = (
                self.current_file.get("fromversion", "00.00.00") or "00.00.00"
            )
            to_version = self.current_file.get("toversion", "00.00.00") or "00.00.00"
        else:
            raise ValueError(f"{self.file_path} is not json or yml type")

        for field, name in ((from_version, "fromversion"), (to_version, "toversion")):
            if not FROM_TO_VERSION_REGEX.fullmatch(field):
                error_message, error_code = Errors.incorrect_from_to_version_format(
                    name
                )
                self.handle_error(error_message, error_code, file_path=self.file_path)
                return False
        return True

    @error_codes("BA118")
    def are_fromversion_toversion_synchronized(self) -> bool:

        if self.file_path.endswith(".json"):
            from_version = self.current_file.get("fromVersion", "")
            to_version = self.current_file.get("toVersion", "")
        elif self.file_path.endswith(".yml"):
            from_version = self.current_file.get("fromversion", "")
            to_version = self.current_file.get("toversion", "")
        else:
            raise ValueError(f"{self.file_path} is not json or yml type")

        if not from_version or not to_version:
            logger.debug(
                f"either not from_version or not to_version in {self.file_path}, considering them synced"
            )
            return True

        if version.parse(to_version) < version.parse(from_version):
            error_message, error_code = Errors.mismatching_from_to_versions()
            self.handle_error(error_message, error_code, file_path=self.file_path)
            return False
        return True

    @error_codes("BA106")
    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
        This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.file_path.endswith(".json"):
            from_version_field = "fromVersion"
        elif self.file_path.endswith(".yml"):
            from_version_field = "fromversion"
        else:
            return True

        if LooseVersion(
            self.current_file.get(from_version_field, DEFAULT_CONTENT_ITEM_FROM_VERSION)
        ) < LooseVersion(self.oldest_supported_version):
            error_message, error_code = Errors.no_minimal_fromversion_in_file(
                from_version_field, self.oldest_supported_version
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False

        return True

    @error_codes("BA106")
    def is_valid_fromversion_for_generic_objects(self):
        """
        Check if the file has a fromversion 6.5.0 or higher
        This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if LooseVersion(
            self.current_file.get("fromVersion", DEFAULT_CONTENT_ITEM_FROM_VERSION)
        ) < LooseVersion(GENERIC_OBJECTS_OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file(
                "fromVersion", GENERIC_OBJECTS_OLDEST_SUPPORTED_VERSION
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False

        return True

    @staticmethod
    def remove_separators_from_name(base_name) -> str:
        """
        Removes separators from a given name of folder or file.

        Args:
            base_name: The base name of the folder/file.

        Return:
            The base name without separators.
        """

        for separator in ENTITY_NAME_SEPARATORS:

            if separator in base_name:
                base_name = base_name.replace(separator, "")

        return base_name

    @error_codes("BA113")
    def is_there_spaces_in_the_end_of_name(self):
        """Validate that the id of the file equals to the name.
        Returns:
            bool. Whether the file's name ends with spaces
        """
        name = self.current_file.get("name", "")
        if name != name.strip():
            error_message, error_code = Errors.spaces_in_the_end_of_name(name)
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False

        return True

    @error_codes("BA112")
    def is_there_spaces_in_the_end_of_id(self):
        """Validate that the id of the file equals to the name.
        Returns:
           bool. Whether the file's id ends with spaces
        """
        file_id = self.structure_validator.get_file_id_from_loaded_file_data(
            self.current_file
        )
        if file_id and file_id != file_id.strip():
            error_message, error_code = Errors.spaces_in_the_end_of_id(file_id)
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False

        return True

    @error_codes("RM109")
    def validate_readme_exists(self, validate_all: bool = False):
        """
        Validates if there is a readme file in the same folder as the caller file.
        The validation is processed only on added or modified files.

        Args:
            validate_all: (bool) is the validation being run with -a
        Return:
           True if the readme file exits False with an error otherwise

        Note: APIModules don't need readme file (issue 47965).
        """
        if validate_all or API_MODULES_PACK in self.file_path:
            return True

        file_path = os.path.normpath(self.file_path)
        path_split = file_path.split(os.sep)
        file_type = find_type(self.file_path, _dict=self.current_file, file_type="yml")
        if file_type == FileType.PLAYBOOK:
            to_replace = os.path.splitext(path_split[-1])[-1]
            readme_path = file_path.replace(to_replace, "_README.md")
        elif file_type in {FileType.SCRIPT, FileType.INTEGRATION}:
            if path_split[-2] in ["Scripts", "Integrations"]:
                to_replace = os.path.splitext(file_path)[-1]
                readme_path = file_path.replace(to_replace, "_README.md")
            else:
                to_replace = path_split[-1]
                readme_path = file_path.replace(to_replace, "README.md")
        else:
            return True

        if os.path.isfile(readme_path):
            return True

        error_message, error_code = Errors.missing_readme_file(file_type)
        if self.handle_error(
            error_message,
            error_code,
            file_path=self.file_path,
            suggested_fix=Errors.suggest_fix(self.file_path, cmd="generate-docs"),
        ):
            return False

        return True
