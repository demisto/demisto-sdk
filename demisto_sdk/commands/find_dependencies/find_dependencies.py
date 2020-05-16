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


def update_pack_metadata_with_dependencies(pack_folder_name, first_level_dependencies, all_level_dependencies):
    """
    Updates pack metadata with found parsed dependencies results.

    Args:
        pack_folder_name (str): pack folder name.
        first_level_dependencies (dict): first level dependencies data.
        all_level_dependencies (list): all level dependencies of pack.

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
        pack_metadata['displayedImages'] = all_level_dependencies

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
        Searches for implemented scrip/integration/playbook.

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
            pack_ids (list): pack ids list.

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
            if packs_found_from_scripts:  # found packs of implementing scripts
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_scripts)
                dependencies_packs.update(pack_dependencies_data)

            implementing_commands_and_integrations = playbook_data.get('command_to_integration', {})

            for command, integration_name in implementing_commands_and_integrations.items():
                packs_found_from_integration = PackDependencies._search_packs_by_items_names(integration_name,
                                                                                             id_set['integrations']) \
                    if integration_name else PackDependencies._search_packs_by_integration_command(command, id_set)

                if packs_found_from_integration:
                    pack_dependencies_data = PackDependencies._detect_generic_commands_dependencies(
                        packs_found_from_integration)
                    dependencies_packs.update(pack_dependencies_data)

            implementing_playbook_names = playbook_data.get('implementing_playbooks', [])
            packs_found_from_playbooks = PackDependencies._search_packs_by_items_names(implementing_playbook_names,
                                                                                       id_set['playbooks'])

            if packs_found_from_playbooks:
                pack_dependencies_data = PackDependencies._label_as_mandatory(packs_found_from_playbooks)
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
        pack_scripts = PackDependencies._search_for_pack_items(pack_id, id_set['scripts'])
        pack_playbooks = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])

        return pack_scripts, pack_playbooks

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
        pack_scripts, pack_playbooks = PackDependencies._collect_pack_items(pack_id, id_set)
        scripts_dependencies = PackDependencies._collect_scripts_dependencies(pack_scripts, id_set)
        playbooks_dependencies = PackDependencies._collect_playbooks_dependencies(pack_playbooks, id_set)
        pack_dependencies = scripts_dependencies | playbooks_dependencies
        # todo check if need to collect dependencies from other content items

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
            id_set_path (dict): id set json.

        """
        if not id_set_path:
            id_set = IDSetCreator(output=None, print_logs=False).create_id_set()
        else:
            with open(id_set_path, 'r') as id_set_file:
                id_set = json.load(id_set_file)

        dependency_graph = PackDependencies.build_dependency_graph(pack_id=pack_name, id_set=id_set)
        first_level_dependencies, all_level_dependencies = parse_for_pack_metadata(dependency_graph, pack_name)
        update_pack_metadata_with_dependencies(pack_name, first_level_dependencies, all_level_dependencies)
        # print the found pack dependency results
        click.echo(click.style(f"Found dependencies result for {pack_name} pack:", bold=True))
        dependency_result = json.dumps(first_level_dependencies, indent=4)
        click.echo(click.style(dependency_result, bold=True))
