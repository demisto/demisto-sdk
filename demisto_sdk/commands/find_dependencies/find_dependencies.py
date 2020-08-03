import glob
import json
import os
import sys
from distutils.version import LooseVersion

import click
import networkx as nx
from demisto_sdk.commands.common import constants
from demisto_sdk.commands.common.tools import print_error
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator

MINIMUM_DEPENDENCY_VERSION = LooseVersion('6.0.0')


class VerboseFile:
    def __init__(self, file_path=''):
        self.file_path = file_path
        self.fd = None

    def __enter__(self):
        if self.file_path:
            self.fd = open(self.file_path, 'w')
        return self

    def write(self, message, ending='\n'):
        if self.fd:
            self.fd.write(f'{message}{ending}')

    def __exit__(self, type_, value, traceback):
        if self.fd:
            self.fd.close()
        self.fd = None


def parse_for_pack_metadata(dependency_graph, graph_root):
    """
    Parses calculated dependency graph and returns first and all level parsed dependency.
    Additionally returns list of displayed pack images of all graph levels.

    Args:
        dependency_graph (DiGraph): dependency direct graph.
        graph_root (str): graph root pack id.

    Returns:
        dict: first level dependencies parsed data.
        list: all level pack dependencies ids (is used for displaying dependencies images).

    """
    first_level_dependencies = {}
    parsed_dependency_graph = [(k, v) for k, v in dependency_graph.nodes(data=True) if
                               dependency_graph.has_edge(graph_root, k)]

    for dependency_id, additional_data in parsed_dependency_graph:
        additional_data['display_name'] = find_pack_display_name(dependency_id)
        first_level_dependencies[dependency_id] = additional_data

    all_level_dependencies = [n for n in dependency_graph.nodes if dependency_graph.in_degree(n) > 0]

    return first_level_dependencies, all_level_dependencies


def find_pack_path(pack_folder_name):
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


def find_pack_display_name(pack_folder_name):
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


def update_pack_metadata_with_dependencies(pack_folder_name, first_level_dependencies):
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


