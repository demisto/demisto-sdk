import json
import os

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies


@pytest.fixture(scope="module")
def id_set():
    id_set_path = os.path.normpath(
        os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files', 'id_set', 'id_set.json'))

    with open(id_set_path, 'r') as id_set_file:
        id_set = json.load(id_set_file)
        yield id_set


class TestIdSetFilters:
    @pytest.mark.parametrize("item_section", ["scripts", "playbooks"])
    def test_search_for_pack_item_with_no_result(self, item_section, id_set):
        pack_id = "Non Existing Pack"
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set[item_section])

        assert len(found_filtered_result) == 0

    @pytest.mark.parametrize("pack_id", ["CalculateTimeDifference", "Expanse", "HelloWorld"])
    def test_search_for_pack_script_item(self, pack_id, id_set):
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['scripts'])

        assert len(found_filtered_result) > 0

    def test_search_for_specific_pack_script_item(self, id_set):
        pack_id = "PrismaCloudCompute"
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['scripts'])
        expected_result = [
            {
                "PrismaCloudComputeParseAuditAlert": {
                    "name": "PrismaCloudComputeParseAuditAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseAuditAlert/PrismaCloudComputeParseAuditAlert.yml",
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseCloudDiscoveryAlert": {
                    "name": "PrismaCloudComputeParseCloudDiscoveryAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseCloudDiscoveryAlert/PrismaCloudComputeParseCloudDiscoveryAlert.yml",
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseComplianceAlert": {
                    "name": "PrismaCloudComputeParseComplianceAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseComplianceAlert/PrismaCloudComputeParseComplianceAlert.yml",
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseVulnerabilityAlert": {
                    "name": "PrismaCloudComputeParseVulnerabilityAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseVulnerabilityAlert/PrismaCloudComputeParseVulnerabilityAlert.yml",
                    "pack": "PrismaCloudCompute"
                }
            }
        ]

        assert found_filtered_result == expected_result

    @pytest.mark.parametrize("pack_id", ["Claroty", "Code42", "Cymulate"])
    def test_search_for_pack_playbook_item(self, pack_id, id_set):
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])

        assert len(found_filtered_result) > 0

    def test_search_for_specific_pack_playbook_item(self, id_set):
        pack_id = "Expanse"
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])
        expected_result = [
            {
                "ExpanseParseRawIncident": {
                    "name": "Expanse Incident Playbook",
                    "file_path": "Packs/Expanse/Playbooks/Expanse_Incident_Playbook.yml",
                    "fromversion": "5.0.0",
                    "implementing_scripts": [
                        "ExpanseParseRawIncident"
                    ],
                    "tests": [
                        "No tests (auto formatted)"
                    ],
                    "pack": "Expanse"
                }
            }
        ]

        assert found_filtered_result == expected_result


