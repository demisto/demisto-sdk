import glob
import json
import os
import sys
from copy import deepcopy
from distutils.version import LooseVersion
from typing import Union

import click
import networkx as nx
from demisto_sdk.commands.common import constants
from demisto_sdk.commands.common.constants import GENERIC_COMMANDS_NAMES
from demisto_sdk.commands.common.tools import (get_content_id_set,
                                               is_external_repository,
                                               print_error, print_warning)
from demisto_sdk.commands.common.update_id_set import merge_id_sets
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from requests import RequestException

MINIMUM_DEPENDENCY_VERSION = LooseVersion('6.0.0')
COMMON_TYPES_PACK = 'CommonTypes'


def parse_for_pack_metadata(dependency_graph: nx.DiGraph, graph_root: str, verbose: bool = False,
                            complete_data: bool = False, id_set_data=None) -> tuple:
    """
    Parses calculated dependency graph and returns first and all level parsed dependency.
    Additionally returns list of displayed pack images of all graph levels.

    Args:
        dependency_graph (DiGraph): dependency direct graph.
        graph_root (str): graph root pack id.
        verbose(bool): Whether to print the log to the console.
        complete_data (bool): whether to update complete data on the dependent packs.
        id_set_data (dict): id set data.

    Returns:
        dict: first level dependencies parsed data.
        list: all level pack dependencies ids (is used for displaying dependencies images).

    """
    if id_set_data is None:
        id_set_data = {}

    first_level_dependencies = {}
    parsed_dependency_graph = [(k, v) for k, v in dependency_graph.nodes(data=True) if
                               dependency_graph.has_edge(graph_root, k)]

    for dependency_id, additional_data in parsed_dependency_graph:
        pack_name = find_pack_display_name(dependency_id)

        if not complete_data:
            additional_data['display_name'] = pack_name

        else:
            dependency_data = id_set_data.get('Packs', {}).get(dependency_id)
            if dependency_data:
                additional_data['name'] = dependency_data['name']
                additional_data['author'] = dependency_data['author']
                additional_data['minVersion'] = dependency_data['current_version']
                additional_data['certification'] = dependency_data['certification']
            else:
                additional_data['display_name'] = pack_name

        first_level_dependencies[dependency_id] = additional_data

    all_level_dependencies = [n for n in dependency_graph.nodes if dependency_graph.in_degree(n) > 0]

    if verbose:
        click.secho(f'All level dependencies are: {all_level_dependencies}', fg='white')

    return first_level_dependencies, all_level_dependencies


def find_pack_path(pack_folder_name: str) -> list:
    """
    Find pack path matching from content repo root directory.

    Args:
        pack_folder_name (str): pack folder name.

    Returns:
        list: pack metadata json path.

    """
    pack_metadata_path = os.path.join(constants.PACKS_DIR, pack_folder_name, constants.PACKS_PACK_META_FILE_NAME)
    found_path_results = glob.glob(pack_metadata_path)

    return found_path_results


def find_pack_display_name(pack_folder_name: str) -> str:
    """
    Returns pack display name from pack_metadata.json file.

    Args:
        pack_folder_name (str): pack folder name.

    Returns:
        str: pack display name from pack metaata

    """
    found_path_results = find_pack_path(pack_folder_name)

    if not found_path_results:
        return pack_folder_name

    pack_metadata_path = found_path_results[0]

    with open(pack_metadata_path, 'r') as pack_metadata_file:
        pack_metadata = json.load(pack_metadata_file)

    pack_display_name = pack_metadata.get('name') if pack_metadata.get('name') else pack_folder_name

    return pack_display_name


def update_pack_metadata_with_dependencies(pack_folder_name: str, first_level_dependencies: dict) -> None:
    """
    Updates pack metadata with found parsed dependencies results.

    Args:
        pack_folder_name (str): pack folder name.
        first_level_dependencies (dict): first level dependencies data.

    """
    found_path_results = find_pack_path(pack_folder_name)

    if not found_path_results:
        print_error(f"{pack_folder_name} {constants.PACKS_PACK_META_FILE_NAME} was not found")
        sys.exit(1)

    pack_metadata_path = found_path_results[0]

    with open(pack_metadata_path, 'r+') as pack_metadata_file:
        pack_metadata = json.load(pack_metadata_file)
        pack_metadata = {} if not isinstance(pack_metadata, dict) else pack_metadata
        pack_metadata['dependencies'] = first_level_dependencies
        pack_metadata['displayedImages'] = list(first_level_dependencies.keys())

        pack_metadata_file.seek(0)
        json.dump(pack_metadata, pack_metadata_file, indent=4)
        pack_metadata_file.truncate()


