import glob
import json
import os
import sys
from copy import deepcopy
from distutils.version import LooseVersion
from pathlib import Path
from pprint import pformat
from typing import Iterable, Optional, Tuple, Union

import click
import networkx as nx
from requests import RequestException

from demisto_sdk.commands.common import constants
from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_TO_VERSION, GENERIC_COMMANDS_NAMES,
    IGNORED_PACKS_IN_DEPENDENCY_CALC, PACKS_DIR)
from demisto_sdk.commands.common.tools import (ProcessPoolHandler,
                                               get_content_id_set,
                                               get_content_path, get_pack_name,
                                               is_external_repository,
                                               print_error, print_success,
                                               print_warning,
                                               wait_futures_complete)
from demisto_sdk.commands.common.update_id_set import merge_id_sets
from demisto_sdk.commands.create_id_set.create_id_set import (IDSetCreator,
                                                              get_id_set)

MINIMUM_DEPENDENCY_VERSION = LooseVersion('6.0.0')
COMMON_TYPES_PACK = 'CommonTypes'
PACKS_FULL_PATH = os.path.join(get_content_path(), PACKS_DIR)  # full path to Packs folder in content repo


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

    # Filter out the dependent items to avoid overloading the pack's metadata
    for _, dependency_info in first_level_dependencies.items():
        dependency_info.pop('depending_on_items_mandatorily')

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
    if duplicates:
        raise ValueError('Found duplicates when merging local id_set with official id_set')
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
                                     exclude_ignored_dependencies: bool = True, item_type=None):
        """
        Searches for implemented script/integration/playbook.
        Get a list of dict of (pack, item)

        Args:
            items_names (str or list): items names to search.
            items_list (list): specific section of id set.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            tupple of set: found pack ids.

        """
        packs_and_items_dict = {}
        if not isinstance(items_names, list):
            items_names = [items_names]

        pack_names = set()
        for item in items_list:
            item_id = list(item.keys())[0]
            item_details = list(item.values())[0]
            if item_details.get('name', '') in items_names and 'pack' in item_details and \
                    LooseVersion(item_details.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)) >= MINIMUM_DEPENDENCY_VERSION:
                pack_names.add(item_details.get('pack'))
                packs_and_items_dict[item_details.get('pack')] = (item_type, item_id)

        if not exclude_ignored_dependencies:
            return set(pack_names), packs_and_items_dict
        return {p for p in pack_names if p not in constants.IGNORED_DEPENDENCY_CALCULATION}, packs_and_items_dict

    @staticmethod
    def _search_packs_by_items_names_or_ids(items_names: Union[str, list],
                                            items_list: list,
                                            exclude_ignored_dependencies: bool = True,
                                            incident_or_indicator: Optional[str] = 'Both', items_type=None):
        """
        Searches for implemented packs of the given items.

        Args:
            items_names (str or list): items names to search.
            items_list (list): specific section of id set.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.
            incident_or_indicator (str):
                'Indicator' to search packs with indicator fields,
                'Incident' to search packs with incident fields,
                'Both' to search packs with indicator fields and incident fields.
        Returns:
            tuppele of
            set: found pack ids and
dict:       dict: found {pack, (item_type, item_id)} ids
        """
        packs_and_items_dict = {}
        packs = set()
        if not isinstance(items_names, list):
            items_names = [items_names]
        item_possible_ids = []

        for item_name in items_names:
            if incident_or_indicator == 'Incident':
                item_possible_ids = [item_name, f'incident_{item_name}', f'{item_name}-mapper']
            elif incident_or_indicator == 'Indicator':
                item_possible_ids = [item_name, f'indicator_{item_name}', f'{item_name}-mapper']
            elif incident_or_indicator == 'Generic':
                item_possible_ids = [item_name, f'generic_{item_name}', f'{item_name}-mapper']
            elif incident_or_indicator == 'Both':
                item_possible_ids = [item_name, f'incident_{item_name}', f'indicator_{item_name}',
                                     f'{item_name}-mapper']

            for item_from_id_set in items_list:
                item_id = list(item_from_id_set.keys())[0]
                item_details = list(item_from_id_set.values())[0]
                if (item_id in item_possible_ids or item_name == item_details.get('name')) \
                        and item_details.get('pack') \
                        and LooseVersion(item_details.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)) >= MINIMUM_DEPENDENCY_VERSION \
                        and (item_details['pack'] not in constants.IGNORED_DEPENDENCY_CALCULATION or
                             not exclude_ignored_dependencies):
                    packs.add(item_details.get('pack'))
                    packs_and_items_dict[item_details.get('pack')] = (items_type, item_id)

        return packs, packs_and_items_dict

    @staticmethod
    def _search_packs_by_integration_command(command: str,
                                             id_set: dict,
                                             exclude_ignored_dependencies: bool = True):
        """
        Filters packs by implementing integration commands.

        Args:
            command (str): integration command.
            id_set (dict): id set json.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            tuppele of:
            set: found pack ids
            dict: found {pack, (item_type, item_id)} ids
        """
        packs_and_items_dict = {}
        pack_names = set()
        for item in id_set['integrations']:
            item_id = list(item.keys())[0]
            item_details = list(item.values())[0]
            if command in item_details.get('commands', []) and 'pack' in item_details and \
                    LooseVersion(item_details.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)) >= MINIMUM_DEPENDENCY_VERSION:
                pack_names.add(item_details.get('pack'))
                packs_and_items_dict[item_details.get('pack')] = ('integration', item_id)

        if not exclude_ignored_dependencies:
            return set(pack_names), packs_and_items_dict
        return {p for p in pack_names if p not in constants.IGNORED_DEPENDENCY_CALCULATION}, packs_and_items_dict

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
                                      exclude_ignored_dependencies: bool = True,
                                      get_dependent_items: bool = False):
        """
        Collects script pack dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_scripts (list): pack scripts collection.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids
        """
        dependencies_packs = set()
        items_dependencies = dict()
        pack_dependencies_data = []
        if verbose:
            click.secho('### Scripts', fg='white')

        for script_mapping in pack_scripts:
            script_id = list(script_mapping.keys())[0]
            script = next(iter(script_mapping.values()))
            script_dependencies = set()

            # 'depends on' list can have both scripts and integration commands
            depends_on = script.get('depends_on', [])
            command_to_integration = list(script.get('command_to_integration', {}).keys())
            script_executions = script.get('script_executions', [])

            all_dependencies_commands = list(set(depends_on + command_to_integration + script_executions))
            dependencies_commands = list(filter(lambda cmd: cmd not in GENERIC_COMMANDS_NAMES,
                                                all_dependencies_commands))  # filter out generic commands

            for command in dependencies_commands:
                # try to search dependency by scripts first
                pack_names, packs_and_items_dict = PackDependencies._search_packs_by_items_names(command, id_set['scripts'], exclude_ignored_dependencies, 'script')

                if pack_names:  # found script dependency implementing pack name
                    pack_dependencies_data = PackDependencies._label_as_mandatory(pack_names)
                    script_dependencies.update(pack_dependencies_data)  # set found script as mandatory

                else:
                    # try to search dependency by integration
                    pack_names, packs_and_items_dict = PackDependencies._search_packs_by_integration_command(
                        command, id_set, exclude_ignored_dependencies)

                    if pack_names:  # found integration dependency implementing pack name
                        pack_dependencies_data = PackDependencies._detect_generic_commands_dependencies(pack_names)
                        script_dependencies.update(pack_dependencies_data)

                if pack_dependencies_data and get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'script', script_id,
                                              packs_and_items_dict)

            if verbose:
                click.secho(f'{os.path.basename(script.get("file_path", ""))} depends on: {script_dependencies}',
                            fg='white')
            dependencies_packs.update(script_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _differentiate_playbook_implementing_objects(implementing_objects: list,
                                                     skippable_tasks: set,
                                                     id_set_section: list,
                                                     exclude_ignored_dependencies: bool = True, section_type=None):
        """
        Differentiate implementing objects by skippable.

        Args:
            implementing_objects (list): playbook object collection.
            skippable_tasks (set): playbook skippable tasks.
            id_set_section (list): id set section corresponds to implementing_objects (scripts or playbooks).
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            tupple of:
            set: dependencies data that includes pack id and whether is mandatory or not.
            dict: found {mandatory_pack, (item_type, item_id)} ids
        """
        dependencies = set()

        mandatory_scripts = set(implementing_objects) - skippable_tasks
        optional_scripts = set(implementing_objects) - mandatory_scripts

        optional_script_packs, _ = PackDependencies._search_packs_by_items_names(
            list(optional_scripts), id_set_section, exclude_ignored_dependencies, section_type)
        if optional_script_packs:  # found packs of optional objects
            pack_dependencies_data = PackDependencies._label_as_optional(optional_script_packs)
            dependencies.update(pack_dependencies_data)

        mandatory_script_packs, mandatory_packs_and_items_dict = PackDependencies._search_packs_by_items_names(
            list(mandatory_scripts), id_set_section, exclude_ignored_dependencies, section_type)
        if mandatory_script_packs:  # found packs of mandatory objects
            pack_dependencies_data = PackDependencies._label_as_mandatory(mandatory_script_packs)
            dependencies.update(pack_dependencies_data)

        return dependencies, mandatory_packs_and_items_dict

    @staticmethod
    def _collect_playbooks_dependencies(pack_playbooks: list, id_set: dict, verbose: bool,
                                        exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects playbook pack dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_playbooks (list): collection of pack playbooks data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also mandatory dependency items dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()
        packs_and_items_dict = dict()
        if verbose:
            click.secho('### Playbooks', fg='white')

        for playbook in pack_playbooks:
            playbook_id = list(playbook.keys())[0]
            playbook_data = next(iter(playbook.values()))
            playbook_dependencies = set()

            skippable_tasks = set(playbook_data.get('skippable_tasks', []))

            # searching for packs of implementing integrations
            implementing_commands_and_integrations = playbook_data.get('command_to_integration', {})

            for command, integration_name in implementing_commands_and_integrations.items():
                packs_found_from_integration = set()
                if integration_name:
                    packs_found_from_integration, packs_and_items_dict = PackDependencies._search_packs_by_items_names(
                        integration_name, id_set['integrations'], exclude_ignored_dependencies, 'integration')
                elif command not in GENERIC_COMMANDS_NAMES:  # do not collect deps on generic command in Pbs
                    packs_found_from_integration, packs_and_items_dict = PackDependencies.\
                        _search_packs_by_integration_command(command, id_set, exclude_ignored_dependencies)

                if packs_found_from_integration:
                    if command in skippable_tasks:
                        pack_dependencies_data = PackDependencies._label_as_optional(packs_found_from_integration)
                    else:
                        pack_dependencies_data = PackDependencies._detect_generic_commands_dependencies(
                            packs_found_from_integration)
                    playbook_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'playbook', playbook_id,
                                                  packs_and_items_dict)

            implementing_scripts = playbook_data.get('implementing_scripts', []) + \
                playbook_data.get('filters', []) + \
                playbook_data.get('transformers', [])

            # searching for packs of implementing scripts
            dependencies, mandatory_packs_and_scripts_dict = PackDependencies.\
                _differentiate_playbook_implementing_objects(implementing_scripts, skippable_tasks, id_set['scripts'],
                                                             exclude_ignored_dependencies, 'script')
            playbook_dependencies.update(dependencies)
            if get_dependent_items:
                update_items_dependencies(dependencies, items_dependencies, 'playbook', playbook_id,
                                          mandatory_packs_and_scripts_dict)

            # searching for packs of implementing playbooks
            dependencies, mandatory_packs_and_playbooks_dict = PackDependencies.\
                _differentiate_playbook_implementing_objects(playbook_data.get('implementing_playbooks', []),
                                                             skippable_tasks, id_set['playbooks'],
                                                             exclude_ignored_dependencies,
                                                             'playbook')
            playbook_dependencies.update(dependencies)
            if get_dependent_items:
                update_items_dependencies(dependencies, items_dependencies, 'playbook', playbook_id,
                                          mandatory_packs_and_playbooks_dict)

            dependencies, mandatory_packs_and_lists_dict = PackDependencies._differentiate_playbook_implementing_objects(
                playbook_data.get('lists', []),
                skippable_tasks,
                id_set['Lists'],
                exclude_ignored_dependencies, 'list'
            )
            playbook_dependencies.update(dependencies)
            if get_dependent_items:
                update_items_dependencies(dependencies, items_dependencies, 'playbook', playbook_id,
                                          mandatory_packs_and_lists_dict)
            # ---- incident fields packs ----
            # playbook dependencies from incident fields should be marked as optional unless CommonTypes pack,
            # as customers do not have to use the OOTB inputs.
            incident_fields = playbook_data.get('incident_fields', [])
            packs_found_from_incident_fields, packs_and_incident_fields_dict = PackDependencies.\
                _search_packs_by_items_names_or_ids(incident_fields, id_set['IncidentFields'],
                                                    exclude_ignored_dependencies, 'incident_field')
            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                    packs_found_from_incident_fields)
                playbook_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'playbook', playbook_id,
                                              packs_and_incident_fields_dict)
            # ---- indicator fields packs ----
            # playbook dependencies from indicator fields should be marked as optional unless CommonTypes pack,
            # as customers do not have to use the OOTB inputs.
            indicator_fields = playbook_data.get('indicator_fields', [])
            packs_found_from_indicator_fields, packs_and_indicator_fields_dict = PackDependencies._search_packs_by_items_names_or_ids(
                indicator_fields, id_set['IndicatorFields'], exclude_ignored_dependencies, 'indicator_field')
            if packs_found_from_indicator_fields:
                pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                    packs_found_from_indicator_fields)
                playbook_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'playbook', playbook_id,
                                              packs_and_indicator_fields_dict)
            if playbook_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(playbook_data.get("file_path", ""))} depends on: {playbook_dependencies}',
                        fg='white'
                    )
            dependencies_packs.update(playbook_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_layouts_dependencies(pack_layouts: list,
                                      id_set: dict,
                                      verbose: bool,
                                      exclude_ignored_dependencies: bool = True,
                                      get_dependent_items: bool = False
                                      ):
        """
        Collects layouts pack dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_layouts (list): collection of pack layouts data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()
        if verbose:
            click.secho('### Layouts', fg='white')

        for layout in pack_layouts:
            layout_id = list(layout.keys())[0]
            layout_data = next(iter(layout.values()))
            layout_dependencies = set()
            if layout_data.get('definitionId') and layout_data.get('definitionId') not in ['incident', 'indicator']:
                layout_type = "Generic"

            elif layout_data.get('group') == 'indicator' or layout_data.get('kind') == 'indicatorsDetails':
                layout_type = 'Indicator'

            else:
                layout_type = 'Incident'

            if layout_type in ["Incident", "Indicator"]:
                related_types = layout_data.get('incident_and_indicator_types', [])
                packs_found_from_incident_indicator_types, packs_and_incident_indicator_dict = PackDependencies._search_packs_by_items_names(
                    related_types, id_set[f'{layout_type}Types'],
                    exclude_ignored_dependencies, 'layout')

                if packs_found_from_incident_indicator_types:
                    pack_dependencies_data = PackDependencies. \
                        _label_as_mandatory(packs_found_from_incident_indicator_types)
                    layout_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'layout', layout_id,
                                                  packs_and_incident_indicator_dict)
            related_fields = layout_data.get('incident_and_indicator_fields', [])
            packs_found_from_incident_indicator_fields, packs_and_incident_indicator_dict = PackDependencies.\
                _search_packs_by_items_names_or_ids(related_fields, id_set[f'{layout_type}Fields'],
                                                    exclude_ignored_dependencies, layout_type, f'{layout_type.lower()}_field')

            if packs_found_from_incident_indicator_fields:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_indicator_fields)
                layout_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'layout', layout_id,
                                              packs_and_incident_indicator_dict)

            if layout_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(layout_data.get("file_path", ""))} depends on: {layout_dependencies}',
                        fg='white'
                    )
            dependencies_packs.update(layout_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_incidents_fields_dependencies(pack_incidents_fields: list, id_set: dict, verbose: bool,
                                               exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects in incidents fields dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_incidents_fields (list): collection of pack incidents fields data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()
        if verbose:
            click.secho('### Incident Fields', fg='white')

        for incident_field in pack_incidents_fields:
            incident_field_id = list(incident_field.keys())[0]
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
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                incident_field_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'incident_field', incident_field_id,
                                              packs_and_scripts_dict)
            if incident_field_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(incident_field_data.get("file_path", ""))} '
                        f'depends on: {incident_field_dependencies}', fg='white')
            dependencies_packs.update(incident_field_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_indicators_types_dependencies(pack_indicators_types: list, id_set: dict, verbose: bool,
                                               exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects in indicators types dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_indicators_types (list): collection of pack indicators types data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()
        if verbose:
            click.secho('### Indicator Types', fg='white')

        for indicator_type in pack_indicators_types:
            indicator_type_id = list(indicator_type.keys())[0]
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
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_optional(packs_found_from_scripts)
                indicator_type_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'incident_type', indicator_type_id,
                                              packs_and_scripts_dict)

            if indicator_type_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(indicator_type_data.get("file_path", ""))} depends on: {indicator_type_dependencies}',
                        fg='white')
            dependencies_packs.update(indicator_type_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_integrations_dependencies(pack_integrations: list, id_set: dict, verbose: bool,
                                           exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects integrations dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.
        Args:
            pack_integrations (list): collection of pack integrations data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()
        if verbose:
            click.secho('### Integrations', fg='white')

        for integration in pack_integrations:
            integration_id = list(integration.keys())[0]
            integration_data = next(iter(integration.values()))
            integration_dependencies: set = set()

            related_classifiers = integration_data.get('classifiers', [])
            packs_found_from_classifiers, packs_and_classifiers_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_classifiers, id_set['Classifiers'], exclude_ignored_dependencies, 'classifier')

            if packs_found_from_classifiers:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_classifiers)
                dependencies_packs.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'integration', integration_id,
                                              packs_and_classifiers_dict)

            related_mappers = integration_data.get('mappers', [])
            packs_found_from_mappers, packs_and_mappers_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_mappers, id_set['Mappers'], exclude_ignored_dependencies, 'mapper')

            if packs_found_from_mappers:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_mappers)
                dependencies_packs.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'integration', integration_id,
                                              packs_and_mappers_dict)

            related_incident_types = integration_data.get('incident_types', [])
            packs_found_from_incident_types, packs_and_incident_types_dict = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'], exclude_ignored_dependencies, 'incident_type')

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                dependencies_packs.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'integration', integration_id,
                                                           packs_and_incident_types_dict)

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

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_incidents_types_dependencies(pack_incidents_types: list, id_set: dict, verbose: bool,
                                              exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects in incidents types dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_incidents_types (list): collection of pack incidents types data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()
        if verbose:
            click.secho('### Incident Types', fg='white')

        for incident_type in pack_incidents_types:
            incident_type_id = list(incident_type.keys())[0]
            incident_type_data = next(iter(incident_type.values()))
            incident_type_dependencies = set()

            related_playbooks = incident_type_data.get('playbooks', [])
            packs_found_from_playbooks, packs_and_playbooks_dict = PackDependencies._search_packs_by_items_names(
                related_playbooks, id_set['playbooks'], exclude_ignored_dependencies, 'playbook')

            if packs_found_from_playbooks:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_playbooks)
                incident_type_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'incident_type', incident_type_id,
                                              packs_and_playbooks_dict)

            related_scripts = incident_type_data.get('scripts', [])
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                incident_type_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'incident_type', incident_type_id,
                                              packs_and_scripts_dict)

            if incident_type_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(incident_type_data.get("file_path", ""))} depends on: {incident_type_dependencies}',
                        fg='white')
            dependencies_packs.update(incident_type_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_classifiers_dependencies(pack_classifiers: list, id_set: dict, verbose: bool,
                                          exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects in classifiers dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_classifiers (list): collection of pack classifiers data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()
        if verbose:
            click.secho('### Classifiers', fg='white')

        for classifier in pack_classifiers:
            classifier_id = list(classifier.keys())[0]
            classifier_data = next(iter(classifier.values()))
            classifier_dependencies = set()

            related_types = classifier_data.get('incident_types', [])

            if classifier_data.get('definitionId') and classifier_data.get('definitionId') not in ['incident',
                                                                                                   'indicator']:
                packs_found_from_generic_types, packs_and_generic_types_dict = PackDependencies._search_packs_by_items_names_or_ids(
                    related_types, id_set['GenericTypes'], exclude_ignored_dependencies, "Generic", 'generic_type')

                if packs_found_from_generic_types:
                    pack_dependencies_data = PackDependencies._label_as_mandatory(
                        packs_found_from_generic_types)
                    classifier_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'classifier', classifier_id,
                                                  packs_and_generic_types_dict)
            else:
                packs_found_from_incident_types, packs_and_incident_types_dict = PackDependencies._search_packs_by_items_names(
                    related_types, id_set['IncidentTypes'], exclude_ignored_dependencies, 'incident_type')

                # classifiers dependencies from incident types should be marked as optional unless CommonTypes pack,
                # as customers do not have to use the OOTB mapping.
                if packs_found_from_incident_types:
                    pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                        packs_found_from_incident_types)
                    classifier_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'classifier', classifier_id,
                                                  packs_and_incident_types_dict)

            # collect pack dependencies from transformers and filters
            related_scripts = classifier_data.get('filters', []) + classifier_data.get('transformers', [])
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_scripts)
                classifier_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies,'classifier',
                                                           classifier_id,
                                                           packs_and_scripts_dict)
            if classifier_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(classifier_data.get("file_path", ""))} depends on: {classifier_dependencies}',
                        fg='white')
            dependencies_packs.update(classifier_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_mappers_dependencies(pack_mappers: list, id_set: dict, verbose: bool,
                                      exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects in mappers dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_mappers (list): collection of pack mappers data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()

        if verbose:
            click.secho('### Mappers', fg='white')
# one dict item has no value
        for mapper in pack_mappers:
            mapper_id = list(mapper.keys())[0]
            mapper_data = next(iter(mapper.values()))
            mapper_dependencies = set()

            related_types = mapper_data.get('incident_types', [])

            if mapper_data.get('definitionId') and mapper_data.get('definitionId') not in ['incident', 'indicator']:
                packs_found_from_generic_types, packs_and_generic_types_dict = PackDependencies._search_packs_by_items_names(
                    related_types, id_set['GenericTypes'], exclude_ignored_dependencies, 'generic_type')

                if packs_found_from_generic_types:
                    pack_dependencies_data = PackDependencies._label_as_mandatory(
                        packs_found_from_generic_types)
                    mapper_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'mapper', mapper_id,
                                                  packs_and_generic_types_dict)

                packs_found_from_generic_fields, packs_and_generic_fields_dict = PackDependencies._search_packs_by_items_names(
                    related_types, id_set['GenericFields'], exclude_ignored_dependencies, 'generic_field')

                if packs_found_from_generic_fields:
                    pack_dependencies_data = PackDependencies._label_as_mandatory(
                        packs_found_from_generic_fields)
                    mapper_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'mapper', mapper_id,
                                                  packs_and_generic_fields_dict)
            else:
                packs_found_from_incident_types, packs_and_incident_types_dict = PackDependencies._search_packs_by_items_names(
                    related_types, id_set['IncidentTypes'], exclude_ignored_dependencies, 'incident_type')

                # mappers dependencies from incident types should be marked as optional unless CommonTypes Pack,
                # as customers do not have to use the OOTB mapping.
                if packs_found_from_incident_types:
                    pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                        packs_found_from_incident_types)
                    mapper_dependencies.update(pack_dependencies_data)

                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'mapper', mapper_id,
                                                  packs_and_incident_types_dict)

                related_fields = mapper_data.get('incident_fields', [])
                packs_found_from_incident_fields, packs_and_incident_fields_dict = PackDependencies._search_packs_by_items_names_or_ids(
                    related_fields, id_set['IncidentFields'], exclude_ignored_dependencies, 'incident_field')

                # mappers dependencies from incident fields should be marked as optional unless CommonTypes pack,
                # as customers do not have to use the OOTB mapping.
                if packs_found_from_incident_fields:
                    pack_dependencies_data = PackDependencies._update_optional_commontypes_pack_dependencies(
                        packs_found_from_incident_fields)
                    mapper_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'mapper', mapper_id,
                                                  packs_and_incident_fields_dict)
            # collect pack dependencies from transformers and filters
            related_scripts = mapper_data.get('filters', []) + mapper_data.get('transformers', [])
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_scripts)
                mapper_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'mapper', mapper_id,
                                              packs_and_scripts_dict)
            if mapper_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(mapper_data.get("file_path", ""))} depends on: {mapper_dependencies}',
                        fg='white')
            dependencies_packs.update(mapper_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_widget_dependencies(pack_widgets: list, id_set: dict, verbose: bool,
                                     exclude_ignored_dependencies: bool = True, header: str = "Widgets", get_dependent_items: bool = False):
        """
        Collects widget dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_widgets (list): collection of pack widget data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()

        if verbose:
            click.secho(f'### {header}', fg='white')

        for widget in pack_widgets:
            widget_id = list(widget.keys())[0]
            widget_data = next(iter(widget.values()))
            widget_dependencies = set()

            related_scripts = widget_data.get('scripts', [])
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                widget_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, header[:-1].lower(), widget_id,
                                              packs_and_scripts_dict)
            if widget_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(widget_data.get("file_path", ""))} depends on: {widget_dependencies}',
                        fg='white')
            dependencies_packs.update(widget_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_generic_types_dependencies(pack_generic_types: list, id_set: dict, verbose: bool,
                                            exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects generic types dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.
        Args:
            pack_generic_types (list): collection of pack generics types data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.
        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()

        if verbose:
            click.secho('### Generic Types', fg='white')

        for generic_type in pack_generic_types:
            generic_type_id = list(generic_type.keys())[0]
            generic_type_data = next(iter(generic_type.values()))
            generic_type_dependencies = set()

            related_scripts = generic_type_data.get('scripts', [])
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                generic_type_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_type',
                                                           generic_type_id,
                                                           packs_and_scripts_dict)
            related_definitions = generic_type_data.get('definitionId')
            packs_found_from_definitions, packs_and_definitions_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_definitions, id_set['GenericDefinitions'], exclude_ignored_dependencies, 'generic_definition')

            if packs_found_from_definitions:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_definitions)
                generic_type_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_type',
                                                           generic_type_id,
                                                           packs_and_definitions_dict)

            related_layout = generic_type_data.get('layout')
            packs_found_from_layout, packs_and_layouts_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_layout, id_set['Layouts'], exclude_ignored_dependencies, 'layout')

            if packs_found_from_definitions:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_layout)
                generic_type_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_type',
                                                           generic_type_id,
                                                           packs_and_layouts_dict)
            if generic_type_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(generic_type_data.get("file_path", ""))} depends on: {generic_type_dependencies}',
                        fg='white')
            dependencies_packs.update(generic_type_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_generic_fields_dependencies(pack_generic_fields: list, id_set: dict, verbose: bool,
                                             exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects in generic fields dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.

        Args:
            pack_generic_fields (list): collection of pack incidents fields data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()

        if verbose:
            click.secho('### Generic Fields', fg='white')

        for generic_field in pack_generic_fields:
            generic_field_id = list(generic_field.keys())[0]
            generic_field_data = next(iter(generic_field.values()))
            generic_field_dependencies = set()

            related_scripts = generic_field_data.get('scripts', [])
            packs_found_from_scripts, packs_and_scripts_dict = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies, 'script')

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                generic_field_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_field',
                                                           generic_field_id,
                                                           packs_and_scripts_dict)
            related_definitions = generic_field_data.get('definitionId')
            packs_found_from_definitions, packs_and_definitions_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_definitions, id_set['GenericDefinitions'], exclude_ignored_dependencies, 'generic_definition')

            if packs_found_from_definitions:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_definitions)
                generic_field_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_field',
                                                           generic_field_id,
                                                           packs_and_definitions_dict)
            related_types = generic_field_data.get('generic_types')
            packs_found_from_types, packs_and_types_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_types, id_set['GenericTypes'], exclude_ignored_dependencies, 'generic_type')

            if packs_found_from_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_types)
                generic_field_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_field',
                                                           generic_field_id,
                                                           packs_and_types_dict)
            if generic_field_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(generic_field_data.get("file_path", ""))} '
                        f'depends on: {generic_field_dependencies}', fg='white')
            dependencies_packs.update(generic_field_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_generic_modules_dependencies(pack_generic_modules: list, id_set: dict, verbose: bool,
                                              exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects generic types dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.
        Args:
            pack_generic_types (list): collection of pack generics types data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.
        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        dependencies_packs = set()
        items_dependencies = dict()

        if verbose:
            click.secho('### Generic Modules', fg='white')

        for generic_module in pack_generic_modules:
            generic_module_id = list(generic_module.keys())[0]
            generic_module_data = next(iter(generic_module.values()))
            generic_module_dependencies = set()

            related_definitions = generic_module_data.get('definitionIds')
            packs_found_from_definitions, packs_and_definitions_dict = PackDependencies._search_packs_by_items_names_or_ids(
                related_definitions, id_set['GenericDefinitions'], exclude_ignored_dependencies, 'generic_definition')

            if packs_found_from_definitions:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_definitions)
                generic_module_dependencies.update(pack_dependencies_data)
                if get_dependent_items:
                    update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_module',
                                                           generic_module_id,
                                                           packs_and_definitions_dict)
            related_views = generic_module_data.get('views', {})
            for view in related_views:
                related_dashboards = related_views.get(view, {}).get('dashboards', [])
                packs_found_from_dashboards, packs_and_dashboards_dict = PackDependencies._search_packs_by_items_names_or_ids(
                    related_dashboards, id_set['Dashboards'], exclude_ignored_dependencies, 'dashboard')

                if packs_found_from_dashboards:
                    pack_dependencies_data = PackDependencies. \
                        _label_as_mandatory(packs_found_from_dashboards)
                    generic_module_dependencies.update(pack_dependencies_data)
                    if get_dependent_items:
                        update_items_dependencies(pack_dependencies_data, items_dependencies, 'generic_module',
                                                               generic_module_id,
                                                               packs_and_dashboards_dict)

            if generic_module_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(generic_module_data.get("file_path", ""))} depends on: {generic_module_dependencies}',
                        fg='white')
            dependencies_packs.update(generic_module_dependencies)

        if get_dependent_items:
            return dependencies_packs, items_dependencies
        return dependencies_packs

    @staticmethod
    def _collect_jobs_dependencies(pack_jobs: list, id_set: dict, verbose: bool,
                                   exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Collects integrations dependencies. If get_dependent_on flag is on, collect the items causing the dependencies
        and the packs containing them.
        Args:
            pack_jobs (list): collection of pack job data.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
            if get_dependent_on: returns also dict: found {pack, (item_type, item_id)} ids

        """
        all_job_dependencies = set()
        items_dependencies = dict()

        if verbose:
            click.secho('### Jobs', fg='white')

        for job in pack_jobs:
            job_id = list(job.keys())[0]
            job_data = next(iter(job.values()))
            job_dependencies = set()

            # Playbook dependency
            packs_found_from_playbooks, packs_and_playbooks_dict = PackDependencies._search_packs_by_items_names_or_ids(
                job_data.get('playbookId', ''), id_set['playbooks'], exclude_ignored_dependencies, 'playbook')
            pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_playbooks)
            job_dependencies.update(pack_dependencies_data)
            if get_dependent_items:
               update_items_dependencies(pack_dependencies_data, items_dependencies, 'job',
                                                           job_id,
                                                           packs_and_playbooks_dict)
            # Specified feeds dependencies
            packs_found_from_feeds, packs_and_feeds_dict = PackDependencies._search_packs_by_items_names_or_ids(
                job_data.get('selectedFeeds', []), id_set['integrations'], exclude_ignored_dependencies, 'integration')
            pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_feeds)
            job_dependencies.update(pack_dependencies_data)
            if get_dependent_items:
               update_items_dependencies(pack_dependencies_data, items_dependencies, 'job',
                                                           job_id,
                                                           packs_and_feeds_dict)
            if job_dependencies:
                # do not trim spaces from the end of the string, they are required for the MD structure.
                if verbose:
                    click.secho(
                        f'{os.path.basename(job_data.get("file_path", ""))} depends on: {job_dependencies}',
                        fg='white')
            all_job_dependencies.update(job_dependencies)

        if get_dependent_items:
            return all_job_dependencies, items_dependencies
        return all_job_dependencies

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

        for pack_key, id_set_key in (('scripts', 'scripts',),
                                     ('playbooks', 'playbooks'),
                                     ('layouts', 'Layouts'),
                                     ('incidents_fields', 'IncidentFields'),
                                     ('indicators_fields', 'IndicatorFields'),
                                     ('indicators_types', 'IndicatorTypes'),
                                     ('integrations', 'integrations'),
                                     ('incidents_types', 'IncidentTypes'),
                                     ('classifiers', 'Classifiers'),
                                     ('mappers', 'Mappers'),
                                     ('widgets', 'Widgets'),
                                     ('dashboards', 'Dashboards'),
                                     ('reports', 'Reports'),
                                     ('generic_types', 'GenericTypes'),
                                     ('generic_fields', 'GenericFields'),
                                     ('generic_modules', 'GenericModules'),
                                     ('generic_definitions', 'GenericDefinitions'),
                                     ('lists', 'Lists'),
                                     ('jobs', 'Jobs')):
            if id_set_key not in id_set:
                raise RuntimeError(
                    "\n".join((f"Error: the {id_set_key} content type is missing from the id_set.",
                               "This may mean the existing id_set was created with an outdated version "
                               "of the Demisto SDK. Please delete content/Tests/id_set.json and "
                               "run demisto-sdk find-dependencies again."))
                )
            pack_items[pack_key] = PackDependencies._search_for_pack_items(pack_id, id_set[id_set_key])

        if not sum(pack_items.values(), []):
            click.secho(f"Couldn't find any items for pack '{pack_id}'. Please make sure:\n"
                        f"1 - The spelling is correct.\n"
                        f"2 - The id_set.json file is up to date. Delete the file by running: `rm -rf "
                        f"Tests/id_set.json` and rerun the command.", fg='yellow')

        return pack_items

    @staticmethod
    def _find_pack_dependencies(pack_id: str, id_set: dict, verbose: bool,
                                exclude_ignored_dependencies: bool = True, get_dependent_items: bool = False):
        """
        Searches for the packs and items the given pack is depending on.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.
        # TODO: add comment about only mandatory items
        Returns:
            tupple of:
            set: dependencies data that includes pack id and whether is mandatory or not.
            dict: found {pack, (item_type, item_id)} ids of mandatory dependent items.

        """
        if verbose:
            click.secho(f'\n# Pack ID: {pack_id}', fg='white')
        pack_items = PackDependencies._collect_pack_items(pack_id, id_set)

        scripts_dependencies, scripts_items_dependencies = PackDependencies._collect_scripts_dependencies(
            pack_items['scripts'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )

        playbooks_dependencies, playbooks_items_dependencies = PackDependencies._collect_playbooks_dependencies(
            pack_items['playbooks'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )

        layouts_dependencies, layouts_items_dependencies = PackDependencies._collect_layouts_dependencies(
            pack_items['layouts'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )
        incidents_fields_dependencies, incidents_fields_items_dependencies = PackDependencies._collect_incidents_fields_dependencies(
            pack_items['incidents_fields'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )
        indicators_types_dependencies, indicators_types_items_dependencies = PackDependencies._collect_indicators_types_dependencies(
            pack_items['indicators_types'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )

        integrations_dependencies, integrations_items_dependencies = PackDependencies._collect_integrations_dependencies(
            pack_items['integrations'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )
        incidents_types_dependencies, incidents_types_items_dependencies = PackDependencies._collect_incidents_types_dependencies(
            pack_items['incidents_types'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )
        classifiers_dependencies, classifiers_items_dependencies = PackDependencies._collect_classifiers_dependencies(
            pack_items['classifiers'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )
        mappers_dependencies, mappers_items_dependencies = PackDependencies._collect_mappers_dependencies(
            pack_items['mappers'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items
        )
        widget_dependencies, widgets_items_dependencies = PackDependencies._collect_widget_dependencies(
            pack_items['widgets'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items=get_dependent_items
        )
        dashboards_dependencies, dashboards_items_dependencies = PackDependencies._collect_widget_dependencies(
            pack_items['dashboards'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            header='Dashboards',
            get_dependent_items=get_dependent_items
        )
        reports_dependencies, reports_items_dependencies = PackDependencies._collect_widget_dependencies(
            pack_items['reports'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            header='Reports',
            get_dependent_items=get_dependent_items
        )
        generic_types_dependencies, generic_types_items_dependencies = PackDependencies._collect_generic_types_dependencies(
            pack_items['generic_types'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items=get_dependent_items
        )
        generic_fields_dependencies, generic_fields_items_dependencies = PackDependencies._collect_generic_fields_dependencies(
            pack_items['generic_fields'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items=get_dependent_items
        )
        generic_modules_dependencies, generic_modules_items_dependencies = PackDependencies._collect_generic_modules_dependencies(
            pack_items['generic_modules'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items=get_dependent_items
        )
        jobs_dependencies, jobs_items_dependencies = PackDependencies._collect_jobs_dependencies(
            pack_items['jobs'],
            id_set,
            verbose,
            exclude_ignored_dependencies,
            get_dependent_items=get_dependent_items
        )

        pack_dependencies = (
            scripts_dependencies | playbooks_dependencies | layouts_dependencies | incidents_fields_dependencies |
            indicators_types_dependencies | integrations_dependencies | incidents_types_dependencies |
            classifiers_dependencies | mappers_dependencies | widget_dependencies | dashboards_dependencies |
            reports_dependencies | generic_types_dependencies | generic_modules_dependencies |
            generic_fields_dependencies | jobs_dependencies
        )

        items_depenencies = {**scripts_items_dependencies, **playbooks_items_dependencies, **widgets_items_dependencies,
                             **layouts_items_dependencies, **incidents_fields_items_dependencies,
                             **indicators_types_items_dependencies, **integrations_items_dependencies,
                             **incidents_types_items_dependencies, **classifiers_items_dependencies,
                             **mappers_items_dependencies, **dashboards_items_dependencies, **reports_items_dependencies,
                             **generic_types_items_dependencies, **generic_fields_items_dependencies,
                             **generic_modules_items_dependencies, **jobs_items_dependencies}

        return pack_dependencies, items_depenencies

    @staticmethod
    def build_all_dependencies_graph(
            pack_ids: list,
            id_set: dict,
            verbose: bool = False,
            exclude_ignored_dependencies: bool = True
    ) -> nx.DiGraph:
        """
        Builds all level of dependencies and returns dependency graph for all packs.

        The Graph is of packs as nodes, and each vertical resembles a dependency. For each pack, the node
        representing it contains 4 data structures:
        1. A list of 'mandatory_for_packs' - this is a list of packs that the pack of this node is mandatory for.
        2. A dict of dicts 'mandatory_for_items' - the corresponding items causing the mandatory dependency, in the structure of:
        {(item_type, item_id): {pack_of_dependent_item: (dependent_item_type, dependent_item_id)}},
        when item_id is mandatory for dependent_item_id which is in pack pack_of_dependent_item.
        3. A list of tupples 'depending_on_packs' - the packs of which this pack is dependent on, and whether it is
         a mandatory dependency or not.
        4. A dict of dicts 'depending_on_items_mandatorily' the items causing these dependencies, but only the mandatory
        ones, in the sturcture of:
        {(item_type, item_id): {pack_of_item_to_be_dependent_on: (item_type_to_be_dependent_on, item_id_to_be_dependent_on)}}
        when item_id is dependent on item_id_to_be_dependent_on which is in pack pack_of_item_to_be_dependent_on.

        Args:
            pack_ids (list): pack ids, currently pack folder names is in use.
            id_set (dict): id set json.
            verbose (bool): Whether to log the dependencies to the console.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            DiGraph: all dependencies of given packs.
        """
        if verbose:
            print('Building the dependencies graph...')
        dependency_graph = nx.DiGraph()
        for pack in pack_ids:
            dependency_graph.add_node(pack, mandatory_for_packs=[], depending_on_items_mandatorily={},
                                      mandatory_for_items={}, depending_on_packs=[])
        for pack in pack_ids:
            if verbose:
                print(f'Adding {pack} pack dependencies to the graph...')
            # ITEMS *THIS PACK* IS DEPENDENT *ON*:
            dependencies, dependencies_items = PackDependencies._find_pack_dependencies(
                pack, id_set, verbose=verbose, exclude_ignored_dependencies=exclude_ignored_dependencies,
                get_dependent_items=True)
            for dependency_name, is_mandatory in dependencies:
                if dependency_name == pack:
                    continue
                if verbose:
                    print(f'Collecting info about {pack} and {dependency_name} dependencies')
                if dependency_name not in dependency_graph:
                    dependency_graph.add_node(dependency_name, mandatory_for_packs=[], depending_on_items_mandatorily={},
                                              mandatory_for_items={}, depending_on_packs=[])
                dependency_graph.add_edge(pack, dependency_name)
                if is_mandatory:
                    if verbose:
                        print(f'Found {dependency_name} pack is mandatory for {pack}')
                    dependency_graph.nodes()[dependency_name]['mandatory_for_packs'].append(pack)
                    if verbose:
                        print('Checking for the items causing the dependencies')
            for dependent_item, items_depending_on_item in dependencies_items.items():
                for pack_of_item_dependent_on, item_dependent_on in items_depending_on_item.items():
                    if pack_of_item_dependent_on == pack:
                        continue
                    if pack_of_item_dependent_on not in dependency_graph:
                        dependency_graph.add_node(pack_of_item_dependent_on, mandatory_for_packs=[],
                                                  depending_on_items_mandatorily={}, mandatory_for_items={},
                                                  depending_on_packs=[])
                    if dependency_graph.nodes()[pack_of_item_dependent_on].get('mandatory_for_items').get(item_dependent_on):
                        dependency_graph.nodes()[pack_of_item_dependent_on]['mandatory_for_items'][item_dependent_on].update({pack: dependent_item})
                    else:
                        dependency_graph.nodes()[pack_of_item_dependent_on]['mandatory_for_items'][item_dependent_on] = {pack: dependent_item}
            if verbose:
                print(f'\nPack {pack} and its dependencies were successfully added to the dependencies graph.')
            dependency_graph.nodes()[pack]['depending_on_packs'] = list(dependencies)
            dependency_graph.nodes()[pack]['depending_on_items_mandatorily'] = dependencies_items

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
                               exclude_ignored_dependencies: bool = True, get_dependent_items: bool = True) -> nx.DiGraph:
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
                leaf_dependencies, dependencies_items = PackDependencies._find_pack_dependencies(
                    leaf, id_set, verbose=verbose, exclude_ignored_dependencies=exclude_ignored_dependencies,
                    get_dependent_items=get_dependent_items)

                if leaf_dependencies:
                    for dependency_name, is_mandatory in leaf_dependencies:
                        if dependency_name not in graph.nodes():
                            graph.add_node(dependency_name, mandatory=is_mandatory, depending_on_items_mandatorily=dependencies_items)
                            graph.add_edge(leaf, dependency_name)

            found_new_dependencies = graph.number_of_nodes() > current_number_of_nodes

        return graph

    @staticmethod
    def check_arguments_find_dependencies(input_paths, all_packs_dependencies, output_path, get_dependent_on):
        if not input_paths:
            if not all_packs_dependencies:
                print_error("Please provide an input path. The path should be formatted as 'Packs/<some pack name>'. "
                            "For example, Packs/HelloWorld.")
                sys.exit(1)

        else:
            input_paths = [Path(path) for path in list(input_paths)]

            if input_paths and all_packs_dependencies:
                print_warning("You used the '--input/-i' argument, which is not relevant for when using the"
                              " '--all-packs-dependencies'. Ignoring this argument.")
                return

            elif len(input_paths) > 1 and not get_dependent_on:
                print_error("Please supply only one pack path to calculate its dependencies. Multiple inputs in only "
                            "supported when using the --get-dependent-on flag.")
                sys.exit(1)

            for path in input_paths:
                if len(path.parts) != 2 or path.parts[-2] != "Packs":
                    print_error(f"Input path ({path}) must be formatted as 'Packs/<some pack name>'. "
                                f"For example, Packs/HelloWorld.")
                    sys.exit(1)
                if get_dependent_on:
                    if path.parts[-1] in IGNORED_PACKS_IN_DEPENDENCY_CALC:
                        print_error(f"Finding all packs dependent on {path.parts[-1]} pack is not supported.")
                        sys.exit(1)
        if all_packs_dependencies and not output_path:
            print_error("Please insert path for the generated output using --output-path")
            sys.exit(1)
        if output_path and not all_packs_dependencies and not get_dependent_on:
            print_warning("You used the '--output-path' argument, which is only relevant for when using the"
                          " '--all-packs-dependencies' or '--get-dependent-on' flags. Ignoring this argument.")

    @staticmethod
    def find_dependencies_manager(
            id_set_path: str = '',
            update_pack_metadata: bool = False,
            verbose: bool = False,
            use_pack_metadata: bool = False,
            input_paths: Tuple = None,
            all_packs_dependencies: bool = False,
            get_dependent_on: bool = False,
            output_path: str = None,
    ) -> None:
        """

        Args:
            id_set_path: Path to id set json file.
            update_pack_metadata: Whether to update the pack metadata.
            verbose :Whether to print the log to the console
            use_pack_metadata: Whether to update the dependencies from the pack metadata.
            input_paths: Packs paths to find dependencies.
            all_packs_dependencies: Whether to calculate dependencies for all content packs.
            get_dependent_on: Whether to get the packs dependent on the given packs.
            output_path: The destination path for the packs dependencies json file.

        """

        PackDependencies.check_arguments_find_dependencies(input_paths, all_packs_dependencies, output_path,
                                                           get_dependent_on)

        if get_dependent_on:
            dependent_packs, _ = get_packs_dependent_on_given_packs(input_paths, id_set_path, output_path, verbose)
            print_success("Found the following dependent packs:")
            dependent_packs = json.dumps(dependent_packs, indent=4)
            click.echo(click.style(dependent_packs, bold=True))

        elif all_packs_dependencies:
            calculate_all_packs_dependencies(id_set_path, output_path, verbose)  # type: ignore[arg-type]
            print_success(f"The packs dependencies json was successfully saved to {output_path}")

        else:
            PackDependencies.find_dependencies(
                pack_name=Path(input_paths[0]).name,  # type: ignore
                id_set_path=id_set_path,
                verbose=verbose,
                update_pack_metadata=update_pack_metadata,
                use_pack_metadata=use_pack_metadata,
            )

    @staticmethod
    def find_dependencies(
            pack_name: str,
            id_set_path: str = '',
            exclude_ignored_dependencies: bool = True,
            update_pack_metadata: bool = False,
            silent_mode: bool = False,
            verbose: bool = False,
            skip_id_set_creation: bool = False,
            use_pack_metadata: bool = False,
            complete_data: bool = False,
    ) -> dict:
        """
        Main function for dependencies search and pack metadata update.

        Args:
            use_pack_metadata: Whether to update the dependencies from the pack metadata.
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

        if id_set_path and os.path.isfile(id_set_path):
            with open(id_set_path, 'r') as id_set_file:
                id_set = json.load(id_set_file)
        else:
            if skip_id_set_creation:
                return {}

            id_set = IDSetCreator(print_logs=False).create_id_set()

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
        if use_pack_metadata:
            first_level_dependencies = PackDependencies.update_dependencies_from_pack_metadata(pack_name,
                                                                                               first_level_dependencies)
        if update_pack_metadata:
            update_pack_metadata_with_dependencies(pack_name, first_level_dependencies)

        if not silent_mode:
            # print the found pack dependency results
            click.echo(click.style(f"Found dependencies result for {pack_name} pack:", bold=True))
            dependency_result = json.dumps(first_level_dependencies, indent=4)
            click.echo(click.style(dependency_result, bold=True))

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

def calculate_single_pack_depends_on(pack: str, dependency_graph: object, verbose: bool = False) -> Tuple[dict, list, str]:
    """

    Args:
        pack:
        dependency_graph:
        verbose:

    Returns:

    """
    try:
        pack_graph_node = dependency_graph.nodes[pack]
        subgraph = PackDependencies.get_dependencies_subgraph_by_dfs(dependency_graph, pack)
        first_level_dependencies = {}

        for man_pack in pack_graph_node.get('mandatory_for_packs'):
            if verbose:
                print(f'Parsing info of {man_pack} mandatory dependency of pack {pack} from graph')
            first_level_dependencies[man_pack] = {'mandatory': True}
            for item, dependent_item_and_pack in pack_graph_node.get('mandatory_for_items', {}).items():
                for dep_pack, dep_item in dependent_item_and_pack.items():
                    if dep_pack == man_pack:
                        if verbose:
                            print(f'Parsing info of dependent items {dep_item} from {dep_pack} on item {item} from {pack} from graph')
                        if first_level_dependencies[man_pack].get('dependent_items'):
                            first_level_dependencies[man_pack]['dependent_items'].append((item, dep_item))
                        else:
                            first_level_dependencies[man_pack]['dependent_items'] = [(item, dep_item)]
    except Exception as e:
        print_error(f"Failed calculating {pack} pack dependencies: {e}")
        raise

    return first_level_dependencies, pack


def calculate_single_pack_dependencies(pack: str, dependency_graph: object, verbose: bool = False) -> Tuple[dict, list, str]:
    """
    Calculates pack dependencies given a pack and a dependencies graph.
    First is extract the dependencies subgraph of the given graph only using DFS algorithm with the pack as source.

    Then, for all the dependencies of that pack it Replaces the 'mandatory_for_packs' key with a boolean key 'mandatory'
    which indicates whether this dependency is mandatory for this pack or not.

    Then using that subgraph we get the first-level dependencies and all-levels dependencies.

    Args:
        pack: The pack for which we need to calculate the dependencies
        dependency_graph: The full dependencies graph
        verbose: Whether to output a detailed response.

    Returns:
        first_level_dependencies: A dict of the form {'dependency_name': {'mandatory': < >, 'display_name': < >}}
        all_level_dependencies: A list with all dependencies names
        pack: The pack name
    """
    try:
        subgraph = PackDependencies.get_dependencies_subgraph_by_dfs(dependency_graph, pack)

        if verbose:
            print(f"Calculating {pack} pack dependencies.")

        for dependency_pack, additional_data in subgraph.nodes(data=True):
            if verbose:
                print(f'Iterating dependency {dependency_pack} for pack {pack}')
            additional_data['mandatory'] = pack in additional_data['mandatory_for_packs']
            del additional_data['mandatory_for_packs']
            del additional_data['mandatory_for_items']
            del additional_data['depending_on_packs']
            del additional_data['depending_on_items_mandatorily'] # This could be added as a value to the output, see issue XXX #TODO: fix

        first_level_dependencies, all_level_dependencies = parse_for_pack_metadata(subgraph, pack)
    except Exception:
        print_error(f"Failed calculating {pack} pack dependencies")
        raise

    return first_level_dependencies, all_level_dependencies, pack


def get_all_packs_dependency_graph(id_set: dict, packs: list) -> Iterable:
    """
    Gets a graph with dependencies for all packs
    Args:
        id_set: The content of id_set file
        packs: The packs that should be part of the dependencies calculation

    Returns:
        A graph with all packs dependencies
    """
    print("Calculating all packs dependencies.")
    # try:
    dependency_graph = PackDependencies.build_all_dependencies_graph(packs, id_set=id_set, verbose=False)
    return dependency_graph
    # except Exception as e:
    #     print_error(f"Failed calculating dependencies graph: {e}")
    #     exit(2)


def select_packs_for_calculation() -> list:
    """
    Select the packs on which the dependencies will be calculated on
    Returns:
        A list of packs
    """
    packs = []
    for pack in os.scandir(PACKS_FULL_PATH):
        if not pack.is_dir() or pack.name in IGNORED_PACKS_IN_DEPENDENCY_CALC:
            print_warning(f"Skipping dependency calculation of {pack.name} pack.")
            continue  # skipping ignored packs
        packs.append(pack.name)
    return packs


def calculate_all_packs_dependencies(id_set_path: str, output_path: str, verbose: bool = False) -> dict:
    """
    Calculates all packs dependencies in parallel.
    First - the method generates the full dependency graph. Then - using a process pool we extract the
    dependencies of each pack and adds them to the dict 'pack_dependencies_result'.
    Args:
        id_set_path: The id_set content.
        output_path: The path for the outputs json.
        verbose: Whether to print the log to the console.
    """

    def add_pack_metadata_results(results: Tuple) -> None:
        """
        This is a callback that should be called once the result of the future is ready.
        The results include: first_level_dependencies, all_level_dependencies, pack_name
        Using these results we write the dependencies
        """
        try:
            first_level_dependencies, all_level_dependencies, pack_name = results
            if verbose:
                print(f'Got dependencies for pack {pack_name}\n: {pformat(all_level_dependencies)}')
            pack_dependencies_result[pack_name] = {
                "dependencies": first_level_dependencies,
                "displayedImages": list(first_level_dependencies.keys()),
                "allLevelDependencies": all_level_dependencies,
                "path": os.path.join(PACKS_DIR, pack_name),
                "fullPath": os.path.abspath(os.path.join(PACKS_DIR, pack_name))
            }
        except Exception:
            print_error('Failed to collect pack dependencies results')
            raise

    pack_dependencies_result: dict = {}
    id_set = get_id_set(id_set_path)
    packs = select_packs_for_calculation()

    # Generating one graph with dependencies for all packs
    dependency_graph = get_all_packs_dependency_graph(id_set, packs)

    with ProcessPoolHandler() as pool:
        futures = []
        for pack in dependency_graph:
            futures.append(pool.schedule(calculate_single_pack_dependencies, args=(pack, dependency_graph, verbose)))
        wait_futures_complete(futures=futures, done_fn=add_pack_metadata_results)
        print(f"Number of created pack dependencies entries: {len(pack_dependencies_result.keys())}")
        # finished iteration over pack folders
        print_success("Finished dependencies calculation")

        with open(output_path, 'w') as pack_dependencies_file:
            json.dump(pack_dependencies_result, pack_dependencies_file, indent=4)
    return pack_dependencies_result


def get_packs_dependent_on_given_packs(packs, id_set_path, output_path=None, verbose=False) -> Tuple:
    """

    Args:
        packs: A list of paths of packs of interest. The resulted packs will be
         dependent on these packs.
        id_set_path: Path to id_set.json file.
        output_path: The path for the outputs json.
        verbose: Whether to print the log to the console.

    Returns:
        1. A dict with the given packs as keys, and the dependent packs with details about the dependency
         (such as mandatory or not) as values (as a nested dict).
        2. A set with the names of packs dependent on the given packs.
    """

    def collect_dependent_packs(results) -> None:
        try:
            first_level_dependencies, pack_name = results
            dependent_on_results[pack_name] = {
                "packsDependentOnThisPackMandatorily": first_level_dependencies,
                "path": os.path.join(PACKS_DIR, pack_name),
                "fullPath": os.path.abspath(os.path.join(PACKS_DIR, pack_name))
            }
            dependent_packs_list.extend(first_level_dependencies.keys())

        except Exception:
            print_error('Failed to collect the packs dependent on given packs')
            raise

    dependent_on_results: dict = {}
    dependent_packs_list: list = []
    id_set = get_id_set(id_set_path)
    all_packs = select_packs_for_calculation()
    dependency_graph = PackDependencies.build_all_dependencies_graph(all_packs, id_set=id_set, verbose=verbose)
    reverse_dependency_graph = nx.DiGraph.reverse(dependency_graph)
    pack_names = [get_pack_name(pack_path) for pack_path in packs]
    with ProcessPoolHandler() as pool:
        futures = []
        for pack in pack_names:
            futures.append(
                pool.schedule(calculate_single_pack_depends_on, args=(str(pack), reverse_dependency_graph, verbose),
                              ))
        wait_futures_complete(futures=futures, done_fn=collect_dependent_packs)
        # finished iteration over pack folders
        print_success("Finished calculating the dependencies on the given packs.")

        if output_path:
            with open(output_path, 'w') as pack_dependencies_file:
                json.dump(dependent_on_results, pack_dependencies_file, indent=4)
    return dependent_on_results, set(dependent_packs_list)


def update_items_dependencies(pack_dependencies_data, items_dependencies, current_entity_type, current_entity_id, packs_and_items_dict) -> None:
    """
    Updates the given items dependencies dict with the packs and items dict (those are items dependent on the current entitiy id)
    Args:
        pack_dependencies_data: list of tupples of (pack id, is mandatory).
        items_dependencies: the part of id set that contains the current type of item.
        current_entity_id: the entity of interest, that we are looking for items that are dependent on it.
        packs_and_items_dict: the dict containing the already known dependencies data.

    """
    entity_key = (current_entity_type, current_entity_id)
    if packs_and_items_dict:
        remove_unmandatory_items(packs_and_items_dict, pack_dependencies_data)
        if packs_and_items_dict:
            if items_dependencies.get(entity_key):
                items_dependencies[entity_key].update(packs_and_items_dict)
            else:
                items_dependencies[entity_key] = packs_and_items_dict


def remove_unmandatory_items(packs_and_items_dict, pack_dependencies_data) -> None:
    """
    Removes unmandatory items from packs_and_items_dict by the data in pack_dependencies_data.
    Args:
        packs_and_items_dict: dict generated based on id set, of {pack id: item from that pack}
        pack_dependencies_data: list of tupples of (pack id, is mandatory)
    """
    for pack, is_mandatory in pack_dependencies_data:
        if not is_mandatory and pack in packs_and_items_dict.keys():
            packs_and_items_dict.pop(pack)