class TestDependsOnScriptAndIntegration:
    @pytest.mark.parametrize("dependency_script,expected_result",
                             [("GetServerURL", {("GetServerURL", True)}),
                              ("HelloWorldScript", {("HelloWorld", True)}),
                              ("PrismaCloudComputeParseAuditAlert", {("PrismaCloudCompute", True)})
                              ])
    def test_collect_scripts_depends_on_script(self, dependency_script, expected_result, id_set):
        test_input = [
            {
                "DummyScript": {
                    "name": "DummyScript",
                    "file_path": "dummy_path",
                    "depends_on": [
                        dependency_script
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input, id_set=id_set)

        assert found_result == expected_result

    @pytest.mark.parametrize("dependency_integration_command,expected_result",
                             [("sslbl-get-indicators", {("Feedsslabusech", True)}),
                              ("activemq-subscribe", {("ActiveMQ", True)}),
                              ("alienvault-get-indicators", {("FeedAlienVault", True)})
                              ])
    def test_collect_scripts_depends_on_integration(self, dependency_integration_command, expected_result, id_set):
        test_input = [
            {
                "DummyScript": {
                    "name": "DummyScript",
                    "file_path": "dummy_path",
                    "depends_on": [
                        dependency_integration_command
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input, id_set=id_set)

        assert found_result == expected_result

    def test_collect_scripts_depends_on_two_scripts(self, id_set):
        test_input = [
            {
                "DummyScript": {
                    "name": "DummyScript",
                    "file_path": "dummy_path",
                    "depends_on": [
                        "PrismaCloudComputeParseAuditAlert",
                        "HelloWorldScript"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input, id_set=id_set)

        assert found_result == {('HelloWorld', True), ('PrismaCloudCompute', True)}

    def test_collect_scripts_depends_on_two_integrations(self, id_set):
        test_input = [
            {
                "DummyScript": {
                    "name": "DummyScript",
                    "file_path": "dummy_path",
                    "depends_on": [
                        "sslbl-get-indicators",
                        "ad-get-user"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input, id_set=id_set)

        assert found_result == {('Active_Directory_Query', True), ('Feedsslabusech', True)}

    def test_collect_scripts_depends_on_with_two_inputs(self, id_set):
        test_input = [
            {
                "DummyScript1": {
                    "name": "DummyScript1",
                    "file_path": "dummy_path1",
                    "depends_on": [
                        "sslbl-get-indicators"
                    ],
                    "pack": "dummy_pack"
                }
            },
            {
                "DummyScript2": {
                    "name": "DummyScript2",
                    "file_path": "dummy_path1",
                    "depends_on": [
                        "ad-get-user"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input, id_set=id_set)

        assert found_result == {('Active_Directory_Query', True), ('Feedsslabusech', True)}

    @pytest.mark.parametrize("generic_command", ["ip", "domain", "url"])
    def test_collect_detection_of_optional_dependencies(self, generic_command, id_set):
        test_input = [
            {
                "DummyScript": {
                    "name": "DummyScript",
                    "file_path": "dummy_path",
                    "depends_on": [
                        generic_command
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]

        dependencies_set = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input, id_set=id_set)

        assert len(dependencies_set) > 0

        for dependency_data in dependencies_set:
            assert not dependency_data[1]  # validate that mandatory is set to False


class TestDependsOnPlaybook:
    @pytest.mark.parametrize("dependency_script,expected_result",
                             [("GetServerURL", {("GetServerURL", True)}),
                              ("HelloWorldScript", {("HelloWorld", True)}),
                              ("PrismaCloudComputeParseAuditAlert", {("PrismaCloudCompute", True)})
                              ])
    def test_collect_playbooks_dependencies_on_script(self, dependency_script, expected_result, id_set):
        test_input = [
            {
                "Dummy Playbook": {
                    "name": "Dummy Playbook",
                    "file_path": "dummy_path",
                    "fromversion": "dummy_version",
                    "implementing_scripts": [
                        dependency_script
                    ],
                    "implementing_playbooks": [
                    ],
                    "command_to_integration": {
                    },
                    "tests": [
                        "dummy_playbook"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input, id_set=id_set)

        assert found_result == expected_result

    @pytest.mark.parametrize("dependency_playbook,expected_result",
                             [("Pentera Run Scan", {("Pcysys", True)}),
                              ("Indeni Demo", {("Indeni", True)}),
                              ("Failed Login Playbook - Slack v2", {("Slack", True)})
                              ])
    def test_collect_playbooks_dependencies_on_playbook(self, dependency_playbook, expected_result, id_set):
        test_input = [
            {
                "Dummy Playbook": {
                    "name": "Dummy Playbook",
                    "file_path": "dummy_path",
                    "fromversion": "dummy_version",
                    "implementing_scripts": [
                    ],
                    "implementing_playbooks": [
                        dependency_playbook
                    ],
                    "command_to_integration": {
                    },
                    "tests": [
                        "dummy_playbook"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input, id_set=id_set)

        assert found_result == expected_result

    @pytest.mark.parametrize("integration_command,expected_result",
                             [("aws-get-indicators", {("FeedAWS", True)}),
                              ("autofocus-get-indicators", {("FeedAutofocus", True)}),
                              ("alienvault-get-indicators", {("FeedAlienVault", True)})
                              ])
    def test_collect_playbooks_dependencies_on_integrations(self, integration_command, expected_result, id_set):
        test_input = [
            {
                "Dummy Playbook": {
                    "name": "Dummy Playbook",
                    "file_path": "dummy_path",
                    "fromversion": "dummy_version",
                    "implementing_scripts": [
                    ],
                    "implementing_playbooks": [
                    ],
                    "command_to_integration": {
                        integration_command: ""
                    },
                    "tests": [
                        "dummy_playbook"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input, id_set=id_set)

        assert found_result == expected_result

    def test_collect_playbooks_dependencies_on_integrations_with_brand(self, id_set):
        command = "ip"
        pack_name = "ipinfo"
        test_input = [
            {
                "Dummy Playbook": {
                    "name": "Dummy Playbook",
                    "file_path": "dummy_path",
                    "fromversion": "dummy_version",
                    "implementing_scripts": [
                    ],
                    "implementing_playbooks": [
                    ],
                    "command_to_integration": {
                        command: pack_name
                    },
                    "tests": [
                        "dummy_playbook"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]
        found_result_set = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input, id_set=id_set)

        assert len(found_result_set) == 1
        found_result = found_result_set.pop()
        assert found_result[0] == pack_name
        assert found_result[1]

    @pytest.mark.parametrize("integration_command", ["ip", "domain", "url"])
    def test_collect_detection_of_optional_dependencies_in_playbooks(self, integration_command, id_set):
        test_input = [
            {
                "Dummy Playbook": {
                    "name": "Dummy Playbook",
                    "file_path": "dummy_path",
                    "fromversion": "dummy_version",
                    "implementing_scripts": [
                    ],
                    "implementing_playbooks": [
                    ],
                    "command_to_integration": {
                        integration_command: ""
                    },
                    "tests": [
                        "dummy_playbook"
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]

        found_result_set = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input, id_set=id_set)

        assert len(found_result_set) > 0

        for found_result in found_result_set:
            assert not found_result[1]  # validate that mandatory is set to False


class TestDependsOnLayout:
    @pytest.mark.parametrize("dependency_types, dependency_fields ,expected_result",
                             [("Fake", "Fake", set()),
                              ("Fake", "Fake", set()),
                              ("Fake", "Fake", set())
                              ])
    def test_collect_layouts_dependencies(self, dependency_types, dependency_fields, expected_result, id_set):
        """
        Given
            - A layout entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the layout depends on.
        """
        test_input = [
            {
                "Dummy Layout": {
                    "typeID": "dummy_layout",
                    "name": "Dummy Layout",
                    "pack": "dummy_pack",
                    "kind": "edit",
                    "path": "dummy_path",
                    "incident_and_indicator_types": [
                        dependency_types
                    ],
                    "incident_and_indicator_fields": [
                        dependency_fields
                    ]
                }
            }
        ]
        found_result = PackDependencies._collect_layouts_dependencies(pack_layouts=test_input, id_set=id_set)

        # TODO: update the test once the implementation of all dependencies is working
        assert found_result == expected_result


class TestDependsOnIncidentField:
    @pytest.mark.parametrize("dependency_types, dependency_scripts ,expected_result",
                             [("Fake", "Fake", set()),
                              ("Fake", "Fake", set()),
                              ("Fake", "Fake", set())
                              ])
    def test_collect_layouts_dependencies(self, dependency_types, dependency_scripts, expected_result, id_set):
        """
        Given
            - An incident field entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the incident field depends on.
        """
        test_input = [
            {
                "Dummy Incident Field": {
                    "name": "Dummy Incident Field",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "incident_types": [
                        dependency_types
                    ],
                    "scripts": [
                        dependency_scripts
                    ]
                }
            }
        ]
        found_result = PackDependencies._collect_incidents_fields_dependencies(
            pack_incidents_fields=test_input, id_set=id_set)

        # TODO: update the test once the implementation of all dependencies is working
        assert found_result == expected_result


class TestDependsOnIndicatorType:
    @pytest.mark.parametrize("dependency_integrations, dependency_scripts ,expected_result",
                             [("Fake", "Fake", set()),
                              ("Fake", "Fake", set()),
                              ("Fake", "Fake", set())
                              ])
    def test_collect_layouts_dependencies(self, dependency_integrations, dependency_scripts, expected_result, id_set):
        """
        Given
            - An indicator type entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the indicator type depends on.
        """
        test_input = [
            {
                "Dummy Indicator Type": {
                    "name": "Dummy Indicator Type",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "integrations": [
                        dependency_integrations
                    ],
                    "scripts": [
                        dependency_scripts
                    ]
                }
            }
        ]
        found_result = PackDependencies._collect_indicators_types_dependencies(
            pack_indicators_types=test_input, id_set=id_set)

        # TODO: update the test once the implementation of all dependencies is working
        assert found_result == expected_result


class TestDependsOnIntegrations:
    @pytest.mark.parametrize(
        "dependency_classifiers, dependency_mappers, dependency_incident_types, dependency_indicator_fields, "
        "dependency_indicator_types, expected_result",
        [("Fake", [], "Fake", "Fake", "Fake", set()),
         ("Fake", [], "Fake", "Fake", "Fake", set()),
         ("Fake", [], "Fake", "Fake", "Fake", set())
         ])
    def test_collect_layouts_dependencies(self, dependency_classifiers, dependency_mappers, dependency_incident_types,
                                          dependency_indicator_fields, dependency_indicator_types, expected_result,
                                          id_set):
        """
        Given
            - An integration entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the integration depends on.
        """
        test_input = [
            {
                "Dummy Integration": {
                    "name": "Dummy Incident Field",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "classifiers": dependency_classifiers,
                    "mappers": dependency_mappers,
                    "incident_types": dependency_incident_types,
                    "indicator_fields": dependency_indicator_fields,
                    "indicator_types": dependency_indicator_types
                }
            }
        ]
        found_result = PackDependencies._collect_incidents_fields_dependencies(
            pack_incidents_fields=test_input, id_set=id_set)

        # TODO: update the test once the implementation of all dependencies is working
        assert found_result == expected_result


class TestDependencyGraph:
    def test_build_dependency_graph(self, id_set):
        pack_name = "ImpossibleTraveler"
        found_graph = PackDependencies.build_dependency_graph(pack_id=pack_name, id_set=id_set)
        root_of_graph = [n for n in found_graph.nodes if found_graph.in_degree(n) == 0][0]
        pack_dependencies = [n for n in found_graph.nodes if found_graph.in_degree(n) > 0]

        assert root_of_graph == pack_name
        assert len(pack_dependencies) > 0