def get_merged_official_and_local_id_set(local_id_set: dict, silent_mode: bool = False) -> dict:
    """Merging local idset with content id_set
    Args:
        local_id_set: The local ID set (when running in a local repo)
        silent_mode: When True, will not print logs. False will print logs.
    Returns:
        A unified id_set from local and official content
    """
    try:
        official_id_set = get_content_id_set()
    except RequestException as exception:
        raise RequestException(
            f'Could not download official content from {constants.OFFICIAL_CONTENT_ID_SET_PATH}\n'
            f'Stopping execution.'
        ) from exception
    unified_id_set, duplicates = merge_id_sets(
        official_id_set,
        local_id_set,
        print_logs=not silent_mode
    )
    return unified_id_set.get_dict()


class PackDependencies:
    """
    Pack dependencies calculation class with relevant static methods.
    """

    @staticmethod
    def _search_for_pack_items(pack_id: str, items_list: list) -> list:
        """
        Filtering of content items that belong to specific pack.

        Args:
            pack_id (str): pack id.
            items_list (list): specific section of id set.

        Returns:
            list: collection of content pack items.
        """
        return list(filter(lambda s: next(iter(s.values())).get('pack') == pack_id, items_list))

    @staticmethod
    def _search_packs_by_items_names(items_names: Union[str, list],
                                     items_list: list,
                                     exclude_ignored_dependencies: bool = True) -> set:
        """
        Searches for implemented script/integration/playbook.

        Args:
            items_names (str or list): items names to search.
            items_list (list): specific section of id set.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: found pack ids.

        """
        if not isinstance(items_names, list):
            items_names = [items_names]

        pack_names = set()
        for item in items_list:
            item_details = list(item.values())[0]
            if item_details.get('name', '') in items_names and 'pack' in item_details and \
                    LooseVersion(item_details.get('toversion', '99.99.99')) >= MINIMUM_DEPENDENCY_VERSION:
                pack_names.add(item_details.get('pack'))

        if not exclude_ignored_dependencies:
            return set(pack_names)
        return {p for p in pack_names if p not in constants.IGNORED_DEPENDENCY_CALCULATION}

    @staticmethod
    def _search_packs_by_items_names_or_ids(items_names: Union[str, list],
                                            items_list: list,
                                            exclude_ignored_dependencies: bool = True) -> set:
        """
        Searches for implemented packs of the given items.

        Args:
            items_names (str or list): items names to search.
            items_list (list): specific section of id set.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: found pack ids.

        """
        packs = set()
        if not isinstance(items_names, list):
            items_names = [items_names]

        for item_name in items_names:
            item_possible_names = [item_name, f'incident_{item_name}', f'indicator_{item_name}', f'{item_name}-mapper']
            for item_from_id_set in items_list:
                machine_name = list(item_from_id_set.keys())[0]
                item_details = list(item_from_id_set.values())[0]
                if (machine_name in item_possible_names or item_name == item_details.get('name')) \
                        and item_details.get('pack') \
                        and LooseVersion(item_details.get('toversion', '99.99.99')) >= MINIMUM_DEPENDENCY_VERSION \
                        and (item_details['pack'] not in constants.IGNORED_DEPENDENCY_CALCULATION or
                             not exclude_ignored_dependencies):
                    packs.add(item_details.get('pack'))
        return packs

    @staticmethod
    def _search_packs_by_integration_command(command: str,
                                             id_set: dict,
                                             exclude_ignored_dependencies: bool = True) -> set:
        """
        Filters packs by implementing integration commands.

        Args:
            command (str): integration command.
            id_set (dict): id set json.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: pack id without ignored packs.
        """
        pack_names = set()
        for item in id_set['integrations']:
            item_details = list(item.values())[0]
            if command in item_details.get('commands', []) and 'pack' in item_details and \
                    LooseVersion(item_details.get('toversion', '99.99.99')) >= MINIMUM_DEPENDENCY_VERSION:
                pack_names.add(item_details.get('pack'))

        if not exclude_ignored_dependencies:
            return set(pack_names)
        return {p for p in pack_names if p not in constants.IGNORED_DEPENDENCY_CALCULATION}

    @staticmethod
    def _detect_generic_commands_dependencies(pack_ids: set) -> list:
        """
        Detects whether dependency is mandatory or not. In case two packs implements the same command,
        mandatory is set to False.

        Args:
            pack_ids (set): pack ids list.

        Returns:
            list: collection of packs and mandatory flag set to False if more than 2 packs found.

        """
        return [(p, False) if len(pack_ids) > 1 else (p, True) for p in pack_ids]

    @staticmethod
    def _label_as_mandatory(pack_ids: set) -> list:
        """
        Sets pack as mandatory.

        Args:
            pack_ids (set): collection of pack ids to set as mandatory.

        Returns:
            list: collection of pack id and whether mandatory flag.

        """
        return [(p, True) for p in pack_ids]

    @staticmethod
    def _label_as_optional(pack_ids: set) -> list:
        """
        Sets pack as optional.

        Args:
            pack_ids (set): collection of pack ids to set as optional.

        Returns:
            list: collection of pack id and whether mandatory flag.

        """
        return [(p, False) for p in pack_ids]

    @staticmethod
    def _update_optional_commontypes_pack_dependencies(packs_found_from_incident_fields_or_types: set) -> list:
        """
        Updates pack_dependencies_data for optional dependencies, excluding the CommonTypes pack.
        The reason being when releasing a new pack with e.g, incident fields in the CommonTypes pack,
        only a mandatory dependency will coerce the users to update it to have the necessary content entities.

        Args:
            packs_found_from_incident_fields_or_types (set): pack names found by a dependency to an incident field,
            indicator field or an incident type.

        Returns:
            pack_dependencies_data (list): representing the dependencies.

        """
        common_types_pack_dependency = False
        if COMMON_TYPES_PACK in packs_found_from_incident_fields_or_types:
            packs_found_from_incident_fields_or_types.remove(COMMON_TYPES_PACK)
            common_types_pack_dependency = True
        pack_dependencies_data = PackDependencies._label_as_optional(packs_found_from_incident_fields_or_types)
        if common_types_pack_dependency:
            pack_dependencies_data.extend(PackDependencies._label_as_mandatory({COMMON_TYPES_PACK}))
        return pack_dependencies_data

    @staticmethod
    def _collect_scripts_dependencies(pack_scripts: list,
                                      id_set: dict,
                                      verbose: bool,
                                      exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects script pack dependencies.

        Args:
            pack_scripts (list): pack scripts collection.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Scripts', fg='white')

        for script_mapping in pack_scripts:
            script = next(iter(script_mapping.values()))
            script_dependencies = set()

            # depends on list can have both scripts and integration commands
            depends_on = script.get('depends_on', [])
            command_to_integration = list(script.get('command_to_integration', {}).keys())
            script_executions = script.get('script_executions', [])

            all_dependencies_commands = list(set(depends_on + command_to_integration + script_executions))
            dependencies_commands = list(filter(lambda cmd: cmd not in GENERIC_COMMANDS_NAMES,
                                                all_dependencies_commands))  # filter out generic commands

            for command in dependencies_commands:
                # try to search dependency by scripts first
                pack_name = PackDependencies._search_packs_by_items_names(command, id_set['scripts'],
                                                                          exclude_ignored_dependencies)

                if pack_name:  # found script dependency implementing pack name
                    pack_dependencies_data = PackDependencies._label_as_mandatory(pack_name)
                    script_dependencies.update(pack_dependencies_data)  # set found script as mandatory
                    continue  # found dependency in script section, skipping to next depends on element

                # try to search dependency by integration integration
                pack_names = PackDependencies._search_packs_by_integration_command(
                    command, id_set, exclude_ignored_dependencies)

                if pack_names:  # found integration dependency implementing pack name
                    pack_dependencies_data = PackDependencies._detect_generic_commands_dependencies(pack_names)
                    script_dependencies.update(pack_dependencies_data)

            if verbose:
                click.secho(f'{os.path.basename(script.get("file_path", ""))} depends on: {script_dependencies}',
                            fg='white')
            dependencies_packs.update(script_dependencies)

        return dependencies_packs

    @staticmethod
    def _differentiate_playbook_implementing_objects(implementing_objects: list,
                                                     skippable_tasks: set,
                                                     id_set_section: list,
                                                     exclude_ignored_dependencies: bool = True) -> set:
        """
        Differentiate implementing objects by skippable.

        Args:
            implementing_objects (list): playbook object collection.
            skippable_tasks (set): playbook skippable tasks.
            id_set_section (list): id set section corresponds to implementing_objects (scripts or playbooks).
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
        """
        dependencies = set()

        mandatory_scripts = set(implementing_objects) - skippable_tasks
        optional_scripts = set(implementing_objects) - mandatory_scripts

        optional_script_packs = PackDependencies._search_packs_by_items_names(
            list(optional_scripts), id_set_section, exclude_ignored_dependencies)
        if optional_script_packs:  # found packs of optional objects
            pack_dependencies_data = PackDependencies._label_as_optional(optional_script_packs)
            dependencies.update(pack_dependencies_data)

        mandatory_script_packs = PackDependencies._search_packs_by_items_names(
            list(mandatory_scripts), id_set_section, exclude_ignored_dependencies)
        if mandatory_script_packs:  # found packs of mandatory objects
            pack_dependencies_data = PackDependencies._label_as_mandatory(mandatory_script_packs)
            dependencies.update(pack_dependencies_data)

        return dependencies

    @staticmethod
    def _collect_playbooks_dependencies(pack_playbooks: list, id_set: dict, verbose: bool,
                                        exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects playbook pack dependencies.

        Args:
            pack_playbooks (list): collection of pack playbooks data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Playbooks', fg='white')

        for playbook in pack_playbooks:
            playbook_data = next(iter(playbook.values()))
            playbook_dependencies = set()

            skippable_tasks = set(playbook_data.get('skippable_tasks', []))

            # searching for packs of implementing integrations
            implementing_commands_and_integrations = playbook_data.get('command_to_integration', {})
            if implementing_commands_and_integrations.get('send-notification'):
                del implementing_commands_and_integrations['send-notification']
            for command, integration_name in implementing_commands_and_integrations.items():
                packs_found_from_integration = set()
                if integration_name:
                    packs_found_from_integration = PackDependencies._search_packs_by_items_names(
                        integration_name, id_set['integrations'], exclude_ignored_dependencies)
                elif command not in GENERIC_COMMANDS_NAMES:  # do not collect deps on generic command in Pbs
                    packs_found_from_integration = PackDependencies._search_packs_by_integration_command(
                        command, id_set, exclude_ignored_dependencies)

                if packs_found_from_integration:
                    if command in skippable_tasks:
                        pack_dependencies_data = PackDependencies._label_as_optional(packs_found_from_integration)
                    else:
                        pack_dependencies_data = PackDependencies._detect_generic_commands_dependencies(
                            packs_found_from_integration)
                    playbook_dependencies.update(pack_dependencies_data)

            # searching for packs of implementing scripts
            playbook_dependencies.update(PackDependencies._differentiate_playbook_implementing_objects(
                playbook_data.get('implementing_scripts', []),
                skippable_tasks,
                id_set['scripts'],
                exclude_ignored_dependencies
            ))

            # searching for packs of implementing playbooks
            playbook_dependencies.update(PackDependencies._differentiate_playbook_implementing_objects(
                playbook_data.get('implementing_playbooks', []),
                skippable_tasks,
                id_set['playbooks'],
                exclude_ignored_dependencies
            ))

            # ---- incident fields packs ----
            # playbook dependencies from incident fields should be marked as optional unless CommonTypes pack,
            # as customers do not have to use the OOTB inputs.
            incident_fields = playbook_data.get('incident_fields', [])
            packs_found_from_incident_fields = PackDependencies._search_packs_by_items_names_or_ids(
                incident_fields, id_set['IncidentFields'], exclude_ignored_dependencies)
            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                    packs_found_from_incident_fields)
                playbook_dependencies.update(pack_dependencies_data)

            # ---- indicator fields packs ----
            # playbook dependencies from incident fields should be marked as optional unless CommonTypes pack,
            # as customers do not have to use the OOTB inputs.
            indicator_fields = playbook_data.get('indicator_fields', [])
            packs_found_from_indicator_fields = PackDependencies._search_packs_by_items_names_or_ids(
                indicator_fields, id_set['IndicatorFields'], exclude_ignored_dependencies)
            if packs_found_from_indicator_fields:
                pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                    packs_found_from_indicator_fields)
                playbook_dependencies.update(pack_dependencies_data)

            if playbook_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(playbook_data.get("file_path", ""))} depends on: {playbook_dependencies}',
                        fg='white'
                    )
            dependencies_packs.update(playbook_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_layouts_dependencies(pack_layouts: list,
                                      id_set: dict,
                                      verbose: bool,
                                      exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects layouts pack dependencies.

        Args:
            pack_layouts (list): collection of pack playbooks data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Layouts', fg='white')

        for layout in pack_layouts:
            layout_data = next(iter(layout.values()))
            layout_dependencies = set()

            related_incident_and_indicator_types = layout_data.get('incident_and_indicator_types', [])
            packs_found_from_incident_indicator_types = PackDependencies._search_packs_by_items_names(
                related_incident_and_indicator_types, id_set['IncidentTypes'] + id_set['IndicatorTypes'],
                exclude_ignored_dependencies)

            if packs_found_from_incident_indicator_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_indicator_types)
                layout_dependencies.update(pack_dependencies_data)

            related_incident_and_indicator_fields = layout_data.get('incident_and_indicator_fields', [])
            packs_found_from_incident_indicator_fields = PackDependencies._search_packs_by_items_names_or_ids(
                related_incident_and_indicator_fields, id_set['IncidentFields'] + id_set['IndicatorFields'],
                exclude_ignored_dependencies)

            if packs_found_from_incident_indicator_fields:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_indicator_fields)
                layout_dependencies.update(pack_dependencies_data)

            if layout_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(layout_data.get("file_path", ""))} depends on: {layout_dependencies}',
                        fg='white'
                    )
            dependencies_packs.update(layout_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_incidents_fields_dependencies(pack_incidents_fields: list, id_set: dict, verbose: bool,
                                               exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects in incidents fields dependencies.

        Args:
            pack_incidents_fields (list): collection of pack incidents fields data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Incident Fields', fg='white')

        for incident_field in pack_incidents_fields:
            incident_field_data = next(iter(incident_field.values()))
            incident_field_dependencies = set()

            # If an incident field is used in a specific incident type than it does not depend on it.
            # e.g:
            # 1. deviceid in CommonTypes pack is being used in the Zimperium pack.
            #    The CommonTypes pack is not dependent on the Zimperium Pack, but vice versa.
            # 2. emailfrom in the Phishing pack is being used in the EWS pack.
            #    Phishing pack does not depend on EWS but vice versa.
            # The opposite dependencies are calculated in: _collect_playbook_dependencies, _collect_mappers_dependencies

            related_scripts = incident_field_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies)

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                incident_field_dependencies.update(pack_dependencies_data)

            if incident_field_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(incident_field_data.get("file_path", ""))} '
                        f'depends on: {incident_field_dependencies}', fg='white')
            dependencies_packs.update(incident_field_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_indicators_types_dependencies(pack_indicators_types: list, id_set: dict, verbose: bool,
                                               exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects in indicators types dependencies.

        Args:
            pack_indicators_types (list): collection of pack indicators types data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Indicator Types', fg='white')

        for indicator_type in pack_indicators_types:
            indicator_type_data = next(iter(indicator_type.values()))
            indicator_type_dependencies = set()

            #########################################################################################################
            # Do not collect integrations implementing reputation commands to not clutter CommonTypes and other packs
            # that have a indicator type using e.g `ip` command with all the reputation integrations.

            # this might be an issue if an indicator field is added to an indicator in Common Types
            # but not in the pack that implements it.
            #########################################################################################################

            # related_integrations = indicator_type_data.get('integrations', [])
            # packs_found_from_integrations = PackDependencies._search_packs_by_items_names(
            #     related_integrations, id_set['integrations'], exclude_ignored_dependencies)
            #
            # if packs_found_from_integrations:
            #     pack_dependencies_data = PackDependencies. \
            #         _label_as_optional(packs_found_from_integrations)
            #     indicator_type_dependencies.update(pack_dependencies_data)

            related_scripts = indicator_type_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies)

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_optional(packs_found_from_scripts)
                indicator_type_dependencies.update(pack_dependencies_data)

            if indicator_type_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(indicator_type_data.get("file_path", ""))} depends on: {indicator_type_dependencies}',
                        fg='white')
            dependencies_packs.update(indicator_type_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_integrations_dependencies(pack_integrations: list, id_set: dict, verbose: bool,
                                           exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects integrations dependencies.
        Args:
            pack_integrations (list): collection of pack integrations data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Integrations', fg='white')

        for integration in pack_integrations:
            integration_data = next(iter(integration.values()))
            integration_dependencies: set = set()

            related_classifiers = integration_data.get('classifiers', [])
            packs_found_from_classifiers = PackDependencies._search_packs_by_items_names_or_ids(
                related_classifiers, id_set['Classifiers'], exclude_ignored_dependencies)

            if packs_found_from_classifiers:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_classifiers)
                dependencies_packs.update(pack_dependencies_data)

            related_mappers = integration_data.get('mappers', [])
            packs_found_from_mappers = PackDependencies._search_packs_by_items_names_or_ids(
                related_mappers, id_set['Mappers'], exclude_ignored_dependencies)

            if packs_found_from_mappers:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_mappers)
                dependencies_packs.update(pack_dependencies_data)

            related_incident_types = integration_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'], exclude_ignored_dependencies)

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                dependencies_packs.update(pack_dependencies_data)

            related_indicator_fields = integration_data.get('indicator_fields')

            if related_indicator_fields:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory({related_indicator_fields})
                dependencies_packs.update(pack_dependencies_data)

            if integration_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(integration_data.get("file_path", ""))} depends on: {integration_dependencies}',
                        fg='white')
            dependencies_packs.update(integration_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_incidents_types_dependencies(pack_incidents_types: list, id_set: dict, verbose: bool,
                                              exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects in incidents types dependencies.

        Args:
            pack_incidents_types (list): collection of pack incidents types data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Incident Types', fg='white')

        for incident_type in pack_incidents_types:
            incident_type_data = next(iter(incident_type.values()))
            incident_type_dependencies = set()

            related_playbooks = incident_type_data.get('playbooks', [])
            packs_found_from_playbooks = PackDependencies._search_packs_by_items_names(
                related_playbooks, id_set['playbooks'], exclude_ignored_dependencies)

            if packs_found_from_playbooks:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_playbooks)
                incident_type_dependencies.update(pack_dependencies_data)

            related_scripts = incident_type_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies)

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                incident_type_dependencies.update(pack_dependencies_data)

            if incident_type_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(incident_type_data.get("file_path", ""))} depends on: {incident_type_dependencies}',
                        fg='white')
            dependencies_packs.update(incident_type_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_classifiers_dependencies(pack_classifiers: list, id_set: dict, verbose: bool,
                                          exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects in classifiers dependencies.

        Args:
            pack_classifiers (list): collection of pack classifiers data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Classifiers', fg='white')

        for classifier in pack_classifiers:
            classifier_data = next(iter(classifier.values()))
            classifier_dependencies = set()

            related_incident_types = classifier_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'], exclude_ignored_dependencies)

            # classifiers dependencies from incident types should be marked as optional unless CommonTypes pack,
            # as customers do not have to use the OOTB mapping.
            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                    packs_found_from_incident_types)
                classifier_dependencies.update(pack_dependencies_data)

            if classifier_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(classifier_data.get("file_path", ""))} depends on: {classifier_dependencies}',
                        fg='white')
            dependencies_packs.update(classifier_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_mappers_dependencies(pack_mappers: list, id_set: dict, verbose: bool,
                                      exclude_ignored_dependencies: bool = True) -> set:
        """
        Collects in mappers dependencies.

        Args:
            pack_mappers (list): collection of pack mappers data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho('### Mappers', fg='white')

        for mapper in pack_mappers:
            mapper_data = next(iter(mapper.values()))
            mapper_dependencies = set()

            related_incident_types = mapper_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'], exclude_ignored_dependencies)

            # mappers dependencies from incident types should be marked as optional unless CommonTypes Pack,
            # as customers do not have to use the OOTB mapping.
            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                    packs_found_from_incident_types)
                mapper_dependencies.update(pack_dependencies_data)

            related_incident_fields = mapper_data.get('incident_fields', [])
            packs_found_from_incident_fields = PackDependencies._search_packs_by_items_names_or_ids(
                related_incident_fields, id_set['IncidentFields'], exclude_ignored_dependencies)

            # mappers dependencies from incident fields should be marked as optional unless CommonTypes pack,
            # as customers do not have to use the OOTB mapping.
            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                    packs_found_from_incident_fields)
                mapper_dependencies.update(pack_dependencies_data)

            if mapper_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(mapper_data.get("file_path", ""))} depends on: {mapper_dependencies}',
                        fg='white')
            dependencies_packs.update(mapper_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_widget_dependencies(pack_widgets: list, id_set: dict, verbose: bool,
                                     exclude_ignored_dependencies: bool = True, header: str = "Widgets") -> set:
        """
        Collects widget dependencies.

        Args:
            pack_widgets (list): collection of pack widget data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        if verbose:
            click.secho(f'### {header}', fg='white')

        for widget in pack_widgets:
            widget_data = next(iter(widget.values()))
            widget_dependencies = set()

            related_scripts = widget_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies)

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                widget_dependencies.update(pack_dependencies_data)

            if widget_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(widget_data.get("file_path", ""))} depends on: {widget_dependencies}',
                        fg='white')
            dependencies_packs.update(widget_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_pack_items(pack_id: str, id_set: dict) -> dict:
        """
        Collects script and playbook content items inside specific pack.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.

        Returns:
            list, list: pack scripts and playbooks data.
        """
        pack_items = dict()

        pack_items['scripts'] = PackDependencies._search_for_pack_items(pack_id, id_set['scripts'])
        pack_items['playbooks'] = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])
        pack_items['layouts'] = PackDependencies._search_for_pack_items(pack_id, id_set['Layouts'])
        pack_items['incidents_fields'] = PackDependencies._search_for_pack_items(pack_id, id_set['IncidentFields'])
        pack_items['indicators_types'] = PackDependencies._search_for_pack_items(pack_id, id_set['IndicatorTypes'])
        pack_items['integrations'] = PackDependencies._search_for_pack_items(pack_id, id_set['integrations'])
        pack_items['incidents_types'] = PackDependencies._search_for_pack_items(pack_id, id_set['IncidentTypes'])
        pack_items['classifiers'] = PackDependencies._search_for_pack_items(pack_id, id_set['Classifiers'])
        pack_items['mappers'] = PackDependencies._search_for_pack_items(pack_id, id_set['Mappers'])
        pack_items['widgets'] = PackDependencies._search_for_pack_items(pack_id, id_set['Widgets'])
        pack_items['dashboards'] = PackDependencies._search_for_pack_items(pack_id, id_set['Dashboards'])
        pack_items['reports'] = PackDependencies._search_for_pack_items(pack_id, id_set['Reports'])

        if not sum(pack_items.values(), []):
            click.secho(f"Couldn't find any items for pack '{pack_id}'. Please make sure:\n"
                        f"1 - The spelling is correct.\n"
                        f"2 - The id_set.json file is up to date. Delete the file by running: `rm -rf "
                        f"Tests/id_set.json` and rerun the command.", fg='yellow')

        return pack_items

    @staticmethod
    def _find_pack_dependencies(pack_id: str, id_set: dict, verbose: bool,
                                exclude_ignored_dependencies: bool = True) -> set:
        """
        Searches for specific pack dependencies.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
        """
        if verbose:
            click.secho(f'\n# Pack ID: {pack_id}', fg='white')
        pack_items = PackDependencies._collect_pack_items(pack_id, id_set)

        scripts_dependencies = PackDependencies._collect_scripts_dependencies(
            pack_items['scripts'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        playbooks_dependencies = PackDependencies._collect_playbooks_dependencies(
            pack_items['playbooks'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        layouts_dependencies = PackDependencies._collect_layouts_dependencies(
            pack_items['layouts'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        incidents_fields_dependencies = PackDependencies._collect_incidents_fields_dependencies(
            pack_items['incidents_fields'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        indicators_types_dependencies = PackDependencies._collect_indicators_types_dependencies(
            pack_items['indicators_types'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        integrations_dependencies = PackDependencies._collect_integrations_dependencies(
            pack_items['integrations'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        incidents_types_dependencies = PackDependencies._collect_incidents_types_dependencies(
            pack_items['incidents_types'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        classifiers_dependencies = PackDependencies._collect_classifiers_dependencies(
            pack_items['classifiers'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        mappers_dependencies = PackDependencies._collect_mappers_dependencies(
            pack_items['mappers'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        widget_dependencies = PackDependencies._collect_widget_dependencies(
            pack_items['widgets'],
            id_set,
            verbose,
            exclude_ignored_dependencies
        )
        dashboards_dependencies = PackDependencies._collect_widget_dependencies(
            pack_items['dashboards'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            header='Dashboards'
        )
        reports_dependencies = PackDependencies._collect_widget_dependencies(
            pack_items['reports'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            header='Reports'
        )

        pack_dependencies = (
            scripts_dependencies | playbooks_dependencies | layouts_dependencies | incidents_fields_dependencies |
            indicators_types_dependencies | integrations_dependencies | incidents_types_dependencies |
            classifiers_dependencies | mappers_dependencies | widget_dependencies | dashboards_dependencies |
            reports_dependencies
        )

        return pack_dependencies

    @staticmethod
    def build_all_dependencies_graph(
            pack_ids: list,
            id_set: dict,
            verbose: bool = False,
            exclude_ignored_dependencies: bool = True
    ) -> nx.DiGraph:
        """
        Builds all level of dependencies and returns dependency graph for all packs

        Args:
            pack_ids (list): pack ids, currently pack folder names is in use.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            DiGraph: all dependencies of given packs.
        """
        dependency_graph = nx.DiGraph()
        for pack in pack_ids:
            dependency_graph.add_node(pack, mandatory_for_packs=[])
        for pack in pack_ids:
            dependencies = PackDependencies._find_pack_dependencies(
                pack, id_set, verbose=verbose, exclude_ignored_dependencies=exclude_ignored_dependencies)
            for dependency_name, is_mandatory in dependencies:
                if dependency_name == pack:
                    continue
                if dependency_name not in dependency_graph:
                    dependency_graph.add_node(dependency_name, mandatory_for_packs=[])
                dependency_graph.add_edge(pack, dependency_name)
                if is_mandatory:
                    dependency_graph.nodes()[dependency_name]['mandatory_for_packs'].append(pack)
        return dependency_graph

    @staticmethod
    def get_dependencies_subgraph_by_dfs(dependencies_graph: nx.DiGraph, source_pack: str) -> nx.DiGraph:
        """
        Generates a copy of the graph using DFS that starts with source_pack as source
        Args:
            dependencies_graph (DiGraph): A graph that represents the dependencies of all packs
            source_pack (str): The name of the pack that should be considered as source for the DFS algorithm

        Returns:
            DiGraph: The DFS sub graph with source_pack as source
        """
        dfs_edges = list(nx.edge_dfs(dependencies_graph, source_pack))
        subgraph_from_edges = dependencies_graph.edge_subgraph(dfs_edges)
        # We need to copy the graph so that we can modify it's content without any modifications to the original graph
        return deepcopy(subgraph_from_edges)

    @staticmethod
    def build_dependency_graph(pack_id: str, id_set: dict, verbose: bool,
                               exclude_ignored_dependencies: bool = True) -> nx.DiGraph:
        """
        Builds all level of dependencies and returns dependency graph.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            DiGraph: all level dependencies of given pack.
        """
        graph = nx.DiGraph()
        graph.add_node(pack_id)  # add pack id as root of the direct graph
        found_new_dependencies = True

        while found_new_dependencies:
            current_number_of_nodes = graph.number_of_nodes()
            leaf_nodes = [n for n in graph.nodes() if graph.out_degree(n) == 0]

            for leaf in leaf_nodes:
                leaf_dependencies = PackDependencies._find_pack_dependencies(
                    leaf, id_set, verbose=verbose, exclude_ignored_dependencies=exclude_ignored_dependencies)

                if leaf_dependencies:
                    for dependency_name, is_mandatory in leaf_dependencies:
                        if dependency_name not in graph.nodes():
                            graph.add_node(dependency_name, mandatory=is_mandatory)
                            graph.add_edge(leaf, dependency_name)

            found_new_dependencies = graph.number_of_nodes() > current_number_of_nodes

        return graph

    @staticmethod
    def find_dependencies(
            pack_name: str,
            id_set_path: str = '',
            exclude_ignored_dependencies: bool = True,
            update_pack_metadata: bool = True,
            silent_mode: bool = False,
            verbose: bool = False,
            debug_file_path: str = '',
            skip_id_set_creation: bool = False,
            use_pack_metadata: bool = False,
            complete_data: bool = False
    ) -> dict:
        """
        Main function for dependencies search and pack metadata update.

        Args:
            pack_name (str): pack id, currently pack folder name is in use.
            id_set_path (str): id set json.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.
            update_pack_metadata (bool): Determines whether to update to pack metadata or not.
            silent_mode (bool): Determines whether to echo the dependencies or not.
            verbose(bool): Whether to print the log to the console.
            skip_id_set_creation (bool): Whether to skip id_set.json file creation.
            complete_data (bool): Whether to update complete data on the dependent packs.

        Returns:
            Dict: first level dependencies of a given pack.

        """
        if not id_set_path or not os.path.isfile(id_set_path):
            if not skip_id_set_creation:
                id_set = IDSetCreator(print_logs=False).create_id_set()
            else:
                return {}
        else:
            with open(id_set_path, 'r') as id_set_file:
                id_set = json.load(id_set_file)
        if is_external_repository():
            print_warning('Running in a private repository, will download the id set from official content')
            id_set = get_merged_official_and_local_id_set(id_set, silent_mode=silent_mode)

        dependency_graph = PackDependencies.build_dependency_graph(
            pack_id=pack_name,
            id_set=id_set,
            verbose=verbose,
            exclude_ignored_dependencies=exclude_ignored_dependencies
        )
        first_level_dependencies, _ = parse_for_pack_metadata(
            dependency_graph,
            pack_name,
            verbose,
            complete_data=complete_data,
            id_set_data=id_set,
        )
        if update_pack_metadata:
            update_pack_metadata_with_dependencies(pack_name, first_level_dependencies)
        if not silent_mode:
            # print the found pack dependency results
            click.echo(click.style(f"Found dependencies result for {pack_name} pack:", bold=True))
            dependency_result = json.dumps(first_level_dependencies, indent=4)
            click.echo(click.style(dependency_result, bold=True))

        if use_pack_metadata:
            first_level_dependencies = PackDependencies.update_dependencies_from_pack_metadata(pack_name,
                                                                                               first_level_dependencies)

        return first_level_dependencies

    @staticmethod
    def update_dependencies_from_pack_metadata(pack_name, first_level_dependencies):
        """
        Update the dependencies by the pack metadata.

        Args:
            pack_name (str): the pack name to take the metadata from.
            first_level_dependencies (list): the given dependencies from the id set.

        Returns:
            A list of the updated dependencies.
        """
        pack_meta_file_content = PackDependencies.get_metadata_from_pack(pack_name)

        manual_dependencies = pack_meta_file_content.get('dependencies', {})
        first_level_dependencies.update(manual_dependencies)

        return first_level_dependencies

    @staticmethod
    def get_metadata_from_pack(pack_name):
        """
        Returns the pack metadata content of a given pack name.

        Args:
            pack_name (str): the pack name.

        Return:
            The pack metadata content.
        """

        with open(find_pack_path(pack_name)[0], "r") as pack_metadata:
            pack_meta_file_content = json.loads(pack_metadata.read())

        return pack_meta_file_content
