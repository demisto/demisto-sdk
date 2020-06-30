import glob
import json
import os
import sys

import click
import networkx as nx
from demisto_sdk.commands.common import constants
from demisto_sdk.commands.common.tools import print_error
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator


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
    def _search_packs_by_items_names(items_names, items_list):
        """
        Searches for implemented script/integration/playbook.

        Args:
            items_names (str or list): items names to search.
            items_list (list): specific section of id set.

        Returns:
            set or None: found pack ids or None in case nothing was found.

        """
        if not isinstance(items_names, list):
            items_names = [items_names]

        content_items = list(
            filter(lambda s: list(s.values())[0].get('name', '') in items_names and 'pack' in list(s.values())[0],
                   items_list))

        if content_items:
            pack_names = list(map(lambda s: next(iter(s.values()))['pack'], content_items))

            return {p for p in pack_names if p not in constants.IGNORED_DEPENDENCY_CALCULATION}

        return None

    @staticmethod
    def _search_packs_by_items_names_or_ids(items_names, items_list):
        """
        Searches for implemented packs of the given items.

        Args:
            items_names (str or list): items names to search.
            items_list (list): specific section of id set.

        Returns:
            set or None: found pack ids or None in case nothing was found.

        """
        packs = set()
        if not isinstance(items_names, list):
            items_names = [items_names]

        for item_name in items_names:
            for item_from_id_set in items_list:
                machine_name = list(item_from_id_set.keys())[0]
                item_details = list(item_from_id_set.values())[0]
                if (item_name in machine_name or item_name in
                        item_details.get('name') and item_details.get('pack')):
                    packs.add(item_details.get('pack'))

        return packs

    @staticmethod
    def _search_packs_by_integration_command(command, id_set):
        """
        Filters packs by implementing integration commands.

        Args:
            command (str): integration command.
            id_set (dict): id set json.

        Returns:
            set: pack id without ignored packs.
        """
        integrations = list(
            filter(lambda i: command in list(i.values())[0].get('commands', []) and 'pack' in list(i.values())[0],
                   id_set['integrations']))

        if integrations:
            pack_names = [next(iter(i.values()))['pack'] for i in integrations]

            return {p for p in pack_names if p not in constants.IGNORED_DEPENDENCY_CALCULATION}

        return None

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
    def _collect_scripts_dependencies(pack_scripts, id_set):
        """
        Collects script pack dependencies.

        Args:
            pack_scripts (list): pack scripts collection.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for script_mapping in pack_scripts:
            script = next(iter(script_mapping.values()))
            # depends on list can have both scripts and integration commands
            dependencies_commands = script.get('depends_on', [])

            for command in dependencies_commands:
                # try to search dependency by scripts first
                pack_name = PackDependencies._search_packs_by_items_names(command, id_set['scripts'])

                if pack_name:  # found script dependency implementing pack name
                    pack_dependencies_data = PackDependencies._label_as_mandatory(pack_name)
                    dependencies_packs.update(pack_dependencies_data)  # set found script as mandatory
                    continue  # found dependency in script section, skipping to next depends on element

                # try to search dependency by integration integration
                pack_names = PackDependencies._search_packs_by_integration_command(command, id_set)

                if pack_names:  # found integration dependency implementing pack name
                    pack_dependencies_data = PackDependencies._detect_generic_commands_dependencies(pack_names)
                    dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_playbooks_dependencies(pack_playbooks, id_set):
        """
        Collects playbook pack dependencies.

        Args:
            pack_playbooks (list): collection of pack playbooks data.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for playbook in pack_playbooks:
            playbook_data = next(iter(playbook.values()))
            # searching for packs of implementing scripts
            implementing_script_names = playbook_data.get('implementing_scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(implementing_script_names,
                                                                                     id_set['scripts'])
            # ---- scripts packs ----
            if packs_found_from_scripts:  # found packs of implementing scripts
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_scripts)
                dependencies_packs.update(pack_dependencies_data)

            implementing_commands_and_integrations = playbook_data.get('command_to_integration', {})

            for command, integration_name in implementing_commands_and_integrations.items():
                packs_found_from_integration = PackDependencies._search_packs_by_items_names(integration_name,
                                                                                             id_set['integrations']) \
                    if integration_name else PackDependencies._search_packs_by_integration_command(command, id_set)

                # ---- integrations packs ----
                if packs_found_from_integration:
                    pack_dependencies_data = PackDependencies._detect_generic_commands_dependencies(
                        packs_found_from_integration)
                    dependencies_packs.update(pack_dependencies_data)

            # ---- other playbooks packs ----
            implementing_playbook_names = playbook_data.get('implementing_playbooks', [])
            packs_found_from_playbooks = PackDependencies._search_packs_by_items_names(implementing_playbook_names,
                                                                                       id_set['playbooks'])
            if packs_found_from_playbooks:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_playbooks)
                dependencies_packs.update(pack_dependencies_data)

            # ---- incident fields packs ----
            incident_fields = playbook_data.get('incident_fields', [])
            packs_found_from_incident_fields = PackDependencies._search_packs_by_items_names_or_ids(
                incident_fields, id_set['IncidentFields'])
            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_incident_fields)
                dependencies_packs.update(pack_dependencies_data)

            # ---- indicator fields packs ----
            indicator_fields = playbook_data.get('indicator_fields', [])
            packs_found_from_indicator_fields = PackDependencies._search_packs_by_items_names_or_ids(
                indicator_fields, id_set['IndicatorFields'])
            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_indicator_fields)
                dependencies_packs.update(pack_dependencies_data)
        return dependencies_packs

    @staticmethod
    def _collect_layouts_dependencies(pack_layouts, id_set):
        """
        Collects layouts pack dependencies.

        Args:
            pack_layouts (list): collection of pack playbooks data.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for layout in pack_layouts:
            layout_data = next(iter(layout.values()))

            related_incident_and_indicator_types = layout_data.get('incident_and_indicator_types', [])
            packs_found_from_incident_indicator_types = PackDependencies._search_packs_by_items_names(
                related_incident_and_indicator_types, id_set['IncidentTypes'] + id_set['IndicatorTypes'])

            if packs_found_from_incident_indicator_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_indicator_types)
                dependencies_packs.update(pack_dependencies_data)

            related_incident_and_indicator_fields = layout_data.get('incident_and_indicator_fields', [])
            packs_found_from_incident_indicator_fields = PackDependencies._search_packs_by_items_names_or_ids(
                related_incident_and_indicator_fields, id_set['IncidentFields'] + id_set['IndicatorFields'])

            if packs_found_from_incident_indicator_fields:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_indicator_fields)
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_incidents_fields_dependencies(pack_incidents_fields, id_set):
        """
        Collects in incidents fields dependencies.

        Args:
            pack_incidents_fields (list): collection of pack incidents fields data.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for incident_field in pack_incidents_fields:
            incident_field_data = next(iter(incident_field.values()))

            related_incident_types = incident_field_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'])

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                dependencies_packs.update(pack_dependencies_data)

            related_scripts = incident_field_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'])

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_indicators_types_dependencies(pack_indicators_types, id_set):
        """
        Collects in indicators types dependencies.

        Args:
            pack_indicators_types (list): collection of pack indicators types data.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for indicator_type in pack_indicators_types:
            incident_field_data = next(iter(indicator_type.values()))

            related_integrations = incident_field_data.get('integrations', [])
            packs_found_from_integrations = PackDependencies._search_packs_by_items_names(
                related_integrations, id_set['integrations'])

            if packs_found_from_integrations:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_integrations)
                dependencies_packs.update(pack_dependencies_data)

            related_scripts = incident_field_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'])

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_integrations_dependencies(pack_integrations, id_set):
        """
        Collects integrations dependencies.
        Args:
            pack_integrations (list): collection of pack integrations data.
            id_set (dict): id set json.
        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
        """
        dependencies_packs = set()

        for integration in pack_integrations:
            integration_data = next(iter(integration.values()))

            related_classifiers = integration_data.get('classifiers', [])
            packs_found_from_classifiers = PackDependencies._search_packs_by_items_names_or_ids(
                related_classifiers, id_set['Classifiers'])

            if packs_found_from_classifiers:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_classifiers)
                dependencies_packs.update(pack_dependencies_data)

            related_mappers = integration_data.get('mappers', [])
            packs_found_from_mappers = PackDependencies._search_packs_by_items_names_or_ids(
                related_mappers, id_set['Mappers'])

            if packs_found_from_mappers:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_mappers)
                dependencies_packs.update(pack_dependencies_data)

            related_incident_types = integration_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'])

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                dependencies_packs.update(pack_dependencies_data)

            related_indicator_fields = integration_data.get('indicator_fields')

            if related_indicator_fields:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory({related_indicator_fields})
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_incidents_types_dependencies(pack_incidents_types, id_set):
        """
        Collects in incidents types dependencies.

        Args:
            pack_incidents_types (list): collection of pack incidents types data.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for incident_type in pack_incidents_types:
            incident_field_data = next(iter(incident_type.values()))

            related_playbooks = incident_field_data.get('playbooks', [])
            packs_found_from_playbooks = PackDependencies._search_packs_by_items_names(
                related_playbooks, id_set['playbooks'])

            if packs_found_from_playbooks:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_playbooks)
                dependencies_packs.update(pack_dependencies_data)

            related_scripts = incident_field_data.get('scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(
                related_scripts, id_set['scripts'])

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_scripts)
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_classifiers_dependencies(pack_classifiers, id_set):
        """
        Collects in classifiers dependencies.

        Args:
            pack_classifiers (list): collection of pack classifiers data.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for classifier in pack_classifiers:
            classifier_data = next(iter(classifier.values()))

            related_incident_types = classifier_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'])

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_mappers_dependencies(pack_mappers, id_set):
        """
        Collects in mappers dependencies.

        Args:
            pack_mappers (list): collection of pack mappers data.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.

        """
        dependencies_packs = set()

        for mapper in pack_mappers:
            mapper_data = next(iter(mapper.values()))

            related_incident_types = mapper_data.get('incident_types', [])
            packs_found_from_incident_types = PackDependencies._search_packs_by_items_names(
                related_incident_types, id_set['IncidentTypes'])

            if packs_found_from_incident_types:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_types)
                dependencies_packs.update(pack_dependencies_data)

            related_incident_fields = mapper_data.get('incident_fields', [])
            packs_found_from_incident_fields = PackDependencies._search_packs_by_items_names_or_ids(
                related_incident_fields, id_set['IncidentFields'])

            if packs_found_from_incident_fields:
                pack_dependencies_data = PackDependencies. \
                    _label_as_mandatory(packs_found_from_incident_fields)
                dependencies_packs.update(pack_dependencies_data)

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

        return pack_items

    @staticmethod
    def _find_pack_dependencies(pack_id, id_set):
        """
        Searches for specific pack dependencies.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.

        Returns:
            set: dependencies data that includes pack id and whether is mandatory or not.
        """
        pack_items = PackDependencies._collect_pack_items(pack_id, id_set)

        scripts_dependencies = PackDependencies._collect_scripts_dependencies(pack_items['scripts'], id_set)
        playbooks_dependencies = PackDependencies._collect_playbooks_dependencies(pack_items['playbooks'], id_set)
        layouts_dependencies = PackDependencies._collect_layouts_dependencies(pack_items['layouts'], id_set)
        incidents_fields_dependencies = PackDependencies._collect_incidents_fields_dependencies(
            pack_items['incidents_fields'], id_set)
        indicators_types_dependencies = PackDependencies._collect_indicators_types_dependencies(
            pack_items['indicators_types'], id_set)
        integrations_dependencies = PackDependencies. \
            _collect_integrations_dependencies(pack_items['integrations'], id_set)
        incidents_types_dependencies = PackDependencies. \
            _collect_incidents_types_dependencies(pack_items['incidents_types'], id_set)
        classifiers_dependencies = PackDependencies. \
            _collect_classifiers_dependencies(pack_items['classifiers'], id_set)
        mappers_dependencies = PackDependencies. \
            _collect_mappers_dependencies(pack_items['mappers'], id_set)

        pack_dependencies = scripts_dependencies | playbooks_dependencies | layouts_dependencies | \
            incidents_fields_dependencies | indicators_types_dependencies | integrations_dependencies \
            | incidents_types_dependencies | classifiers_dependencies | mappers_dependencies

        return pack_dependencies

    @staticmethod
    def build_dependency_graph(pack_id, id_set):
        """
        Builds all level of dependencies and returns dependency graph.

        Args:
            pack_id (str): pack id, currently pack folder name is in use.
            id_set (dict): id set json.

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
                leaf_dependencies = PackDependencies._find_pack_dependencies(leaf, id_set)

                if leaf_dependencies:
                    for dependency_name, is_mandatory in leaf_dependencies:
                        if dependency_name not in graph.nodes():
                            graph.add_node(dependency_name, mandatory=is_mandatory)
                            graph.add_edge(leaf, dependency_name)

            found_new_dependencies = graph.number_of_nodes() > current_number_of_nodes

        return graph

    @staticmethod
    def find_dependencies(pack_name, id_set_path=None):
        """
        Main function for dependencies search and pack metadata update.

        Args:
            pack_name (str): pack id, currently pack folder name is in use.
            id_set_path (str): id set json.

        """
        if not id_set_path:
            id_set = IDSetCreator(output=None, print_logs=False).create_id_set()
        else:
            with open(id_set_path, 'r') as id_set_file:
                id_set = json.load(id_set_file)

        dependency_graph = PackDependencies.build_dependency_graph(pack_id=pack_name, id_set=id_set)
        first_level_dependencies, _ = parse_for_pack_metadata(dependency_graph, pack_name)
        update_pack_metadata_with_dependencies(pack_name, first_level_dependencies)
        # print the found pack dependency results
        click.echo(click.style(f"Found dependencies result for {pack_name} pack:", bold=True))
        dependency_result = json.dumps(first_level_dependencies, indent=4)
        click.echo(click.style(dependency_result, bold=True))
