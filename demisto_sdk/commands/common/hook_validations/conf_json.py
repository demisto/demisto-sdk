import json
from pathlib import Path

from demisto_sdk.commands.common.constants import (API_MODULES_PACK, CONF_PATH,
                                                   FileType)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import _get_file_id, get_pack_name


class ConfJsonValidator(BaseValidator):
    """ConfJsonValidator has been designed to make sure we are following the standards for the conf.json file.

    Attributes:
        _is_valid (bool): Whether the conf.json file current state is valid or not.
        conf_data (dict): The data from the conf.json file in our repo.
    """
    CONF_PATH = "./Tests/conf.json"
    DYNAMIC_SECTION_TAG = 'dynamic-section'

    def __init__(self, ignored_errors=None, print_as_warnings=False, suppress_print=False, json_file_path=None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self._is_valid = True
        self.conf_data = self.load_conf_file()

    def load_conf_file(self):
        with open(self.CONF_PATH) as data_file:
            return json.load(data_file)

    def is_valid_conf_json(self):
        """Validate the fields skipped_tests, skipped_integrations and unmockable_integrations in conf.json file."""
        print('\nValidating conf.json')
        skipped_tests_conf = self.conf_data['skipped_tests']
        skipped_integrations_conf = self.conf_data['skipped_integrations']
        unmockable_integrations_conf = self.conf_data['unmockable_integrations']

        self.is_valid_description_in_conf_dict(skipped_tests_conf)
        self.is_valid_description_in_conf_dict(skipped_integrations_conf)
        self.is_valid_description_in_conf_dict(unmockable_integrations_conf)

        return self._is_valid

    def is_valid_description_in_conf_dict(self, checked_dict):
        """Validate that the checked_dict has description for all it's fields.

        Args:
            checked_dict (dict): Dictionary from conf.json file.
        """
        problematic_instances = []
        for instance, description in checked_dict.items():
            if description == "":
                problematic_instances.append(instance)

        if problematic_instances:
            error_message, error_code = Errors.description_missing_from_conf_json(problematic_instances)
            if self.handle_error(error_message, error_code, file_path=CONF_PATH):
                self._is_valid = False

        return self._is_valid

    def is_test_in_conf_json(self, file_id):
        """Check if the file_id(We get this ID only if it is a test) is located in the tests section in conf.json file.

        Args:
            file_id (string): the ID of the test we are looking for in the conf.json file.

        Returns:
            bool. Whether the test as been located in the conf.json file or not.
        """
        conf_tests = self.conf_data['tests']
        for test in conf_tests:
            playbook_id = test['playbookID']
            if file_id == playbook_id:
                return True

        error_message, error_code = Errors.test_not_in_conf_json(file_id)
        if self.handle_error(error_message, error_code, file_path=CONF_PATH):
            return False
        return True

    def is_valid_file_in_conf_json(self, current_file, file_type, file_path):
        """Check if the file is valid in the conf.json"""
        entity_id = _get_file_id(file_type.value, current_file)
        if file_type in {FileType.INTEGRATION, FileType.BETA_INTEGRATION}:
            return self.integration_has_unskipped_test_playbook(current_file, entity_id, file_path)
        if file_type == FileType.SCRIPT:
            return self.has_unskipped_test_playbook(current_file=current_file,
                                                    entity_id=entity_id,
                                                    file_path=file_path)
        return True

    def has_unskipped_test_playbook(self, current_file, entity_id, file_path, test_playbook_ids=None):
        """Check if the content entity has at least one unskipped test playbook.

        Collect test playbook ids from the `tests` field in the file, merge them with
        provided test_playbook_ids and validate at least one is unskipped.

        Args:
            current_file: The file to check.
            entity_id: The id of the entity to check.
            file_path: The file path of the entity to check.
            test_playbook_ids: test_playbook_ids unrelated to `tests` field in the file.

        Returns:
            True if the content entity has at least one unskipped test playbook.
        """
        # If it has a dynamic section tag, it shouldn't have a test playbook.
        if self.DYNAMIC_SECTION_TAG in current_file.get('tags', []):
            return True
        if test_playbook_ids is None:
            test_playbook_ids = []
        test_playbooks_unskip_status = {}
        all_test_playbook_ids = test_playbook_ids.copy()
        skipped_tests = self.conf_data.get('skipped_tests', {})

        # do not check this validation for ApiModules pack
        if get_pack_name(file_path) == API_MODULES_PACK:
            return self._is_valid

        if isinstance(current_file.get('tests'), list):
            all_test_playbook_ids.extend(current_file.get('tests', []))

        for test_playbook_id in set(all_test_playbook_ids):
            if (skipped_tests and test_playbook_id in skipped_tests) or 'No test' in test_playbook_id:
                test_playbooks_unskip_status[test_playbook_id] = False
            else:
                test_playbooks_unskip_status[test_playbook_id] = True

        if not any(test_playbooks_unskip_status.values()) and not self.has_unittest(file_path):
            error_message, error_code = Errors.all_entity_test_playbooks_are_skipped(entity_id)
            if self.handle_error(error_message, error_code, file_path=file_path):
                self._is_valid = False
        return self._is_valid

    def integration_has_unskipped_test_playbook(self, integration_data, integration_id, file_path):
        """Validate there is at least one unskipped test playbook."""
        test_playbook_ids = []
        conf_tests = self.conf_data.get('tests', [])
        for test in conf_tests:
            if 'integrations' in test:
                if (isinstance(test['integrations'], str) and integration_id == test['integrations']) or \
                        integration_id in list(test['integrations']):
                    test_playbook_ids.append(test['playbookID'])

        return self.has_unskipped_test_playbook(integration_data, integration_id, file_path, test_playbook_ids)

    def get_test_path(self, file_path):
        """ Gets a yml path and returns the matching integration's test."""
        test_path = Path(file_path)
        test_file_name = test_path.parts[-1].replace('.yml', '_test.py')
        return test_path.parent / test_file_name

    def has_unittest(self, file_path):
        """ Checks if the tests file exist. If so, Test Playbook is not a must. """
        test_path = self.get_test_path(file_path)

        # We only check existence as we have coverage report to check the actual tests
        if not test_path.exists():
            return False

        return True
