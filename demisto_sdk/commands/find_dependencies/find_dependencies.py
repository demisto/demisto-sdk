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
    """
    pack_metadata_path = os.path.join(constants.PACKS_DIR, pack_folder_name, constants.PACKS_PACK_META_FILE_NAME)
    found_path_results = glob.glob(pack_metadata_path)

    return found_path_results


def find_pack_display_name(pack_folder_name):
    """
    Returns pack display name from pack_metadata.json file.
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
        """
        return list(filter(lambda s: next(iter(s.values())).get('pack') == pack_id, items_list))

    @staticmethod
    def _search_packs_by_items_names(items_names, items_list):
        """
        Searches for implemented scrip/integration/playbook.
        """
        if not isinstance(items_names, list):
            items_names = [items_names]

        content_items = list(
            filter(lambda s: list(s.values())[0].get('name', '') in items_names and 'pack' in list(s.values())[0],
                   items_list))

        if content_items:
            return list(map(lambda s: next(iter(s.values()))['pack'], content_items))

        return None

    @staticmethod
    def _search_packs_by_integration_command(command, id_set):
        """
        Filters packs by implementing integration commands.
        """
        integrations = list(
            filter(lambda i: command in list(i.values())[0].get('commands', []) and 'pack' in list(i.values())[0],
                   id_set['integrations']))

        if integrations:
            pack_names = [next(iter(i.values()))['pack'] for i in integrations]

            return pack_names

        return None

    @staticmethod
    def _detect_optional_dependencies(pack_ids):
        """
        Detects mandatory/non mandatory pack dependencies.
        """
        return [(p, False) if len(pack_ids) > 1 else (p, True) for p in pack_ids]

    @staticmethod
    def _collect_scripts_dependencies(pack_scripts, id_set):
        """
        Collects script pack dependencies.
        """
        dependencies_packs = set()

        for script_mapping in pack_scripts:
            script = next(iter(script_mapping.values()))
            dependencies_commands = script.get('depends_on', [])

            for command in dependencies_commands:
                pack_names = PackDependencies._search_packs_by_items_names(command, id_set['scripts'])

                if pack_names:
                    pack_dependencies_data = PackDependencies._detect_optional_dependencies(pack_names)
                    dependencies_packs.update(pack_dependencies_data)
                    continue

                pack_names = PackDependencies._search_packs_by_integration_command(command, id_set)

                if pack_names:
                    pack_dependencies_data = PackDependencies._detect_optional_dependencies(pack_names)
                    dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_playbooks_dependencies(pack_playbooks, id_set):
        """
        Collects playbook pack dependencies.
        """
        dependencies_packs = set()

        for playbook in pack_playbooks:
            playbook_data = next(iter(playbook.values()))

            implementing_script_names = playbook_data.get('implementing_scripts', [])
            packs_found_from_scripts = PackDependencies._search_packs_by_items_names(implementing_script_names,
                                                                                     id_set['scripts'])

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies._detect_optional_dependencies(packs_found_from_scripts)
                dependencies_packs.update(pack_dependencies_data)

            implementing_commands_and_integrations = playbook_data.get('command_to_integration', {})

            for command, integration_name in implementing_commands_and_integrations.items():
                packs_found_from_integration = PackDependencies._search_packs_by_items_names(integration_name,
                                                                                             id_set['integrations']) \
                    if integration_name else PackDependencies._search_packs_by_integration_command(command, id_set)

                if packs_found_from_integration:
                    pack_dependencies_data = PackDependencies._detect_optional_dependencies(
                        packs_found_from_integration)
                    dependencies_packs.update(pack_dependencies_data)

            implementing_playbook_names = playbook_data.get('implementing_playbooks', [])
            packs_found_from_playbooks = PackDependencies._search_packs_by_items_names(implementing_playbook_names,
                                                                                       id_set['playbooks'])

            if packs_found_from_playbooks:
                pack_dependencies_data = [(p, True) for p in packs_found_from_playbooks]
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def _collect_pack_items(pack_id, id_set):
        """
        Collects script and playbook content items inside specific pack.
        """
        pack_scripts = PackDependencies._search_for_pack_items(pack_id, id_set['scripts'])
        pack_playbooks = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])

        return pack_scripts, pack_playbooks

    @staticmethod
    def _find_pack_dependencies(pack_id, id_set):
        """
        Searches for specific pack dependencies.
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
        """
        graph = nx.DiGraph()
        graph.add_node(pack_id)
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
