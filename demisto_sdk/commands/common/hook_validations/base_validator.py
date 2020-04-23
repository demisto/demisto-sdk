import json
import os
import re
from abc import abstractmethod

from demisto_sdk.commands.common.constants import (ID_IN_COMMONFIELDS,
                                                   ID_IN_ROOT, Errors)
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (get_latest_release_notes_text,
                                               get_release_notes_file_path,
                                               print_error, run_command)


class BaseValidator:
    DEFAULT_VERSION = -1
    CONF_PATH = "./Tests/conf.json"

    def __init__(self, structure_validator):
        # type: (StructureValidator) -> None
        self.structure_validator = structure_validator
        self.current_file = structure_validator.current_file
        self.old_file = structure_validator.old_file
        self.file_path = structure_validator.file_path
        self.is_valid = structure_validator.is_valid

    def is_valid_file(self, validate_rn=True):
        tests = [
            self.is_valid_version()
        ]
        # In case of release branch we allow to remove release notes
        if validate_rn and not self.is_release_branch():
            tests.append(self.is_there_release_notes())
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
            print_error(Errors.wrong_version(self.file_path, self.DEFAULT_VERSION))
            print_error(Errors.suggest_fix(self.file_path))
            self.is_valid = False
            return False
        return True

    def is_there_release_notes(self):
        """Validate that the file has proper release notes when modified.
        This function updates the class attribute self._is_valid.

        Returns:
            (bool): is there release notes
        """
        if os.path.isfile(self.file_path):
            rn_path = get_release_notes_file_path(self.file_path)
            release_notes = get_latest_release_notes_text(rn_path)

            # check release_notes file exists and contain text
            if release_notes is None:
                self.is_valid = False
                print_error("Missing release notes for: {}".format(self.file_path))
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

    def _get_file_id(self, file_type):
        file_id = ''
        if file_type in ID_IN_ROOT:
            file_id = self.current_file.get('id')
        elif file_type in ID_IN_COMMONFIELDS:
            file_id = self.current_file.get('commonfields', {}).get('id')
        return file_id

    def _is_id_equals_name(self, file_type):
        """Validate that the id of the file equals to the name.
         Args:
            file_type (str): the file type. can be 'integration', 'script', 'playbook', 'dashboard', 'id'

        Returns:
            bool. Whether the file's id is equal to to its name
        """

        file_id = self._get_file_id(file_type)
        name = self.current_file.get('name', '')
        if file_id != name:
            print_error("The File's name, which is: '{0}', should be equal to its ID, which is: '{1}'."
                        " please update the file (path to file: {2}).".format(name, file_id, self.file_path))
            print_error(Errors.suggest_fix(self.file_path))
            return False
        return True

    def _load_conf_file(self):
        with open(self.CONF_PATH) as data_file:
            return json.load(data_file)

    def are_tests_configured(self) -> bool:
        """
        Checks if a file (playbook or integration) has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        file_type = self.structure_validator.scheme_name
        tests = self.current_file.get('tests', [])
        if not self.yml_has_test_key(tests, file_type):
            return False
        return self.tests_registered_in_conf_json_file(tests)

    def tests_registered_in_conf_json_file(self, test_playbooks: list) -> bool:
        """
        Checking if test playbooks are configured in 'conf.json' unless 'No tests' is in test playbooks.
        If 'No tests' is not in test playbooks and there is a test playbook that is not configured: Will print's
        an error message and return a boolean accordingly.
        Args:
            test_playbooks: The yml file's list of test playbooks

        Returns:
            True if all test playbooks are configured in conf.json
        """
        no_tests_explicitly = any(test for test in test_playbooks if 'no test' in test.lower())
        if no_tests_explicitly:
            return True
        conf_json_tests = self._load_conf_file()['tests']

        content_item_id = self._get_file_id(self.structure_validator.scheme_name)
        not_registered_tests = self.get_not_registered_tests(conf_json_tests, content_item_id, test_playbooks)
        if not_registered_tests:
            file_type = self.structure_validator.scheme_name
            if file_type == 'integration':
                missing_test_configurations = json.dumps([
                    {'integrations': content_item_id, 'playbookID': test} for test in not_registered_tests
                ], indent=4).strip('[]')
            else:
                missing_test_configurations = json.dumps([
                    {'playbookID': test} for test in not_registered_tests
                ], indent=4).strip('[]')
            error_message = \
                f'The following TestPlaybooks are not registered in {self.CONF_PATH} file.\n' \
                f'Please add\n{missing_test_configurations}\nto {self.CONF_PATH} path under \'tests\' key.'
            print_error(error_message)
            return False
        return True

    def get_not_registered_tests(self, conf_json_tests: list, content_item_id: str, test_playbooks: list) -> list:
        """
        Return all test playbooks that are not configured in conf.json file
        Args:
            conf_json_tests: the 'tests' value of 'conf.json file
            content_item_id: A content item ID, could be a script, an integration or a playbook.
            test_playbooks: The yml file's list of test playbooks

        Returns:
            A list of TestPlaybooks not configured
        """
        not_registered_tests = []
        file_type = self.structure_validator.scheme_name
        for test in test_playbooks:
            test_registered_in_conf_json = any(
                test_config for test_config in conf_json_tests if self.find_test_match(test_config,
                                                                                       test,
                                                                                       content_item_id,
                                                                                       file_type)
            )
            if not test_registered_in_conf_json:
                not_registered_tests.append(test)
        return not_registered_tests

    def yml_has_test_key(self, test_playbooks: list, file_type: str) -> bool:
        """
        Checks if tests are configured.
        If not: prints an error message according to the file type and return the check result
        Args:
            test_playbooks: The yml file's list of test playbooks
            file_type: The file type, could be a script, an integration or a playbook.

        Returns:
            True if tests are configured (not None and not an empty list) otherwise return False.
        """
        if not test_playbooks:
            print_error(
                f'You don\'t have a TestPlaybook for {file_type} {self.file_path}. '
                f'If you have a TestPlaybook for this {file_type}, '
                f'please edit the yml file and add the TestPlaybook under the \'tests\' key. '
                f'If you don\'t want to create a'
                f' TestPlaybook for this {file_type}, edit the yml file and add  \ntests:\n -  No tests\n lines'
                f' to it.')
            return False
        return True

    @staticmethod
    def find_test_match(test_config: dict, test_playbook_id: str, content_item_id: str, file_type: str) -> bool:
        """
        Given a test configuration from conf.json file, this method checks if the configuration is configured for the
        test playbook with content item.
        Since in conf.json there could be test configurations with 'integrations' as strings or list of strings
        the type of test_configurations['integrations'] is checked in first and the match according to the type.
        If file type is not an integration- will return True if the test_playbook id matches playbookID.
        Args:
            file_type: The file type. can be 'integration', 'script', 'playbook'.
            test_config: A test configuration from conf.json file under 'tests' key.
            test_playbook_id: A test playbook ID.
            content_item_id: A content item ID, could be a script, an integration or a playbook.

        Returns:
            True if the test configuration contains the test playbook and the content item or False if not
        """
        if test_playbook_id != test_config.get('playbookID'):
            return False
        if file_type != 'integration':
            return True

        test_integrations = test_config.get('integrations')
        if isinstance(test_integrations, list):
            return any(
                test_integration for test_integration in test_integrations if test_integration == content_item_id)
        else:
            return test_integrations == content_item_id
