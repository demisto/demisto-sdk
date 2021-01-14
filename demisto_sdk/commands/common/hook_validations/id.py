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
from demisto_sdk.commands.common.update_id_set import (get_classifier_data,
                                                       get_incident_type_data,
                                                       get_integration_data,
                                                       get_mapper_data,
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
    CLASSIFIERS_SECTION = "Classifiers"
    LAYOUTS_SECTION = "Layouts"
    MAPPERS_SECTION = "Mappers"
    INCIDENT_TYPES_SECTION = "IncidentTypes"

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
            self.classifiers_set = self.id_set[self.CLASSIFIERS_SECTION]
            self.layouts_set = self.id_set[self.LAYOUTS_SECTION]
            self.mappers_set = self.id_set[self.MAPPERS_SECTION]
            self.incident_types_set = self.id_set[self.INCIDENT_TYPES_SECTION]

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

    def _is_incident_type_default_playbook_found(self, incident_type_data):
        """Check if the default playbook of an incident type is in the id_set

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
        if depends_on_commands:
            for command in depends_on_commands:
                if command != 'test-module':
                    if command.endswith('dev') or command.endswith('copy'):
                        error_message, error_code = Errors.invalid_command_name_in_script(script_data.get('name'),
                                                                                          command)
                        self.handle_error(error_message, error_code, file_path="id_set.json")
                        return not is_valid
        return is_valid

    def _is_integration_classifier_and_mapper_found(self, integration_data):
        """Check if the integration classifier and mapper are found

        Args:
            integration_data (dict): Dictionary that holds the extracted details from the given integration.

        Returns:
            bool. Whether the integration fetch incident classifier is found.
        """
        is_valid_classifier = True
        integration_classifier = integration_data.get('classifiers', '')  # there is only 1 classifier per integration
        if integration_classifier:
            # setting initially to false, if the classifier is in the id_set, it will be valid
            is_valid_classifier = False
            for classifier in self.classifiers_set:
                checked_classifier_name = list(classifier.keys())[0]
                if integration_classifier == checked_classifier_name:
                    is_valid_classifier = True
                    break
            if not is_valid_classifier:  # add error message if not valid
                error_message, error_code = Errors.integration_non_existent_classifier(integration_classifier)
                self.handle_error(error_message, error_code, file_path="id_set.json")

        is_valid_mapper = True
        integration_mapper = integration_data.get('mappers', [''])[0]  # there is only 1 mapper per integration
        if integration_mapper:
            # setting initially to false, if the mapper is in the id_set, it will be valid
            is_valid_mapper = False
            for mapper in self.mappers_set:
                checked_mapper_name = list(mapper.keys())[0]
                if integration_mapper == checked_mapper_name:
                    is_valid_mapper = True
                    break
            if not is_valid_mapper:  # add error message if not valid
                error_message, error_code = Errors.integration_non_existent_mapper(integration_mapper)
                self.handle_error(error_message, error_code, file_path="id_set.json")

        return is_valid_classifier and is_valid_mapper

    def _is_classifier_incident_types_found(self, classifier_data):
        """Check if the classifier incident types were found

        Args:
            classifier_data (dict): Dictionary that holds the extracted details from the given classfier.

        Returns:
            bool. Whether the classifier related incident types are found.
        """
        is_valid = True
        classifier_incident_types = set(classifier_data.get('incident_types', set()))
        if classifier_incident_types:
            # setting initially to false, if the incident types is in the id_set, it will be valid
            is_valid = False
            for incident_type in self.incident_types_set:
                incident_type_name = list(incident_type.keys())[0]
                # remove a related incident types if exists in the id_set
                if incident_type_name in classifier_incident_types:
                    classifier_incident_types.remove(incident_type_name)
                    if not classifier_incident_types:
                        break

            if not classifier_incident_types:  # if nothing remains, these incident types were all found
                is_valid = True
            else:  # there are missing incident types in the id_set, classifier is invalid
                error_message, error_code = Errors.classifier_non_existent_incident_types(str(classifier_incident_types))
                self.handle_error(error_message, error_code, file_path="id_set.json")

        return is_valid

    def _is_mapper_incident_types_found(self, mapper_data):
        """Check if the classifier incident types were found

        Args:
            mapper_data (dict): Dictionary that holds the extracted details from the given mapper.

        Returns:
            bool. Whether the classifier related incident types are found.
        """
        is_valid = True
        mapper_incident_types = set(mapper_data.get('incident_types', set()))
        if mapper_incident_types:
            # setting initially to false, if the incident types is in the id_set, it will be valid
            is_valid = False
            for incident_type in self.incident_types_set:
                incident_type_name = list(incident_type.keys())[0]
                # remove a related incident types if exists in the id_set
                if incident_type_name in mapper_incident_types:
                    mapper_incident_types.remove(incident_type_name)
                    if not mapper_incident_types:
                        break

            if not mapper_incident_types:  # if nothing remains, these incident types were all found
                is_valid = True
            else:  # there are missing incident types in the id_set, mapper is invalid
                error_message, error_code = Errors.mapper_non_existent_incident_types(str(mapper_incident_types))
                self.handle_error(error_message, error_code, file_path="id_set.json")

        return is_valid

    def is_file_valid_in_set(self, file_path, file_type):
        """Check if the file is valid in the id_set

        Args:
            file_path (string): Path to the file.
            file_type (string): The file type.

        Returns:
            bool. Whether the file is valid in the id_set or not.
        """
        is_valid = True
        if self.is_circle:  # No need to check on local env because the id_set will contain this info after the commit
            click.echo(f"id set validations for: {file_path}")

            if re.match(constants.PACKS_SCRIPT_YML_REGEX, file_path, re.IGNORECASE):
                unifier = Unifier(os.path.dirname(file_path))
                yml_path, code = unifier.get_script_or_integration_package_data()
                script_data = get_script_data(yml_path, script_code=code)
                is_valid = self._is_non_real_command_found(script_data)
            elif file_type == constants.FileType.INCIDENT_TYPE:
                incident_type_data = OrderedDict(get_incident_type_data(file_path))
                is_valid = self._is_incident_type_default_playbook_found(incident_type_data)
            elif file_type == constants.FileType.INTEGRATION:
                integration_data = get_integration_data(file_path)
                is_valid = self._is_integration_classifier_and_mapper_found(integration_data)
            elif file_type == constants.FileType.CLASSIFIER:
                classifier_data = get_classifier_data(file_path)
                is_valid = self._is_classifier_incident_types_found(classifier_data)
            elif file_type == constants.FileType.MAPPER:
                mapper_data = get_mapper_data(file_path)
                is_valid = self._is_mapper_incident_types_found(mapper_data)

        return is_valid
