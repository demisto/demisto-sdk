import os
import re
from collections import OrderedDict
from distutils.version import LooseVersion
from typing import Dict, Optional, Tuple

import click
from packaging.version import Version

import demisto_sdk.commands.common.constants as constants
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import GENERIC_COMMANDS_NAMES
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.tools import (
    get_script_or_sub_playbook_tasks_from_playbook,
    get_yaml,
)
from demisto_sdk.commands.common.update_id_set import (
    get_classifier_data,
    get_incident_field_data,
    get_incident_type_data,
    get_integration_data,
    get_layout_data,
    get_layouts_scripts_ids,
    get_layoutscontainer_data,
    get_mapper_data,
    get_pack_metadata_data,
    get_playbook_data,
    get_script_data,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


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

    def __init__(
        self,
        is_test_run=False,
        is_circle=False,
        configuration=Configuration(),
        ignored_errors=None,
        print_as_warnings=False,
        suppress_print=False,
        id_set_file=None,
        json_file_path=None,
        specific_validations=None,
    ):
        super().__init__(
            ignored_errors=ignored_errors,
            print_as_warnings=print_as_warnings,
            suppress_print=suppress_print,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )
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

    @error_codes("IT104")
    def _is_incident_type_default_playbook_found(self, incident_type_data):
        """Check if the default playbook of an incident type is in the id_set

        Args:
            incident_type_data (dict): Dictionary that holds the extracted details from the given incident type.

        Returns:
            bool. Whether the playbook is in the id_set or not.
        """
        is_valid = True
        incident_type_name = list(incident_type_data.keys())[0]
        incident_type_playbook = incident_type_data[incident_type_name].get("playbooks")
        if incident_type_playbook:
            # setting initially to false, if the default playbook is in the id_set, it will be valid
            is_valid = False
            for checked_playbook in self.playbook_set:
                checked_playbook_name = list(checked_playbook.keys())[0]
                if incident_type_playbook == checked_playbook_name:
                    is_valid = True
                    break
            if not is_valid:  # add error message if not valid
                (
                    error_message,
                    error_code,
                ) = Errors.incident_type_non_existent_playbook_id(
                    incident_type_name, incident_type_playbook
                )
                if not self.handle_error(
                    error_message, error_code, file_path="id_set.json"
                ):
                    is_valid = True

        return is_valid

    @error_codes("IF114")
    def _is_incident_field_scripts_found(
        self, incident_field_data, incident_field_file_path=None
    ):
        """Check if scripts and field calculations scripts of an incident field is in the id_set

        Args:
            incident_field_data (dict): Dictionary that holds the extracted details from the given incident field.
            incident_field_file_path (str): Path to the file.

        Returns:
            bool. Whether the scripts are in the id_set or not.
        """
        is_valid = True
        scripts_not_in_id_set = set()

        incident_field_id = list(incident_field_data.keys())[0]
        incident_field = incident_field_data.get(incident_field_id, {})
        incident_field_name = incident_field.get("name", incident_field_id)
        scripts_set = set(incident_field.get("scripts", []))

        # Check if the incident field scripts are in the id_set:
        if scripts_set:
            scripts_not_in_id_set = self._get_scripts_that_are_not_in_id_set(
                scripts_set
            )

        # Add error message if there are scripts that aren't in the id_set:
        if scripts_not_in_id_set:
            is_valid = False
            scripts_not_in_id_set_str = ", ".join(scripts_not_in_id_set)
            error_message, error_code = Errors.incident_field_non_existent_script_id(
                incident_field_name, scripts_not_in_id_set_str
            )
            if not self.handle_error(
                error_message,
                error_code,
                file_path=incident_field_file_path,
                suggested_fix=Errors.suggest_fix_non_existent_script_id(),
            ):
                is_valid = True

        return is_valid

    @error_codes("LO105")
    def _is_layouts_container_scripts_found(
        self, layouts_container_data, layouts_container_file_path=None
    ):
        """Check if scripts of a layouts container is in the id_set

        Args:
            layouts_container_data (dict): Dictionary that holds the extracted details from the given layouts container.
            layouts_container_file_path (str): Path to the file.

        Returns:
            bool. Whether the scripts are in the id_set or not.
        """
        is_valid = True
        scripts_not_in_id_set = set()

        layouts_container_id = list(layouts_container_data.keys())[0]
        layouts_container = layouts_container_data.get(layouts_container_id, {})
        layouts_container_name = layouts_container.get("name", layouts_container_id)
        layouts_container_tabs = self._get_layouts_container_tabs(layouts_container)
        scripts_set = set(get_layouts_scripts_ids(layouts_container_tabs))

        # Check if the layouts container's scripts are in the id_set:
        if scripts_set:
            scripts_not_in_id_set = self._get_scripts_that_are_not_in_id_set(
                scripts_set
            )

        # Add error message if there are scripts that aren't in the id_set:
        if scripts_not_in_id_set:
            is_valid = False
            scripts_not_in_id_set_str = ", ".join(scripts_not_in_id_set)
            error_message, error_code = Errors.layouts_container_non_existent_script_id(
                layouts_container_name, scripts_not_in_id_set_str
            )
            if not self.handle_error(
                error_message,
                error_code,
                file_path=layouts_container_file_path,
                suggested_fix=Errors.suggest_fix_non_existent_script_id(),
            ):
                is_valid = True

        return is_valid

    @error_codes("LO106")
    def _is_layout_scripts_found(self, layout_data, layout_file_path=None):
        """Check if scripts of a layout  is in the id_set

        Args:
            layout_data (dict): Dictionary that holds the extracted details from the given layout.
            layout_file_path (str): Path to the file.

        Returns:
            bool. Whether the scripts are in the id_set or not.
        """
        is_valid = True
        scripts_not_in_id_set = set()

        layout_id = list(layout_data.keys())[0]
        layout = layout_data.get(layout_id, {})
        layout_name = layout.get("typename", layout_id)
        scripts = layout.get("scripts", [])
        scripts_set = set(scripts)

        # Check if the layouts container's scripts are in the id_set:
        if scripts_set:
            scripts_not_in_id_set = self._get_scripts_that_are_not_in_id_set(
                scripts_set
            )

        # Add error message if there are scripts that aren't in the id_set:
        if scripts_not_in_id_set:
            is_valid = False
            scripts_not_in_id_set_str = ", ".join(scripts_not_in_id_set)
            error_message, error_code = Errors.layout_non_existent_script_id(
                layout_name, scripts_not_in_id_set_str
            )
            if not self.handle_error(
                error_message,
                error_code,
                file_path=layout_file_path,
                suggested_fix=Errors.suggest_fix_non_existent_script_id(),
            ):
                is_valid = True

        return is_valid

    def _get_scripts_that_are_not_in_id_set(self, scripts_in_entity):
        """
        For each script ID in the given scripts set checks if it is exist in the id set.
        If a script is in the id set removes it from the input scripts set.

        Args:
            scripts_set: A set of scripts IDs

        Returns:
            A sub set of the input scripts set which contains only scripts that are not in the id set.
        """
        for checked_script in self.script_set:
            checked_script_id = list(checked_script.keys())[0]
            if checked_script_id in scripts_in_entity:
                scripts_in_entity.remove(checked_script_id)

        # Ignore Builtin scripts because they are implemented on the server side and thus not in the id_set.json
        scripts_in_entity = self._remove_builtin_scripts(scripts_in_entity)

        # Validate command should verify that each integration command called from
        # a layout, a layoutscontainer or an incident field really exist in the content repo.
        scripts_in_entity = self._validate_integration_commands(scripts_in_entity)
        return scripts_in_entity

    def _remove_builtin_scripts(self, scripts_set):
        """
        For each script ID in the given scripts set checks if it is a Builtin script (implemented on the server side)
        by checking if it starts with the string: 'Builtin|||'.
        If a script is not a Builtin script add it to a new scripts set.

        Args:
            scripts_set: A set of scripts IDs

        Returns:
            A new set which includes all scripts of the input scripts set which are not Builtin scripts.
        """
        not_builtin_scripts_set = set()

        for script_id in scripts_set:
            if not script_id.startswith("Builtin|||"):
                not_builtin_scripts_set.add(script_id)

        return not_builtin_scripts_set

    def _validate_integration_commands(self, scripts_set):
        """
        For each script ID in the given scripts set checks if it is an integration command by
        checking if it contains '|||'.
        If a script is  an integration command checks whether it exists in id_set.json
        if it exists we remove it from the scripts_set.
        Args:
            scripts_set: A set of scripts IDs

        Returns:
            A new set which includes all scripts of the input scripts set which are not integration
            commands or valid integration commands.
        """
        validated_scripts_set = set(scripts_set)
        for script_id in scripts_set:
            if "|||" in script_id:
                integration_id, integration_command = script_id.split("|||")
                for checked_integration in self.integration_set:
                    checked_integration_id = list(checked_integration.keys())[0]
                    if checked_integration_id == integration_id:
                        commands = checked_integration.get(
                            checked_integration_id, {}
                        ).get("commands")
                        if integration_command in commands:
                            validated_scripts_set.remove(script_id)
        return validated_scripts_set

    def _get_layouts_container_tabs(self, layouts_container):
        """
        Finds all tabs of the given layouts container

        Args:
            layouts_container: A layout container

        Returns: A list of all the given layouts container's tabs

        """
        all_tabs = []
        layouts_container_fields_with_tabs = [
            "edit",
            "indicatorsDetails",
            "indicatorsQuickView",
            "quickView",
            "details",
            "detailsV2",
            "mobile",
        ]
        for field in layouts_container_fields_with_tabs:
            field_content = layouts_container.get(field)
            if field_content:
                tabs = field_content.get("tabs", [])
                all_tabs.extend(tabs)

        return all_tabs

    @error_codes("SC102")
    def _is_non_real_command_found(self, script_data):
        """Check if the script depend-on section has a non real command

        Args:
            script_data (dict): Dictionary that holds the extracted details from the given script.

        Returns:
            bool. Whether the script is valid or not.
        """
        is_valid = True
        depends_on_commands = script_data.get("depends_on")
        if depends_on_commands:
            for command in depends_on_commands:
                if command != "test-module":
                    if command.endswith("dev") or command.endswith("copy"):
                        (
                            error_message,
                            error_code,
                        ) = Errors.invalid_command_name_in_script(
                            script_data.get("name"), command
                        )
                        if self.handle_error(
                            error_message, error_code, file_path="id_set.json"
                        ):
                            return not is_valid
        return is_valid

    @error_codes("IN132,IN133")
    def _is_integration_classifier_and_mapper_found(self, integration_data):
        """Check if the integration classifier and mapper are found

        Args:
            integration_data (dict): Dictionary that holds the extracted details from the given integration.

        Returns:
            bool. Whether the integration fetch incident classifier is found.
        """
        is_valid_classifier = True
        integration_classifier = integration_data.get(
            "classifiers", ""
        )  # there is only 1 classifier per integration
        if integration_classifier:
            # setting initially to false, if the classifier is in the id_set, it will be valid
            is_valid_classifier = False
            for classifier in self.classifiers_set:
                checked_classifier_name = list(classifier.keys())[0]
                if integration_classifier == checked_classifier_name:
                    is_valid_classifier = True
                    break
            if not is_valid_classifier:  # add error message if not valid
                error_message, error_code = Errors.integration_non_existent_classifier(
                    integration_classifier
                )
                if not self.handle_error(
                    error_message, error_code, file_path="id_set.json"
                ):
                    is_valid_classifier = True

        is_valid_mapper = True
        integration_mapper = integration_data.get("mappers", [""])[
            0
        ]  # there is only 1 mapper per integration
        if integration_mapper:
            # setting initially to false, if the mapper is in the id_set, it will be valid
            is_valid_mapper = False
            for mapper in self.mappers_set:
                checked_mapper_name = list(mapper.keys())[0]
                if integration_mapper == checked_mapper_name:
                    is_valid_mapper = True
                    break
            if not is_valid_mapper:  # add error message if not valid
                error_message, error_code = Errors.integration_non_existent_mapper(
                    integration_mapper
                )
                if not self.handle_error(
                    error_message, error_code, file_path="id_set.json"
                ):
                    is_valid_mapper = True

        return is_valid_classifier and is_valid_mapper

    @error_codes("CL108")
    def _is_classifier_incident_types_found(self, classifier_data):
        """Check if the classifier incident types were found

        Args:
            classifier_data (dict): Dictionary that holds the extracted details from the given classfier.

        Returns:
            bool. Whether the classifier related incident types are found.
        """
        is_valid = True
        classifier_incident_types = set(classifier_data.get("incident_types", set()))
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

            if (
                not classifier_incident_types
            ):  # if nothing remains, these incident types were all found
                is_valid = True
            else:  # there are missing incident types in the id_set, classifier is invalid
                (
                    error_message,
                    error_code,
                ) = Errors.classifier_non_existent_incident_types(
                    str(classifier_incident_types)
                )
                if not self.handle_error(
                    error_message, error_code, file_path="id_set.json"
                ):
                    is_valid = True

        return is_valid

    @error_codes("MP105")
    def _is_mapper_incident_types_found(self, mapper_data):
        """Check if the classifier incident types were found

        Args:
            mapper_data (dict): Dictionary that holds the extracted details from the given mapper.

        Returns:
            bool. Whether the classifier related incident types are found.
        """
        is_valid = True
        mapper_incident_types = set(mapper_data.get("incident_types", set()))
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

            if (
                not mapper_incident_types
            ):  # if nothing remains, these incident types were all found
                is_valid = True
            else:  # there are missing incident types in the id_set, mapper is invalid
                error_message, error_code = Errors.mapper_non_existent_incident_types(
                    str(mapper_incident_types)
                )
                if not self.handle_error(
                    error_message, error_code, file_path="id_set.json"
                ):
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
        playbook_integration_commands = self.get_commands_to_integration(
            playbook_name, file_path
        )
        main_playbook_data = get_yaml(file_path)

        result, error = self.is_entity_version_match_playbook_version(
            sub_playbooks_list,
            playbook_version,
            self.playbook_set,
            playbook_name,
            file_path,
            main_playbook_data,
            "sub-playbooks",
        )
        if not result:
            return False, error
        result, error = self.is_entity_version_match_playbook_version(
            playbook_scripts_list,
            playbook_version,
            self.script_set,
            playbook_name,
            file_path,
            main_playbook_data,
            "scripts",
        )
        if not result:
            return False, error

        result, error = self.is_playbook_integration_version_valid(
            playbook_integration_commands, playbook_version, playbook_name, file_path
        )
        if not result:
            return False, error

        return True, None

    @error_codes("PB113")
    def is_subplaybook_name_valid(self, playbook_data, file_path):
        """Checks whether a sub playbook name is valid (i.e id exists in set_id)
        Args:
            playbook_data (dict): Dictionary that holds the extracted details from the given playbook.
             {playbook name: playbook data (dict)}
            file_path (string): Path to the file (current playbook).

        Return:
            bool. if all sub playbooks names of this playbook are valid.
        """
        # Get a dict with all playbook fields from the playbook data dict.
        playbook_data_2nd_level = playbook_data.get(list(playbook_data.keys())[0])
        main_playbook_name = playbook_data_2nd_level.get("name")
        sub_playbooks_list = playbook_data_2nd_level.get("implementing_playbooks", [])
        for playbook_dict in self.playbook_set:
            playbook_name = list(playbook_dict.values())[0].get("name")
            if playbook_name in sub_playbooks_list:
                sub_playbooks_list.remove(playbook_name)

        if sub_playbooks_list:
            error_message, error_code = Errors.invalid_subplaybook_name(
                sub_playbooks_list, main_playbook_name
            )
            if self.handle_error(error_message, error_code, file_path):
                return False

        return True

    def get_commands_to_integration(self, file_name, file_path):
        """gets playbook's 'command_to_integration' dict from playbook set in id_set file.

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
            is_this_the_playbook = (
                playbook_name == file_name and file_path == playbook_path
            )
            if is_this_the_playbook:
                playbook_data = playbook_dict[playbook_name]
                commands_to_integration = playbook_data.get(
                    "command_to_integration", {}
                )
                return commands_to_integration
        return commands_to_integration

    @error_codes("PB110,PB117")
    def is_entity_version_match_playbook_version(
        self,
        implemented_entity_list_from_playbook,
        main_playbook_version,
        entity_set_from_id_set,
        playbook_name,
        file_path,
        main_playbook_data,
        content_sub_type,
    ) -> Tuple[bool, Optional[str]]:
        """Check if the playbook's version match playbook's entities (script or sub-playbook)
        Goes over the relevant entity set from id_set and check if the version of this entity match is equal or lower
        to the main playbook's version.
        For example, for given scripts list : implemented_entity_list_from_playbook = ["script1", "script2"],
        main playbook version = "5.0.0".
        This code searches for script1 version in the scripts set (in id_set) and returns True only if
        script1 version <= "5.0.0." (main playbook version), otherwise returns False. Does the same for "script2".

        Args:
            implemented_entity_list_from_playbook (list): List of relevant entities to check from playbook. For example,
            list of implementing_scripts or list of implementing_playbooks.
            main_playbook_version (str): Playbook's from version.
            entity_set_from_id_set (dict) : Entity's data set (scripts or playbooks) from id_set file.
            playbook_name (str) : Playbook's name.
            file_path (string): Path to the file (current playbook).
            main_playbook_data (dict): Data of the main playbook.
            content_sub_type (str): content sub type, whether its entity list are sub-playbooks or scripts.

        Returns:
            Tuple[bool, Optional[str]]. Whether the playbook's version match playbook's entities and error message.
        """

        def get_skip_unavailable(_entity_name) -> bool:
            tasks_data = get_script_or_sub_playbook_tasks_from_playbook(
                searched_entity_name=_entity_name, main_playbook_data=main_playbook_data
            )
            # In case all the tasks (in the main_playbook) calling the sub_playbook are skipped,
            # we will allow it to be a higher version than the main_playbook
            return (
                all(task_data.get("skipunavailable", False) for task_data in tasks_data)
                if tasks_data
                else False
            )

        def is_minimum_version_valid(_min_version) -> bool:
            """
            In case we have more than one entity with the same ID,
            verify that the one with the minimum version is valid.
            """
            return Version(_min_version) <= Version(main_playbook_version)

        implemented_entity_list_from_playbook = set(
            implemented_entity_list_from_playbook
        )
        implemented_ids_in_id_set = set()

        entity_ids_with_min_version: Dict[str, tuple] = {}
        for entity in entity_set_from_id_set:
            entity_id = list(entity.keys())[0]
            entity_data = entity.get(entity_id)
            entity_name = (
                entity_id
                if entity_id in implemented_entity_list_from_playbook
                else entity_data.get("name")
            )
            if entity_name in implemented_entity_list_from_playbook:
                # ignore entities which do not have fromversion and extract minimum version in case
                # there are multiple playbooks / scripts with the same ID.
                if from_version := entity_data.get("fromversion"):
                    if entity_name not in entity_ids_with_min_version:
                        entity_ids_with_min_version[entity_name] = (
                            from_version,
                            entity_data.get("file_path"),
                        )
                    else:
                        if min_version_to_path := entity_ids_with_min_version.get(
                            entity_name
                        ):
                            min_version, _ = min_version_to_path
                            if Version(from_version) < Version(min_version):
                                entity_ids_with_min_version[entity_name] = (
                                    from_version,
                                    entity_data.get("file_path"),
                                )
                implemented_ids_in_id_set.add(entity_name)

        invalid_entries_path_to_version = [
            min_version_to_path
            for entity_name, min_version_to_path in entity_ids_with_min_version.items()
            if not (
                is_minimum_version_valid(min_version_to_path[0])
                or get_skip_unavailable(entity_name)
            )
        ]

        if invalid_entries_path_to_version:
            invalid_entities_error_msg = ", ".join(
                [
                    f"{file_path}: {entity_version}"
                    for entity_version, file_path in invalid_entries_path_to_version
                ]
            )
            (
                error_message,
                error_code,
            ) = Errors.content_entity_version_not_match_playbook_version(
                playbook_name,
                invalid_entities_error_msg,
                main_playbook_version,
                content_sub_type,
            )
            if self.handle_error(error_message, error_code, file_path):
                return False, error_message

        entity_ids_not_exist_in_id_set = [
            entity
            for entity in implemented_entity_list_from_playbook
            if entity not in implemented_ids_in_id_set
        ]

        if entity_ids_not_exist_in_id_set:
            error_message, error_code = Errors.content_entity_is_not_in_id_set(
                playbook_name, entity_ids_not_exist_in_id_set
            )
            if self.handle_error(error_message, error_code, file_path):
                return False, error_message

        return True, None

    @error_codes("PB111")
    def is_playbook_integration_version_valid(
        self, playbook_integration_commands, playbook_version, playbook_name, file_path
    ):
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
            # Ignore the error for PB with generic commands that do not depend on specific integration
            if command in GENERIC_COMMANDS_NAMES and not implemented_integrations_list:
                continue
            integration_from_valid_version_found = False
            for integration in implemented_integrations_list:
                integration_version = self.get_integration_version(integration)
                is_version_valid = not integration_version or LooseVersion(
                    integration_version
                ) <= LooseVersion(playbook_version)
                if is_version_valid:
                    integration_from_valid_version_found = True
                    break

            if not integration_from_valid_version_found:
                (
                    error_message,
                    error_code,
                ) = Errors.integration_version_not_match_playbook_version(
                    playbook_name, command, playbook_version
                )
                if self.handle_error(error_message, error_code, file_path):
                    return False, error_message

        return True, None

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
        if (
            self.is_circle
        ):  # No need to check on local env because the id_set will contain this info after the commit
            click.echo(f"id set validations for: {file_path}")

            if re.match(constants.PACKS_SCRIPT_YML_REGEX, file_path, re.IGNORECASE):
                (
                    yml_path,
                    code,
                ) = IntegrationScriptUnifier.get_script_or_integration_package_data(
                    os.path.dirname(file_path)
                )
                script_data = get_script_data(yml_path, script_code=code)
                is_valid = self._is_non_real_command_found(script_data)
            elif file_type == constants.FileType.INCIDENT_TYPE:
                incident_type_data = OrderedDict(get_incident_type_data(file_path))
                is_valid = self._is_incident_type_default_playbook_found(
                    incident_type_data
                )
            elif file_type == constants.FileType.INCIDENT_FIELD:
                incident_field_data = OrderedDict(
                    get_incident_field_data(file_path, [])
                )
                is_valid = self._is_incident_field_scripts_found(
                    incident_field_data, file_path
                )
            elif file_type == constants.FileType.LAYOUTS_CONTAINER:
                layouts_container_data = OrderedDict(
                    get_layoutscontainer_data(file_path)
                )
                is_valid = self._is_layouts_container_scripts_found(
                    layouts_container_data, file_path
                )
            elif file_type == constants.FileType.LAYOUT:
                layout_data = OrderedDict(get_layout_data(file_path))
                is_valid = self._is_layout_scripts_found(layout_data, file_path)
            elif file_type == constants.FileType.INTEGRATION:
                integration_data = get_integration_data(file_path)
                is_valid = self._is_integration_classifier_and_mapper_found(
                    integration_data
                )
            elif file_type == constants.FileType.CLASSIFIER:
                classifier_data = get_classifier_data(file_path)
                is_valid = self._is_classifier_incident_types_found(classifier_data)
            elif file_type == constants.FileType.MAPPER:
                mapper_data = get_mapper_data(file_path)
                is_valid = self._is_mapper_incident_types_found(mapper_data)
            elif file_type == constants.FileType.PLAYBOOK:
                playbook_data = get_playbook_data(file_path)
                playbook_answers = [
                    self._are_playbook_entities_versions_valid(
                        playbook_data, file_path
                    )[0],
                    self.is_subplaybook_name_valid(playbook_data, file_path),
                ]
                is_valid = all(playbook_answers)
        return is_valid

    def _is_pack_display_name_already_exist(self, pack_metadata_data):
        """Check if the pack display name already exists in our repo
        Args:
            pack_metadata_data (dict): Dictionary that holds the extracted details from the given metadata file.
        Returns:
            bool. Whether the metadata file is valid or not.
        """

        if not pack_metadata_data:
            return False, None

        new_pack_folder_name = list(pack_metadata_data.keys())[0]
        new_pack_name = pack_metadata_data[new_pack_folder_name]["name"]
        for pack_folder_name, pack_data in self.packs_set.items():
            if (
                new_pack_name == pack_data["name"]
                and new_pack_folder_name != pack_folder_name
            ):
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
                get_pack_metadata_data(f"{pack_path}/pack_metadata.json", False)
            )

        return is_valid, error
