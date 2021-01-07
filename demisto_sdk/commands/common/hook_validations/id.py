import json
import os
import re
from collections import OrderedDict

import click
import demisto_sdk.commands.common.constants as constants
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.update_id_set import (get_incident_type_data,
                                                       get_integration_data,
                                                       get_playbook_data,
                                                       get_script_data)
from demisto_sdk.commands.unify.unifier import Unifier


class IDSetValidator(BaseValidator):
    """IDSetValidator was designed to make sure we create the id_set.json in the correct way so we can use it later on.

    The id_set.json file is created using the update_id_set.py script. It contains all the data from the various
    executables we have in Content repository - Playbooks/Scripts/Integration. The script extracts the command and
    script names so we will later on will be able to use it in the test filtering we have in our build system.

    Attributes:
        is_circle (bool): whether we are running on circle or local env.
        id_set (dict): Dictionary that hold all the data from the id_set.json file.
        script_set (set): Set of all the data regarding scripts in our system.
        playbook_set (set): Set of all the data regarding playbooks in our system.
        integration_set (set): Set of all the data regarding integrations in our system.
        test_playbook_set (set): Set of all the data regarding test playbooks in our system.
    """
    SCRIPTS_SECTION = "scripts"
    PLAYBOOK_SECTION = "playbooks"
    INTEGRATION_SECTION = "integrations"
    TEST_PLAYBOOK_SECTION = "TestPlaybooks"

    ID_SET_PATH = "./Tests/id_set.json"

    def __init__(self, is_test_run=False, is_circle=False, configuration=Configuration(), ignored_errors=None,
                 print_as_warnings=False, suppress_print=False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print)
        self.is_circle = is_circle
        self.configuration = configuration
        if not is_test_run and self.is_circle:
            self.id_set = self.load_id_set()
            self.id_set_path = os.path.join(self.configuration.env_dir, 'configs', 'id_set.json')
            self.script_set = self.id_set[self.SCRIPTS_SECTION]
            self.playbook_set = self.id_set[self.PLAYBOOK_SECTION]
            self.integration_set = self.id_set[self.INTEGRATION_SECTION]
            self.test_playbook_set = self.id_set[self.TEST_PLAYBOOK_SECTION]

    def load_id_set(self):
        with open(self.ID_SET_PATH, 'r') as id_set_file:
            try:
                id_set = json.load(id_set_file)
            except ValueError as ex:
                if "Expecting property name" in str(ex):
                    error_message, error_code = Errors.id_set_conflicts()
                    if self.handle_error(error_message, error_code, file_path="id_set.json"):
                        raise
                    else:
                        pass

                raise

            return id_set

    def _is_playbook_found(self, incident_type_data):
        """Check if the playbook is in the id_set

        Args:
            incident_type_data (dict): Dictionary that holds the extracted details from the given incident type.

        Returns:
            bool. Whether the playbook is in the id_set or not.
        """
        is_valid = True
        incident_type_name = list(incident_type_data.keys())[0]
        incident_type_playbook = incident_type_data[incident_type_name].get('playbooks')
        if incident_type_playbook:
            # setting initially to false, if the default playbook is in the id_set, it will be valid
            is_valid = False
            for checked_playbook in self.playbook_set:
                checked_playbook_name = list(checked_playbook.keys())[0]
                if incident_type_playbook == checked_playbook_name:
                    is_valid = True
                    break
            if not is_valid:  # add error message if not valid
                error_message, error_code = Errors.incident_type_non_existent_playbook_id(incident_type_name,
                                                                                          incident_type_playbook)
                self.handle_error(error_message, error_code, file_path="id_set.json")

        return is_valid

    def _is_non_real_command_found(self, script_data):
        """Check if the script depend-on section has a non real command

        Args:
            script_data (dict): Dictionary that holds the extracted details from the given script.

        Returns:
            bool. Whether the script is valid or not.
        """
        is_valid = True
        depends_on_commands = script_data.get('depends_on')
        for command in depends_on_commands:
            if command != 'test-module':
                if command.endswith('dev') or command.endswith('copy'):
                    error_message, error_code = Errors.invalid_command_name_in_script(script_data.get('name'),
                                                                                      command)
                    self.handle_error(error_message, error_code, file_path="id_set.json")
                    return not is_valid
        return is_valid

    def _is_valid_in_id_set(self, file_path: str, obj_data: OrderedDict, obj_set: list):
        """Check if the file is represented correctly in the id_set

        Args:
            file_path (string): Path to the file.
            obj_data (dict): Dictionary that holds the extracted details from the given file.
            obj_set (set): The set in which the file should be located at.

        Returns:
            bool. Whether the file is represented correctly in the id_set or not.
        """
        is_found = False
        file_id = list(obj_data.keys())[0]

        for checked_instance in obj_set:
            checked_instance_id = list(checked_instance.keys())[0]
            checked_instance_data = checked_instance[checked_instance_id]
            checked_instance_toversion = checked_instance_data.get('toversion', '99.99.99')
            checked_instance_fromversion = checked_instance_data.get('fromversion', '0.0.0')
            obj_to_version = obj_data[file_id].get('toversion', '99.99.99')
            obj_from_version = obj_data[file_id].get('fromversion', '0.0.0')
            if checked_instance_id == file_id and checked_instance_toversion == obj_to_version and \
                    checked_instance_fromversion == obj_from_version:
                is_found = True
                if checked_instance_data != obj_data[file_id]:
                    error_message, error_code = Errors.id_set_not_updated(file_path)
                    if self.handle_error(error_message, error_code, file_path="id_set.json"):
                        return False

        if not is_found:
            error_message, error_code = Errors.id_set_not_updated(file_path)
            if not self.handle_error(error_message, error_code, file_path="id_set.json"):
                return True

        return is_found

    def is_file_valid_in_set(self, file_path, file_type):
        """Check if the file is valid in the id_set

        Args:
            file_path (string): Path to the file.
            file_type (string): The file type.

        Returns:
            bool. Whether the file is represented correctly in the id_set or not.
        """
        is_valid = True
        if self.is_circle:  # No need to check on local env because the id_set will contain this info after the commit
            click.echo(f"id set validations for: {file_path}")
            if re.match(constants.PLAYBOOK_REGEX, file_path, re.IGNORECASE):
                playbook_data = OrderedDict(get_playbook_data(file_path))
                is_valid = self._is_valid_in_id_set(file_path, playbook_data, self.playbook_set)

            elif re.match(constants.TEST_PLAYBOOK_REGEX, file_path, re.IGNORECASE):
                playbook_data = OrderedDict(get_playbook_data(file_path))
                is_valid = self._is_valid_in_id_set(file_path, playbook_data, self.test_playbook_set)

            elif re.match(constants.TEST_SCRIPT_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_SCRIPT_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE):
                script_data = get_script_data(file_path)
                is_valid = self._is_valid_in_id_set(file_path, script_data, self.script_set)

            elif re.match(constants.PACKS_INTEGRATION_YML_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE):
                integration_data = get_integration_data(file_path)
                is_valid = self._is_valid_in_id_set(file_path, integration_data, self.integration_set)

            elif re.match(constants.PACKS_SCRIPT_YML_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_SCRIPT_PY_REGEX, file_path, re.IGNORECASE):
                unifier = Unifier(os.path.dirname(file_path))
                yml_path, code = unifier.get_script_or_integration_package_data()
                script_data = get_script_data(yml_path, script_code=code)
                is_valid = (self._is_valid_in_id_set(yml_path, script_data, self.script_set) and
                            self._is_non_real_command_found(script_data))

            elif file_type == constants.FileType.INCIDENT_TYPE:
                incident_type_data = OrderedDict(get_incident_type_data(file_path))
                is_valid = self._is_playbook_found(incident_type_data)

        return is_valid
