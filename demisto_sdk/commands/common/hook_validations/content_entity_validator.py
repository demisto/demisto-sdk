import json
import re
from abc import abstractmethod
from distutils.version import LooseVersion
from typing import Optional

import yaml
from demisto_sdk.commands.common.constants import (ENTITY_NAME_SEPARATORS,
                                                   FEATURE_BRANCHES,
                                                   OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (_get_file_id,
                                               is_test_config_match,
                                               run_command)


class ContentEntityValidator(BaseValidator):
    DEFAULT_VERSION = -1
    CONF_PATH = "./Tests/conf.json"

    def __init__(self, structure_validator, ignored_errors=None, print_as_warnings=False, skip_docker_check=False,
                 suppress_print=False, json_file_path=None):
        # type: (StructureValidator, dict, bool, bool, bool, Optional[str]) -> None
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.structure_validator = structure_validator
        self.current_file = structure_validator.current_file
        self.old_file = structure_validator.old_file
        self.file_path = structure_validator.file_path
        self.is_valid = structure_validator.is_valid
        self.skip_docker_check = skip_docker_check
        self.prev_ver = structure_validator.prev_ver
        self.branch_name = structure_validator.branch_name

    def is_valid_file(self, validate_rn=True):
        tests = [
            self.is_valid_version(),
            self.is_valid_fromversion()
        ]
        return all(tests)

    @abstractmethod
    def is_valid_version(self):
        # type: () -> bool
        pass

    def _is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.current_file.get('version') != self.DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(self.DEFAULT_VERSION)
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 suggested_fix=Errors.suggest_fix(self.file_path), warning=self.quite_bc):
                self.is_valid = False
                return False
        return True

    @staticmethod
    def is_release_branch():
        # type: () -> bool
        """Check if we are working on a release branch.

        Returns:
            (bool): is release branch
        """
        diff_string_config_yml = run_command("git diff origin/master .circleci/config.yml")
        if re.search(r'[+-][ ]+CONTENT_VERSION: ".*', diff_string_config_yml):
            return True
        return False

    @staticmethod
    def is_subset_dictionary(new_dict, old_dict):
        # type: (dict, dict) -> bool
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

    def _is_id_equals_name(self, file_type):
        """Validate that the id of the file equals to the name.
         Args:
            file_type (str): the file type. can be 'integration', 'script', 'playbook', 'dashboard', 'id'

        Returns:
            bool. Whether the file's id is equal to to its name
        """

        file_id = _get_file_id(file_type, self.current_file)
        name = self.current_file.get('name', '')
        if file_id != name:
            error_message, error_code = Errors.id_should_equal_name(name, file_id)
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 suggested_fix=Errors.suggest_fix(self.file_path)):
                return False

        return True

    def _load_conf_file(self):
        with open(self.CONF_PATH) as data_file:
            return json.load(data_file)

    def are_tests_registered_in_conf_json_file_or_yml_file(self, test_playbooks: list) -> bool:
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
        no_tests_explicitly = any(test for test in test_playbooks if 'no test' in test.lower())
        if no_tests_explicitly:
            return True
        conf_json_tests = self._load_conf_file()['tests']
        file_type = self.structure_validator.scheme_name
        if not isinstance(file_type, str):
            file_type = file_type.value  # type: ignore

        content_item_id = _get_file_id(file_type, self.current_file)

        # Test playbook case
        if file_type == 'testplaybook':
            is_configured_test = any(test_config for test_config in conf_json_tests if
                                     is_test_config_match(test_config, test_playbook_id=content_item_id))
            if not is_configured_test:
                missing_test_playbook_configurations = json.dumps({'playbookID': content_item_id}, indent=4)
                missing_integration_configurations = json.dumps(
                    {'integrations': '<integration ID>', 'playbookID': content_item_id},
                    indent=4)
                error_message, error_code = Errors.test_playbook_not_configured(content_item_id,
                                                                                missing_test_playbook_configurations,
                                                                                missing_integration_configurations)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        # Integration case
        elif file_type == 'integration':
            is_configured_test = any(
                test_config for test_config in conf_json_tests if is_test_config_match(test_config,
                                                                                       integration_id=content_item_id))
            if not is_configured_test:
                missing_test_playbook_configurations = json.dumps(
                    {'integrations': content_item_id, 'playbookID': '<TestPlaybook ID>'},
                    indent=4)
                no_tests_key = yaml.dump({'tests': ['No tests']})
                error_message, error_code = Errors.integration_not_registered(self.file_path,
                                                                              missing_test_playbook_configurations,
                                                                              no_tests_key)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True

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
            error_message, error_code = Errors.no_test_playbook(self.file_path, file_type)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.prev_ver or feature_branch_name in self.branch_name)
               for feature_branch_name in FEATURE_BRANCHES) or self.file_path.endswith('reputations.json'):
            return False

        return True

    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.file_path.endswith('json'):
            if LooseVersion(self.current_file.get('fromVersion', '0.0.0')) < LooseVersion(OLDEST_SUPPORTED_VERSION):
                error_message, error_code = Errors.no_minimal_fromversion_in_file('fromVersion',
                                                                                  OLDEST_SUPPORTED_VERSION)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        elif self.file_path.endswith('.yml'):
            if LooseVersion(self.current_file.get('fromversion', '0.0.0')) < LooseVersion(OLDEST_SUPPORTED_VERSION):
                error_message, error_code = Errors.no_minimal_fromversion_in_file('fromversion',
                                                                                  OLDEST_SUPPORTED_VERSION)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True

    @staticmethod
    def check_separators_in_name(base_name) -> list:
        """
        Check if there are separators in a given name of folder or file.

        Args:
            base_name: The base name of the folder/file.

        Return:
            list of separators found in the name.
        """
        separators = []

        for separator in ENTITY_NAME_SEPARATORS:

            if separator in base_name:
                separators.append(separator)

        return separators
