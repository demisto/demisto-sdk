import json
import os
import re
from abc import abstractmethod

import yaml
from demisto_sdk.commands.common.constants import Errors
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (_get_file_id,
                                               get_latest_release_notes_text,
                                               get_release_notes_file_path,
                                               is_test_config_match,
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
                print_error(f'Missing release notes for: {self.file_path} in {rn_path}')
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
            print_error("The File's name, which is: '{}', should be equal to its ID, which is: '{}'."
                        " please update the file (path to file: {}).".format(name, file_id, self.file_path))
            print_error(Errors.suggest_fix(self.file_path))
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

        content_item_id = _get_file_id(self.structure_validator.scheme_name, self.current_file)
        file_type = self.structure_validator.scheme_name
        # Test playbook case

        if 'TestPlaybooks' in self.file_path and file_type == 'playbook':
            is_configured_test = any(test_config for test_config in conf_json_tests if
                                     is_test_config_match(test_config, test_playbook_id=content_item_id))
            if not is_configured_test:
                missing_test_playbook_configurations = json.dumps({'playbookID': content_item_id}, indent=4)
                missing_integration_configurations = json.dumps(
                    {'integrations': '<integration ID>', 'playbookID': content_item_id},
                    indent=4)
                error_message = \
                    f'The TestPlaybook {content_item_id} is not registered in {self.CONF_PATH} file.\n' \
                    f'Please add\n{missing_test_playbook_configurations}\n' \
                    f'or if this test playbook is for an integration\n{missing_integration_configurations}\n' \
                    f'to {self.CONF_PATH} path under \'tests\' key.'
                print_error(error_message)
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
                error_message = \
                    f'The following integration is not registered in {self.CONF_PATH} file.\n' \
                    f'Please add\n{missing_test_playbook_configurations}\nto {self.CONF_PATH} ' \
                    f'path under \'tests\' key.\n' \
                    f'If you don\'t want to add a test playbook for this integration, ' \
                    f'please add \n{no_tests_key}to the ' \
                    f'file {self.file_path} or run \'demisto-sdk format -p {self.file_path}\''
                print_error(error_message)
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
            print_error(
                f'You don\'t have a TestPlaybook for {file_type} {self.file_path}. '
                f'If you have a TestPlaybook for this {file_type}, '
                f'please edit the yml file and add the TestPlaybook under the \'tests\' key. '
                f'If you don\'t want to create a'
                f' TestPlaybook for this {file_type}, edit the yml file and add  \ntests:\n -  No tests\n lines'
                f' to it or run \'demisto-sdk format -i {self.file_path}\'')
            return False
        return True
