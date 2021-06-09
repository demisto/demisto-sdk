import json

from demisto_sdk.commands.common.constants import CONF_PATH, FileType
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import _get_file_id


class ConfJsonValidator(BaseValidator):
    """ConfJsonValidator has been designed to make sure we are following the standards for the conf.json file.

    Attributes:
        _is_valid (bool): Whether the conf.json file current state is valid or not.
        conf_data (dict): The data from the conf.json file in our repo.
    """
    CONF_PATH = "./Tests/conf.json"

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
        if file_type == FileType.INTEGRATION:
            return self.integration_has_unskipped_test_playbook(current_file, entity_id, file_path)
        if file_type == FileType.SCRIPT:
            return self.has_unskipped_test_playbook(current_file=current_file,
                                                    entity_id=entity_id,
                                                    file_path=file_path,
                                                    error_func=Errors.all_script_test_playbooks_are_skipped)
        return True

    def is_test_playbook_unskipped(self, test_playbook_id):
        """Check whether the playbook is not skipped."""
        skipped_tests = self.conf_data.get('skipped_tests', {})
        if skipped_tests and test_playbook_id in skipped_tests:
            return False
        return True

    def has_unskipped_test_playbook(self, current_file, entity_id, file_path, error_func, test_playbook_ids: list = []):
        """Check if the content entity has at least one unskipped test playbook."""
        test_playbooks_unskip_status = {}
        skipped_tests = self.conf_data.get('skipped_tests', {})

        if type(current_file.get('tests')) is list:
            test_playbook_ids.extend(current_file.get('tests', []))

        for test_playbook_id in set(test_playbook_ids):
            if skipped_tests and test_playbook_id in skipped_tests:
                test_playbooks_unskip_status[test_playbook_id] = False
            else:
                test_playbooks_unskip_status[test_playbook_id] = True

        if not any(test_playbooks_unskip_status.values()):
            error_message, error_code = error_func(entity_id)
            if self.handle_error(error_message, error_code, file_path=file_path):
                self._is_valid = False
            return False
        return True

    def integration_has_unskipped_test_playbook(self, integration_data, integration_id, file_path):
        """Validate there is at least one unskipped test playbook."""
        test_playbook_ids = []
        conf_tests = self.conf_data.get('tests', [])
        for test in conf_tests:
            if 'integrations' in test:
                if (type(test['integrations']) is str and integration_id == test['integrations']) or \
                        integration_id in list(test['integrations']):
                    test_playbook_ids.append(test['playbookID'])

        return self.has_unskipped_test_playbook(integration_data, integration_id, file_path,
                                                Errors.all_integration_test_playbooks_are_skipped,
                                                test_playbook_ids)
