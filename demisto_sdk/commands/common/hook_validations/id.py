import json
import os
import re
from collections import OrderedDict
from distutils.version import LooseVersion

import demisto_sdk.commands.common.constants as constants
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (collect_ids,
                                               get_script_or_integration_id)
from demisto_sdk.commands.common.update_id_set import (get_integration_data,
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
                 print_as_warnings=False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings)
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

    def is_valid_in_id_set(self, file_path: str, obj_data: OrderedDict, obj_set: list):
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

    def is_file_valid_in_set(self, file_path):
        """Check if the file is represented correctly in the id_set

        Args:
            file_path (string): Path to the file.

        Returns:
            bool. Whether the file is represented correctly in the id_set or not.
        """
        is_valid = True
        if self.is_circle:  # No need to check on local env because the id_set will contain this info after the commit
            if re.match(constants.PLAYBOOK_REGEX, file_path, re.IGNORECASE):
                playbook_data = get_playbook_data(file_path)
                is_valid = self.is_valid_in_id_set(file_path, playbook_data, self.playbook_set)

            elif re.match(constants.TEST_PLAYBOOK_REGEX, file_path, re.IGNORECASE):
                playbook_data = get_playbook_data(file_path)
                is_valid = self.is_valid_in_id_set(file_path, playbook_data, self.test_playbook_set)

            elif re.match(constants.TEST_SCRIPT_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_SCRIPT_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE):

                script_data = get_script_data(file_path)
                is_valid = self.is_valid_in_id_set(file_path, script_data, self.script_set)

            elif re.match(constants.PACKS_INTEGRATION_YML_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE):

                integration_data = get_integration_data(file_path)
                is_valid = self.is_valid_in_id_set(file_path, integration_data, self.integration_set)

            elif re.match(constants.PACKS_SCRIPT_YML_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_SCRIPT_PY_REGEX, file_path, re.IGNORECASE):

                unifier = Unifier(os.path.dirname(file_path))
                yml_path, code = unifier.get_script_or_integration_package_data()
                script_data = get_script_data(yml_path, script_code=code)
                is_valid = self.is_valid_in_id_set(yml_path, script_data, self.script_set)

        return is_valid

    def is_id_duplicated(self, obj_id: str, obj_data: OrderedDict, obj_type: str):
        """Check if the given ID already exist in the system.

        Args:
            obj_id (string): The new ID we want to add.
            obj_data (dict): Dictionary that holds the extracted details from the given file.
            obj_type (string): the type of the new file.

        Returns:
            bool. Whether the ID already exist in the system or not.
        """
        is_duplicated = False
        obj_data_list = list(obj_data.values())
        dict_value = obj_data_list[0]
        obj_toversion = dict_value.get('toversion', '99.99.99')
        obj_fromversion = dict_value.get('fromversion', '0.0.0')

        for section, section_data in self.id_set.items():
            for instance in section_data:
                instance_id = list(instance.keys())[0]
                instance_to_version = instance[instance_id].get('toversion', '99.99.99')
                instance_from_version = instance[instance_id].get('fromversion', '0.0.0')
                if obj_id == instance_id:
                    if section != obj_type and LooseVersion(obj_fromversion) < LooseVersion(instance_to_version):
                        is_duplicated = True
                        break

                    elif obj_fromversion == instance_from_version and obj_toversion == instance_to_version:
                        if instance[instance_id] != obj_data[obj_id]:
                            is_duplicated = True
                            break

                    elif (LooseVersion(obj_fromversion) <= LooseVersion(instance_to_version) and
                          (LooseVersion(obj_toversion) >= LooseVersion(instance_from_version))):
                        is_duplicated = True
                        break

        if is_duplicated:
            error_message, error_code = Errors.duplicated_id(obj_id)
            if not self.handle_error(error_message, error_code, file_path='id_set.json'):
                return False

        return is_duplicated

    def is_file_has_used_id(self, file_path):
        """Check if the ID of the given file already exist in the system.

        Args:
            file_path (string): Path to the file.

        Returns:
            bool. Whether the ID of the given file already exist in the system or not.
        """
        is_used = False
        is_json_file = False
        if self.is_circle:
            if re.match(constants.TEST_PLAYBOOK_REGEX, file_path, re.IGNORECASE):
                obj_type = self.TEST_PLAYBOOK_SECTION
                obj_id = collect_ids(file_path)
                obj_data = get_playbook_data(file_path)

            elif re.match(constants.PACKS_SCRIPT_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.TEST_SCRIPT_REGEX, file_path, re.IGNORECASE):
                obj_type = self.SCRIPTS_SECTION
                obj_id = get_script_or_integration_id(file_path)
                obj_data = get_script_data(file_path)

            elif re.match(constants.PACKS_INTEGRATION_YML_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE):

                obj_type = self.INTEGRATION_SECTION
                obj_id = get_script_or_integration_id(file_path)
                obj_data = get_integration_data(file_path)

            elif re.match(constants.PLAYBOOK_REGEX, file_path, re.IGNORECASE):
                obj_type = self.PLAYBOOK_SECTION
                obj_id = collect_ids(file_path)
                obj_data = get_playbook_data(file_path)

            elif re.match(constants.PACKS_SCRIPT_YML_REGEX, file_path, re.IGNORECASE) or \
                    re.match(constants.PACKS_SCRIPT_PY_REGEX, file_path, re.IGNORECASE):

                unifier = Unifier(os.path.dirname(os.path.dirname(file_path)))
                yml_path, code = unifier.get_script_or_integration_package_data()

                obj_data = get_script_data(yml_path, script_code=code)

                obj_type = self.SCRIPTS_SECTION
                obj_id = get_script_or_integration_id(yml_path)

            else:  # In case of a json file
                is_json_file = True

            if not is_json_file:
                is_used = self.is_id_duplicated(obj_id, obj_data, obj_type)

        return is_used
