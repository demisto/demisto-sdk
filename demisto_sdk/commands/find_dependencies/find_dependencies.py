import networkx as nx


class PackDependencies:

    @staticmethod
    def search_for_pack_items(pack_id, items_list):
        return list(filter(lambda s: next(iter(s.values())).get('pack') == pack_id, items_list))

    @staticmethod
    def search_packs_by_items_names(items_names, items_list):
        if not isinstance(items_names, list):
            items_names = [items_names]

        content_items = list(
            filter(lambda s: list(s.values())[0].get('name', '') in items_names and 'pack' in list(s.values())[0],
                   items_list))

        if content_items:
            return list(map(lambda s: next(iter(s.values()))['pack'], content_items))

        return None

    @staticmethod
    def search_packs_by_integration_command(command, id_set):
        integrations = list(
            filter(lambda i: command in list(i.values())[0].get('commands', []) and 'pack' in list(i.values())[0],
                   id_set['integrations']))

        if integrations:
            pack_names = [next(iter(i.values()))['pack'] for i in integrations]

            return pack_names

        return None

    @staticmethod
    def detect_optional_dependencies(pack_id):
        return [(p, True) if len(pack_id) > 1 else (p, False) for p in pack_id]

    @staticmethod
    def collect_scripts_dependencies(pack_scripts, id_set):
        dependencies_packs = set()

        for script in pack_scripts:
            dependencies_commands = script.get('depends_on', [])

            for command in dependencies_commands:
                pack_names = PackDependencies.search_packs_by_items_names(command, id_set['scripts'])

                if pack_names:
                    pack_dependencies_data = PackDependencies.detect_optional_dependencies(pack_names)
                    dependencies_packs.update(pack_dependencies_data)
                    continue

                pack_names = PackDependencies.search_packs_by_integration_command(command, id_set)

                if pack_names:
                    pack_dependencies_data = PackDependencies.detect_optional_dependencies(pack_names)
                    dependencies_packs.update(pack_dependencies_data)

                print(f"Pack not found for {command} command or task.")

        return dependencies_packs

    @staticmethod
    def collect_playbooks_dependencies(pack_playbooks, id_set):
        dependencies_packs = set()

        for playbook in pack_playbooks:
            playbook_data = next(iter(playbook.values()))

            implementing_script_names = playbook_data.get('implementing_scripts', [])
            packs_found_from_scripts = PackDependencies.search_packs_by_items_names(implementing_script_names,
                                                                                    id_set['scripts'])

            if packs_found_from_scripts:
                pack_dependencies_data = PackDependencies.detect_optional_dependencies(packs_found_from_scripts)
                dependencies_packs.update(pack_dependencies_data)

            implementing_commands_and_integrations = playbook_data.get('command_to_integration', {})

            for command, integration_name in implementing_commands_and_integrations.items():
                packs_found_from_integration = PackDependencies.search_packs_by_items_names(integration_name,
                                                                                            id_set['integrations']) \
                    if integration_name else PackDependencies.search_packs_by_integration_command(command, id_set)

                if packs_found_from_integration:
                    pack_dependencies_data = PackDependencies.detect_optional_dependencies(packs_found_from_integration)
                    dependencies_packs.update(pack_dependencies_data)

            implementing_playbook_names = playbook_data.get('implementing_playbooks', [])
            packs_found_from_playbooks = PackDependencies.search_packs_by_items_names(implementing_playbook_names,
                                                                                      id_set['playbooks'])

            if packs_found_from_playbooks:
                pack_dependencies_data = [(p, True) for p in packs_found_from_playbooks]
                dependencies_packs.update(pack_dependencies_data)

        return dependencies_packs

    @staticmethod
    def collect_pack_items(pack_id, id_set):
        pack_scripts = PackDependencies.search_for_pack_items(pack_id, id_set['scripts'])
        pack_playbooks = PackDependencies.search_for_pack_items(pack_id, id_set['playbooks'])

        return pack_scripts, pack_playbooks

    @staticmethod
    def find_pack_dependencies(pack_id, id_set):
        pack_scripts, pack_playbooks = PackDependencies.collect_pack_items(pack_id, id_set)
        scripts_dependencies = PackDependencies.collect_scripts_dependencies(pack_scripts, id_set)
        playbooks_dependencies = PackDependencies.collect_playbooks_dependencies(pack_playbooks, id_set)
        pack_dependencies = scripts_dependencies | playbooks_dependencies
        # todo check if need to collect dependencies from other content items

        return pack_dependencies

    @staticmethod
    def build_dependency_graph(pack_id, id_set, build_all_levels=True):
        graph = nx.DiGraph()
        graph.add_node(pack_id)
        found_new_dependencies = True

        while found_new_dependencies:
            current_number_of_nodes = graph.number_of_nodes()
            leaf_nodes = [n for n in graph.nodes() if graph.out_degree(n) == 0]

            for leaf in leaf_nodes:
                leaf_dependencies = PackDependencies.find_pack_dependencies(leaf, id_set)

                if leaf_dependencies:
                    for dependency_name, is_mandatory in leaf_dependencies:
                        if dependency_name not in graph.nodes():
                            graph.add_node(dependency_name, mandatory=is_mandatory)
                            graph.add_edge(leaf, dependency_name, mandatory=True)

            found_new_dependencies = graph.number_of_nodes() > current_number_of_nodes and build_all_levels

        return graph

    @staticmethod
    def parse_for_pack_metadata(dependency_graph):
        parsed_result = {}
        parsed_dependency_graph = [(k, v) for k, v in dependency_graph.nodes(data=True) if
                                   dependency_graph.in_degree(k) > 0]

        for dependency_id, additional_data in parsed_dependency_graph:
            additional_data['display_name'] = dependency_id  # todo change it later
            parsed_result[dependency_id] = additional_data

        return parsed_result
