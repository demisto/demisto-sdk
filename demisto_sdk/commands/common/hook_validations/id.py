import os
import re
from collections import OrderedDict
from distutils.version import LooseVersion

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
                                                       get_pack_metadata_data,
                                                       get_playbook_data,
                                                       get_script_data)
from demisto_sdk.commands.unify.unifier import Unifier


class IDSetValidations(BaseValidator):
    """IDSetValidations was designed to make sure all the inter connected content entities are valid.

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
    PACKS_SECTION = "Packs"

    def __init__(self, is_test_run=False, is_circle=False, configuration=Configuration(), ignored_errors=None,
                 print_as_warnings=False, suppress_print=False, id_set_file=None, json_file_path=None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.is_circle = is_circle
        self.configuration = configuration
        if not is_test_run and self.is_circle:
            self.id_set_file = id_set_file
            self.script_set = self.id_set_file[self.SCRIPTS_SECTION]
            self.playbook_set = self.id_set_file[self.PLAYBOOK_SECTION]
            self.integration_set = self.id_set_file[self.INTEGRATION_SECTION]
            self.test_playbook_set = self.id_set_file[self.TEST_PLAYBOOK_SECTION]
            self.classifiers_set = self.id_set_file[self.CLASSIFIERS_SECTION]
            self.layouts_set = self.id_set_file[self.LAYOUTS_SECTION]
            self.mappers_set = self.id_set_file[self.MAPPERS_SECTION]
            self.incident_types_set = self.id_set_file[self.INCIDENT_TYPES_SECTION]
            self.packs_set = self.id_set_file[self.PACKS_SECTION]

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
                if not self.handle_error(error_message, error_code, file_path="id_set.json"):
                    is_valid = True

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
                        if self.handle_error(error_message, error_code, file_path="id_set.json"):
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
                if not self.handle_error(error_message, error_code, file_path="id_set.json"):
                    is_valid_classifier = True

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
                if not self.handle_error(error_message, error_code, file_path="id_set.json"):
                    is_valid_mapper = True

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
                error_message, error_code = Errors.classifier_non_existent_incident_types(
                    str(classifier_incident_types))
                if not self.handle_error(error_message, error_code, file_path="id_set.json"):
                    is_valid = True

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
                if not self.handle_error(error_message, error_code, file_path="id_set.json"):
                    is_valid = True

        return is_valid

    def _are_playbook_entities_versions_valid(self, playbook_data, file_path):
        """Check if the playbook's version match playbook's entities (script , sub-playbook, integration)

        Args:
            playbook_data (dict): Dictionary that holds the extracted details from the given playbook.
            file_path (string): Path to the file (current playbook).

        Returns:
            bool. Whether the playbook's version match playbook's entities.
        """
        playbook_data_2nd_level = playbook_data.get(list(playbook_data.keys())[0])
        playbook_name = playbook_data_2nd_level.get("name")
        playbook_version = playbook_data_2nd_level.get("fromversion")
        playbook_scripts_list = playbook_data_2nd_level.get("implementing_scripts", [])
        sub_playbooks_list = playbook_data_2nd_level.get("implementing_playbooks", [])
        playbook_integration_commands = self.get_commands_to_integration(playbook_name, file_path)

        if not self.is_entity_version_match_playbook_version(sub_playbooks_list, playbook_version, self.playbook_set,
                                                             playbook_name, file_path):
            return False

        if not self.is_entity_version_match_playbook_version(playbook_scripts_list, playbook_version, self.script_set,
                                                             playbook_name, file_path):
            return False

        if not self.is_playbook_integration_version_valid(playbook_integration_commands,
                                                          playbook_version, playbook_name, file_path):
            return False

        return True

    def get_commands_to_integration(self, file_name, file_path):
        """ gets playbook's 'command_to_integration' dict from playbook set in id_set file.

        Args:
            file_name (string): Name of current playbook.
            file_path (string): : Path to the playbook file.

        Returns:
            dictionary. Playbook's 'command_to_integration' dict.
        """
        commands_to_integration = {}
        for playbook_dict in self.playbook_set:
            playbook_name = list(playbook_dict.keys())[0]
            playbook_path = playbook_dict[playbook_name].get("file_path")
            is_this_the_playbook = playbook_name == file_name and file_path == playbook_path
            if is_this_the_playbook:
                playbook_data = playbook_dict[playbook_name]
                commands_to_integration = playbook_data.get("command_to_integration", {})
                return commands_to_integration
        return commands_to_integration

    def is_entity_version_match_playbook_version(self, implemented_entity_list_from_playbook,
                                                 main_playbook_version, entity_set_from_id_set,
                                                 playbook_name, file_path):
        """Check if the playbook's version match playbook's entities (script or sub-playbook)
        Goes over the relevant entity set from id_set and check if the version of this entity match is equal or lower
        to the main playbook's version.
        For example, for given scripts list : implemented_entity_list_from_playbook = ["script1", "script2"],
        main playbook version = "5.0.0".
        This code searches for script1 version in the scripts set (in id_set) and returns True only if
        script1 version <= "5.0.0." (main playbook version), otherwise returns False. Does the same for "script2".

        Args:
            implemented_entity_list_from_playbook (list): List of relevant entities yo check from playbook. For example,
            list of implementing_scripts or list of implementing_playbooks.
            main_playbook_version (str): Playbook's from version.
            entity_set_from_id_set (dict) : Entity's data set (scripts or playbooks) from id_set file.
            playbook_name (str) : Playbook's name.
            file_path (string): Path to the file (current playbook).

        Returns:
            bool. Whether the playbook's version match playbook's entities.
        """
        invalid_version_entities = []
        is_valid = True
        for entity_data_dict in entity_set_from_id_set:

            entity_id = list(entity_data_dict.keys())[0]
            all_entity_fields = entity_data_dict[entity_id]
            entity_name = entity_id if entity_id in implemented_entity_list_from_playbook else all_entity_fields.get(
                "name")
            is_entity_used_in_playbook = entity_name in implemented_entity_list_from_playbook

            if is_entity_used_in_playbook:
                entity_version = all_entity_fields.get("fromversion", "")
                is_version_valid = not entity_version or LooseVersion(entity_version) <= LooseVersion(
                    main_playbook_version)
                if not is_version_valid:
                    invalid_version_entities.append(entity_name)
                    is_valid = False
                implemented_entity_list_from_playbook.remove(entity_name)

        if invalid_version_entities:
            error_message, error_code = Errors.content_entity_version_not_match_playbook_version(
                playbook_name, invalid_version_entities, main_playbook_version)
            if self.handle_error(error_message, error_code, file_path):
                is_valid = False

        if implemented_entity_list_from_playbook:
            error_message, error_code = Errors.content_entity_is_not_in_id_set(
                playbook_name, implemented_entity_list_from_playbook)
            if self.handle_error(error_message, error_code, file_path):
                is_valid = False

        return is_valid

    def is_playbook_integration_version_valid(self, playbook_integration_commands, playbook_version, playbook_name,
                                              file_path):
        """Check if the playbook's version match playbook's used integrations.
        Goes over all the integrations' commands that used in the current playbook. For each command, checks its
        integration's from version.
        If at least one existing integration was found that integration version <= playbook version, True is returned.
        If no such integration was found, False returned.

        Args:
            playbook_integration_commands (dict): Playbook's 'command_to_integration' dict.
            playbook_version (str): Playbook's from version .
            playbook_name (str) : Playbook's name .
            file_path (string): Path to the file (current playbook) .

        Returns:
            bool. Whether the playbook's version match playbook's used integrations.
        """

        for command in playbook_integration_commands:
            implemented_integrations_list = playbook_integration_commands[command]
            integration_from_valid_version_found = False
            for integration in implemented_integrations_list:
                integration_version = self.get_integration_version(integration)
                is_version_valid = not integration_version or LooseVersion(integration_version) <= LooseVersion(
                    playbook_version)
                if is_version_valid:
                    integration_from_valid_version_found = True
                    break

            if not integration_from_valid_version_found:
                error_message, error_code = Errors.integration_version_not_match_playbook_version(playbook_name,
                                                                                                  command,
                                                                                                  playbook_version)
                if self.handle_error(error_message, error_code, file_path):
                    return False

        return True

    def get_integration_version(self, integration_to_search):
        general_version = ""  # i.e integration has no specific version
        for integration_dict in self.integration_set:
            integration_name = list(integration_dict.keys())[0]
            if integration_name == integration_to_search:
                integration_data = integration_dict[integration_name]
                return integration_data.get("fromversion", "")
        return general_version

    def is_file_valid_in_set(self, file_path, file_type, ignored_errors=None):
        """Check if the file is valid in the id_set

        Args:
            file_path (string): Path to the file.
            file_type (string): The file type.
            ignored_errors (list): a list of ignored errors for the specific file

        Returns:
            bool. Whether the file is valid in the id_set or not.
        """
        self.ignored_errors = ignored_errors
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
            elif file_type == constants.FileType.PLAYBOOK:
                playbook_data = get_playbook_data(file_path)
                is_valid = self._are_playbook_entities_versions_valid(playbook_data, file_path)

        return is_valid

    def _is_pack_display_name_already_exist(self, pack_metadata_data):
        """Check if the pack display name already exists in our repo
        Args:
            pack_metadata_data (dict): Dictionary that holds the extracted details from the given metadata file.
        Returns:
            bool. Whether the metadata file is valid or not.
        """
        new_pack_folder_name = list(pack_metadata_data.keys())[0]
        new_pack_name = pack_metadata_data[new_pack_folder_name]['name']
        for pack_folder_name, pack_data in self.packs_set.items():
            if new_pack_name == pack_data['name'] and new_pack_folder_name != pack_folder_name:
                return False, Errors.pack_name_already_exists(new_pack_name)
        return True, None

    def is_unique_file_valid_in_set(self, pack_path, ignored_errors=None):
        """Check if unique files are valid against the rest of the files, using the ID set.
        Args:
            pack_path (string): Path to the file.
            ignored_errors (list): a list of ignored errors for the specific file
        Returns:
            bool. Whether the file is valid in the id_set or not.
            string. Error massage if the file is invalid else None.
        """
        self.ignored_errors = ignored_errors
        is_valid = True
        error = None
        if self.is_circle:
            click.echo(f"id set validations for: {pack_path}")

            is_valid, error = self._is_pack_display_name_already_exist(
                get_pack_metadata_data(f'{pack_path}/pack_metadata.json', False))

        return is_valid, error