class PackDependencies:
    """
    Pack dependencies calculation class with relevant static methods.
    """

    @staticmethod
    def _search_for_pack_items(pack_id, items_list):
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
    def _search_packs_by_items_names(items_names, items_list, exclude_ignored_dependencies=True):
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
    def _search_packs_by_items_names_or_ids(items_names, items_list, exclude_ignored_dependencies=True):
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
    def _search_packs_by_integration_command(command, id_set, exclude_ignored_dependencies=True):
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
    def _detect_generic_commands_dependencies(pack_ids):
        """
        Detects whether dependency is mandatory or not. In case two packs implements the same command,
        mandatory is set to False.

        Args:
            pack_ids (set): pack ids list.

        Returns:
            list: collection of packs and mandatory flag set to True if more than 2 packs found.

        """
        return [(p, False) if len(pack_ids) > 1 else (p, True) for p in pack_ids]

    @staticmethod
    def _label_as_mandatory(pack_ids):
        """
        Sets pack as mandatory.

        Args:
            pack_ids (set): collection of pack ids to set as mandatory.

        Returns:
            list: collection of pack id and whether mandatory flag.

        """
        return [(p, True) for p in pack_ids]

    @staticmethod
    def _label_as_optional(pack_ids):
        """
        Sets pack as optional.

        Args:
            pack_ids (set): collection of pack ids to set as optional.

        Returns:
            list: collection of pack id and whether mandatory flag.

        """
        return [(p, False) for p in pack_ids]

    @staticmethod
    def _collect_scripts_dependencies(pack_scripts, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Collects script pack dependencies.

        Args:
            pack_scripts (list): pack scripts collection.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Scripts')

        for script_mapping in pack_scripts:
            script = next(iter(script_mapping.values()))
            script_dependencies = set()

            # depends on list can have both scripts and integration commands
            dependencies_commands = script.get('depends_on', [])

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

            verbose_file.write(
                f'{os.path.basename(script.get("file_path", ""))} depends on: '
                f'{script_dependencies}  '
            )
            dependencies_packs.update(script_dependencies)

        return dependencies_packs

    @staticmethod
    def _differentiate_playbook_implementing_objects(implementing_objects, skippable_tasks, id_set_section,
                                                     exclude_ignored_dependencies=True):
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
    def _collect_playbooks_dependencies(pack_playbooks, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Collects playbook pack dependencies.

        Args:
            pack_playbooks (list): collection of pack playbooks data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Playbooks')

        for playbook in pack_playbooks:
            playbook_data = next(iter(playbook.values()))
            playbook_dependencies = set()

            skippable_tasks = set(playbook_data.get('skippable_tasks', []))

            # searching for packs of implementing integrations
            implementing_commands_and_integrations = playbook_data.get('command_to_integration', {})

            for command, integration_name in implementing_commands_and_integrations.items():
                if integration_name:
                    packs_found_from_integration = PackDependencies._search_packs_by_items_names(
                        integration_name, id_set['integrations'], exclude_ignored_dependencies)
                else:
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
            incident_fields = playbook_data.get('incident_fields', [])
            packs_found_from_incident_fields = PackDependencies._search_packs_by_items_names_or_ids(
                incident_fields, id_set['IncidentFields'], exclude_ignored_dependencies)
            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_incident_fields)
                playbook_dependencies.update(pack_dependencies_data)

            # ---- indicator fields packs ----
            indicator_fields = playbook_data.get('indicator_fields', [])
            packs_found_from_indicator_fields = PackDependencies._search_packs_by_items_names_or_ids(
                indicator_fields, id_set['IndicatorFields'], exclude_ignored_dependencies)
            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_indicator_fields)
                playbook_dependencies.update(pack_dependencies_data)

            if playbook_dependencies:
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(playbook_data.get("file_path", ""))} depends on: '
                    f'{playbook_dependencies}  '
                )
            dependencies_packs.update(playbook_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_layouts_dependencies(pack_layouts, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Collects layouts pack dependencies.

        Args:
            pack_layouts (list): collection of pack playbooks data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Layouts')

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
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(layout_data.get("file_path", ""))} depends on: '
                    f'{layout_dependencies}  '
                )
            dependencies_packs.update(layout_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_incidents_fields_dependencies(pack_incidents_fields, id_set, verbose_file,
                                               exclude_ignored_dependencies=True):
        """
        Collects in incidents fields dependencies.

        Args:
            pack_incidents_fields (list): collection of pack incidents fields data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Incident Fields')

        for incident_field in pack_incidents_fields:
            incident_field_data = next(iter(incident_field.values()))
            incident_field_dependencies = set()

            # related_incident_types = incident_field_data.get('incident_types', [])
            # packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
            #     related_incident_types, id_set['IncidentTypes'])
            #
            # if packs_found_from_incident_types:
            #     pack_dependencies_data = PackDependencies. \
            #         _label_as_mandatory(packs_found_from_incident_types)
            #     dependencies_packs.update(pack_dependencies_data)

            related_scripts = incident_field_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies)

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                incident_field_dependencies.update(pack_dependencies_data)

            if incident_field_dependencies:
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(incident_field_data.get("file_path", ""))} depends on: '
                    f'{incident_field_dependencies}  '
                )
            dependencies_packs.update(incident_field_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_indicators_types_dependencies(pack_indicators_types, id_set, verbose_file,
                                               exclude_ignored_dependencies=True):
        """
        Collects in indicators types dependencies.

        Args:
            pack_indicators_types (list): collection of pack indicators types data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Indicator Types')

        for indicator_type in pack_indicators_types:
            indicator_type_data = next(iter(indicator_type.values()))
            indicator_type_dependencies = set()

            related_integrations = indicator_type_data.get('integrations', [])
            packs_found_from_integrations = PackDependencies._search_packs_by_items_names(
                related_integrations, id_set['integrations'], exclude_ignored_dependencies)

            if packs_found_from_integrations:
                pack_dependencies_data = PackDependencies. \
                    _label_as_optional(packs_found_from_integrations)
                indicator_type_dependencies.update(pack_dependencies_data)

            related_scripts = indicator_type_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'], exclude_ignored_dependencies)

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                indicator_type_dependencies.update(pack_dependencies_data)

            if indicator_type_dependencies:
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(indicator_type_data.get("file_path", ""))} depends on: '
                    f'{indicator_type_dependencies}  '
                )
            dependencies_packs.update(indicator_type_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_integrations_dependencies(pack_integrations, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Collects integrations dependencies.
        Args:
            pack_integrations (list): collection of pack integrations data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
        """
        dependencies_packs = set()
        verbose_file.write('\n### Integrations')

        for integration in pack_integrations:
            integration_data = next(iter(integration.values()))
            integration_dependencies = set()

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
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(integration_data.get("file_path", ""))} depends on: '
                    f'{integration_dependencies}  '
                )
            dependencies_packs.update(integration_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_incidents_types_dependencies(pack_incidents_types, id_set, verbose_file,
                                              exclude_ignored_dependencies=True):
        """
        Collects in incidents types dependencies.

        Args:
            pack_incidents_types (list): collection of pack incidents types data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Incident Types')

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
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(incident_type_data.get("file_path", ""))} depends on: '
                    f'{incident_type_dependencies}  '
                )
            dependencies_packs.update(incident_type_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_classifiers_dependencies(pack_classifiers, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Collects in classifiers dependencies.

        Args:
            pack_classifiers (list): collection of pack classifiers data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Classifiers')

        for classifier in pack_classifiers:
            classifier_data = next(iter(classifier.values()))
            classifier_dependencies = set()

            related_incident_types = classifier_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'], exclude_ignored_dependencies)

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                classifier_dependencies.update(pack_dependencies_data)

            if classifier_dependencies:
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(classifier_data.get("file_path", ""))} depends on: '
                    f'{classifier_dependencies}  '
                )
            dependencies_packs.update(classifier_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_mappers_dependencies(pack_mappers, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Collects in mappers dependencies.

        Args:
            pack_mappers (list): collection of pack mappers data.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()
        verbose_file.write('\n### Mappers')

        for mapper in pack_mappers:
            mapper_data = next(iter(mapper.values()))
            mapper_dependencies = set()

            related_incident_types = mapper_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'], exclude_ignored_dependencies)

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                mapper_dependencies.update(pack_dependencies_data)

            related_incident_fields = mapper_data.get('incident_fields', [])
            packs_found_from_incident_fields = PackDependencies._search_packs_by_items_names_or_ids(
                related_incident_fields, id_set['IncidentFields'], exclude_ignored_dependencies)

            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_fields)
                mapper_dependencies.update(pack_dependencies_data)

            if mapper_dependencies:
                # do not trim spaces from end of string, there are required for the MD structure.
                verbose_file.write(
                    f'{os.path.basename(mapper_data.get("file_path", ""))} depends on: '
                    f'{mapper_dependencies}  '
                )
            dependencies_packs.update(mapper_dependencies)

        return dependencies_packs

    @staticmethod
    def _collect_pack_items(pack_id, id_set):
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

        if not sum(pack_items.values(), []):
            raise ValueError(f"Couldn't find any items for pack '{pack_id}'. make sure your spelling is correct.")

        return pack_items

    @staticmethod
    def _find_pack_dependencies(pack_id, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Searches for specific pack dependencies.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
        """
        verbose_file.write(f'\n\n# Pack ID: {pack_id}')
        pack_items = PackDependencies._collect_pack_items(pack_id, id_set)

        scripts_dependencies = PackDependencies._collect_scripts_dependencies(
            pack_items['scripts'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        playbooks_dependencies = PackDependencies._collect_playbooks_dependencies(
            pack_items['playbooks'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        layouts_dependencies = PackDependencies._collect_layouts_dependencies(
            pack_items['layouts'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        incidents_fields_dependencies = PackDependencies._collect_incidents_fields_dependencies(
            pack_items['incidents_fields'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        indicators_types_dependencies = PackDependencies._collect_indicators_types_dependencies(
            pack_items['indicators_types'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        integrations_dependencies = PackDependencies._collect_integrations_dependencies(
            pack_items['integrations'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        incidents_types_dependencies = PackDependencies._collect_incidents_types_dependencies(
            pack_items['incidents_types'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        classifiers_dependencies = PackDependencies._collect_classifiers_dependencies(
            pack_items['classifiers'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )
        mappers_dependencies = PackDependencies._collect_mappers_dependencies(
            pack_items['mappers'],
            id_set,
            verbose_file,
            exclude_ignored_dependencies
        )

        pack_dependencies = (
            scripts_dependencies | playbooks_dependencies | layouts_dependencies |
            incidents_fields_dependencies | indicators_types_dependencies | integrations_dependencies |
            incidents_types_dependencies | classifiers_dependencies | mappers_dependencies
        )

        return pack_dependencies

    @staticmethod
    def build_dependency_graph(pack_id, id_set, verbose_file, exclude_ignored_dependencies=True):
        """
        Builds all level of dependencies and returns dependency graph.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.
            verbose_file (VerboseFile): path to dependency explanations file.
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
                    leaf, id_set, verbose_file=verbose_file, exclude_ignored_dependencies=exclude_ignored_dependencies)

                if leaf_dependencies:
                    for dependency_name, is_mandatory in leaf_dependencies:
                        if dependency_name not in graph.nodes():
                            graph.add_node(dependency_name, mandatory=is_mandatory)
                            graph.add_edge(leaf, dependency_name)

            found_new_dependencies = graph.number_of_nodes() > current_number_of_nodes

        return graph

    @staticmethod
    def find_dependencies(pack_name, id_set_path='', exclude_ignored_dependencies=True, update_pack_metadata=True,
                          silent_mode=False, debug_file_path=''):
        """
        Main function for dependencies search and pack metadata update.

        Args:
            pack_name (str): pack id, currently pack folder name is in use.
            id_set_path (str): id set json.
            debug_file_path (str): path to dependency explanations file.
            silent_mode (bool): Determines whether to echo the dependencies or not.
            update_pack_metadata (bool): Determines whether to update to pack metadata or not.
            exclude_ignored_dependencies (bool): Determines whether to include unsupported dependencies or not.

        Returns:
            Dict: first level dependencies of a given pack.

        """
        if not id_set_path or not os.path.isfile(id_set_path):
            id_set = IDSetCreator(print_logs=False).create_id_set()
        else:
            with open(id_set_path, 'r') as id_set_file:
                id_set = json.load(id_set_file)

        with VerboseFile(debug_file_path) as verbose_file:
            dependency_graph = PackDependencies.build_dependency_graph(
                pack_id=pack_name, id_set=id_set, verbose_file=verbose_file,
                exclude_ignored_dependencies=exclude_ignored_dependencies)
        first_level_dependencies, _ = parse_for_pack_metadata(dependency_graph, pack_name)
        if update_pack_metadata:
            update_pack_metadata_with_dependencies(pack_name, first_level_dependencies)
        if not silent_mode:
            # print the found pack dependency results
            click.echo(click.style(f"Found dependencies result for {pack_name} pack:", bold=True))
            dependency_result = json.dumps(first_level_dependencies, indent=4)
            click.echo(click.style(dependency_result, bold=True))
        return first_level_dependencies
