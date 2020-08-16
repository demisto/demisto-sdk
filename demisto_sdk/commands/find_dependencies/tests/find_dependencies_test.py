import json
import os

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.find_dependencies.find_dependencies import (
    PackDependencies, VerboseFile)
from TestSuite.utils import IsEqualFunctions


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

        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['scripts'])

        assert IsEqualFunctions.is_lists_equal(found_filtered_result, expected_result)

    @pytest.mark.parametrize("pack_id", ["Claroty", "Code42", "Cymulate"])
    def test_search_for_pack_playbook_item(self, pack_id, id_set):
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])

        assert len(found_filtered_result) > 0

    def test_search_for_specific_pack_playbook_item(self, id_set):
        pack_id = "Expanse"

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

        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])

        assert IsEqualFunctions.is_lists_equal(found_filtered_result, expected_result)


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

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

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

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_depends_on_two_scripts(self, id_set):
        expected_result = {('HelloWorld', True), ('PrismaCloudCompute', True)}

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

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts__filter_toversion(self, id_set):
        """
        Given
            - A script entry in the id_set depending on QRadar command.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the script depends on.
            - Should ignore the Deprecated pack due to toversion settings of old QRadar integration.
        """
        expected_result = {('QRadar', True)}

        test_input = [
            {
                "DummyScript": {
                    "name": "DummyScript",
                    "file_path": "dummy_path",
                    "depends_on": [
                        "qradar-searches",
                    ],
                    "pack": "dummy_pack"
                }
            }
        ]

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      exclude_ignored_dependencies=False
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_depends_on_two_integrations(self, id_set):
        expected_result = {('Active_Directory_Query', True), ('Feedsslabusech', True)}

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

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_depends_on_with_two_inputs(self, id_set):
        expected_result = {('Active_Directory_Query', True), ('Feedsslabusech', True)}

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

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

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

        dependencies_set = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                          id_set=id_set,
                                                                          verbose_file=VerboseFile(),
                                                                          )

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

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose_file=VerboseFile(),
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

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

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose_file=VerboseFile(),
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

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

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose_file=VerboseFile(),
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

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
        found_result_set = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                            id_set=id_set,
                                                                            verbose_file=VerboseFile(),
                                                                            )

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

        found_result_set = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                            id_set=id_set,
                                                                            verbose_file=VerboseFile(),
                                                                            )

        assert len(found_result_set) > 0

        for found_result in found_result_set:
            assert not found_result[1]  # validate that mandatory is set to False

    def test_collect_playbooks_dependencies_on_incident_fields(self, id_set):
        expected_result = {("DigitalGuardian", True), ("EmployeeOffboarding", True)}
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
                    },
                    "tests": [
                        "dummy_playbook"
                    ],
                    "pack": "dummy_pack",
                    "incident_fields": [
                        "digitalguardianusername",
                        "Google Display Name"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose_file=VerboseFile(),
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_playbooks_dependencies_skip_unavailable(self, id_set):
        """
        Given
            - A playbook entry in the id_set.
            -

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the playbook depends on.
        """
        expected_result = {
            # playbooks:
            ('Slack', False), ('Indeni', True),
            # integrations:
            ('FeedAlienVault', False), ('ipinfo', True), ('FeedAutofocus', True),
            # scripts:
            ('GetServerURL', False), ('HelloWorld', True),
        }
        test_input = [
            {
                'Dummy Playbook': {
                    'name': 'Dummy Playbook',
                    'file_path': 'dummy_path',
                    'fromversion': 'dummy_version',
                    'implementing_scripts': [
                        'GetServerURL',
                        'HelloWorldScript',
                    ],
                    'implementing_playbooks': [
                        'Failed Login Playbook - Slack v2',
                        'Indeni Demo',
                    ],
                    'command_to_integration': {
                        'alienvault-get-indicators': '',
                        'ip': 'ipinfo',
                        'autofocus-get-indicators': '',
                    },
                    'tests': [
                        'dummy_playbook'
                    ],
                    'pack': 'dummy_pack',
                    'incident_fields': [
                    ],
                    'skippable_tasks': [
                        'Print',
                        'Failed Login Playbook - Slack v2',
                        'alienvault-get-indicators',
                        'GetServerURL',
                    ]
                }
            },
        ]

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose_file=VerboseFile(),
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnLayout:
    def test_collect_layouts_dependencies(self, id_set):
        """
        Given
            - A layout entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the layout depends on.
        """
        expected_result = {("FeedMitreAttack", True), ("PrismaCloudCompute", True), ("CommonTypes", True),
                           ("CrisisManagement", True)}

        test_input = [
            {
                "Dummy Layout": {
                    "typeID": "dummy_layout",
                    "name": "Dummy Layout",
                    "pack": "dummy_pack",
                    "kind": "edit",
                    "path": "dummy_path",
                    "incident_and_indicator_types": [
                        "MITRE ATT&CK",
                        "Prisma Cloud Compute Cloud Discovery"
                    ],
                    "incident_and_indicator_fields": [
                        "indicator_adminname",
                        "indicator_jobtitle"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_layouts_dependencies(pack_layouts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_layouts_dependencies_filter_toversion(self, id_set):
        """
        Given
            - A layout entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the layout depends on.
            - Should ignore the NonSupported pack due to toversion settings of both indicator type and field.
        """
        expected_result = {("CommonTypes", True)}

        test_input = [
            {
                "Dummy Layout": {
                    "typeID": "dummy_layout",
                    "name": "Dummy Layout",
                    "pack": "dummy_pack",
                    "kind": "edit",
                    "path": "dummy_path",
                    "incident_and_indicator_types": [
                        "accountRep",
                    ],
                    "incident_and_indicator_fields": [
                        "indicator_tags",
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_layouts_dependencies(pack_layouts=test_input,
                                                                      id_set=id_set,
                                                                      verbose_file=VerboseFile(),
                                                                      exclude_ignored_dependencies=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnIncidentField:
    def test_collect_incident_field_dependencies(self, id_set):
        """
        Given
            - An incident field entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the incident field depends on.
        """
        expected_result = {
            # incident types
            # ("Expanse", True), ("IllusiveNetworks", True),
            # scripts
            ("Carbon_Black_Enterprise_Response", True), ("Phishing", True)
        }

        test_input = [
            {
                "Dummy Incident Field": {
                    "name": "Dummy Incident Field",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "incident_types": [
                        "Expanse Appearance",
                        "Illusive Networks Incident"
                    ],
                    "scripts": [
                        "CBLiveFetchFiles",
                        "CheckEmailAuthenticity"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_incidents_fields_dependencies(
            pack_incidents_fields=test_input,
            id_set=id_set,
            verbose_file=VerboseFile(),
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnIndicatorType:
    def test_collect_indicator_type_dependencies(self, id_set):
        """
        Given
            - An indicator type entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the indicator type depends on.
        """
        expected_result = {
            # integration dependencies
            ("Feedsslabusech", False), ("AbuseDB", False), ("ActiveMQ", False),
            # script dependencies
            ("CommonScripts", True), ("Carbon_Black_Enterprise_Response", True)
        }

        test_input = [
            {
                "Dummy Indicator Type": {
                    "name": "Dummy Indicator Type",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "integrations": [
                        "abuse.ch SSL Blacklist Feed",
                        "AbuseIPDB",
                        "ActiveMQ"
                    ],
                    "scripts": [
                        "AssignAnalystToIncident",
                        "CBAlerts"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_indicators_types_dependencies(
            pack_indicators_types=test_input,
            id_set=id_set,
            verbose_file=VerboseFile(),
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnIntegrations:
    def test_collect_integration_dependencies(self, id_set):
        """
        Given
            - An integration entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the integration depends on.
        """
        expected_result = {("HelloWorld", True), ("Claroty", True), ("EWS", True), ("CrisisManagement", True),
                           ("CommonTypes", True)}

        test_input = [
            {
                "Dummy Integration": {
                    "name": "Dummy Integration",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "classifiers": "HelloWorld",
                    "mappers": [
                        "Claroty-mapper",
                        "EWS v2-mapper"
                    ],
                    "incident_types": "HR Ticket",
                    "indicator_fields": "CommonTypes",
                }
            }
        ]

        found_result = PackDependencies._collect_integrations_dependencies(
            pack_integrations=test_input,
            id_set=id_set,
            verbose_file=VerboseFile(),
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnIncidentType:
    def test_collect_incident_type_dependencies(self, id_set):
        """
        Given
            - An incident type entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the incident type depends on.
        """
        expected_result = {("AutoFocus", True), ("Volatility", True)}

        test_input = [
            {
                "Dummy Incident Type": {
                    "name": "Dummy Incident Type",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "playbooks": "Autofocus Query Samples, Sessions and Tags",
                    "scripts": "AnalyzeMemImage"
                }
            }
        ]

        found_result = PackDependencies._collect_incidents_types_dependencies(
            pack_incidents_types=test_input,
            id_set=id_set,
            verbose_file=VerboseFile(),

        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnClassifiers:
    def test_collect_classifier_dependencies(self, id_set):
        """
        Given
            - A classifier entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the classifier depends on.
        """
        expected_result = {("Claroty", True), ("PAN-OS", True), ("Logzio", True)}

        test_input = [
            {
                "Dummy Classifier": {
                    "name": "Dummy Classifier",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "incident_types": [
                        "Claroty Integrity Incident",
                        "FirewallUpgrade",
                        "Logz.io Alert"
                    ],
                }
            }
        ]

        found_result = PackDependencies._collect_classifiers_dependencies(
            pack_classifiers=test_input,
            id_set=id_set,
            verbose_file=VerboseFile(),
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnMappers:
    def test_collect_mapper_dependencies(self, id_set):
        """
        Given
            - A mapper entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the mapper depends on.
        """
        expected_result = {("AccessInvestigation", True), ("CommonTypes", True), ("PrismaCloud", True),
                           ("BruteForce", True)}

        test_input = [
            {
                "Dummy Mapper": {
                    "name": "Dummy Mapper",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "incident_types": [
                        "Access",
                        "Authentication",
                        "AWS CloudTrail Misconfiguration"
                    ],
                    "incident_fields": [
                        "incident_accountgroups",
                        "incident_accountid"
                    ],
                }
            }
        ]

        found_result = PackDependencies._collect_mappers_dependencies(
            pack_mappers=test_input,
            id_set=id_set,
            verbose_file=VerboseFile(),
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


SEARCH_PACKS_INPUT = [
    (['type'], 'IncidentFields', set()),
    (['emailaddress'], 'IncidentFields', {'Compliance'}),
    (['E-mail Address'], 'IncidentFields', {'Compliance'}),
    (['adminemail'], 'IndicatorFields', {'CommonTypes'}),
    (['Admin Email'], 'IndicatorFields', {'CommonTypes'}),
    (['Claroty'], 'Mappers', {'Claroty'}),
    (['Claroty - Incoming Mapper'], 'Mappers', {'Claroty'}),
    (['Cortex XDR - IR'], 'Classifiers', {'CortexXDR'}),
]


@pytest.mark.parametrize('item_names, section_name, expected_result', SEARCH_PACKS_INPUT)
def test_search_packs_by_items_names_or_ids(item_names, section_name, expected_result, id_set):
    found_packs = PackDependencies._search_packs_by_items_names_or_ids(item_names, id_set[section_name])
    assert IsEqualFunctions.is_sets_equal(found_packs, expected_result)


class TestDependencyGraph:
    def test_build_dependency_graph(self, id_set):
        pack_name = "ImpossibleTraveler"
        found_graph = PackDependencies.build_dependency_graph(pack_id=pack_name,
                                                              id_set=id_set,
                                                              verbose_file=VerboseFile(),
                                                              )
        root_of_graph = [n for n in found_graph.nodes if found_graph.in_degree(n) == 0][0]
        pack_dependencies = [n for n in found_graph.nodes if found_graph.in_degree(n) > 0]

        assert root_of_graph == pack_name
        assert len(pack_dependencies) > 0

    def test_build_dependency_graph_include_ignored_content(self, id_set):
        """
        Given
            - A pack name which depends on unsupported content.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the pack dependencies with unsupported content.
        """

        pack_name = "ImpossibleTraveler"
        found_graph = PackDependencies.build_dependency_graph(pack_id=pack_name,
                                                              id_set=id_set,
                                                              verbose_file=VerboseFile(),
                                                              exclude_ignored_dependencies=False
                                                              )
        root_of_graph = [n for n in found_graph.nodes if found_graph.in_degree(n) == 0][0]
        pack_dependencies = [n for n in found_graph.nodes if found_graph.in_degree(n) > 0]

        assert root_of_graph == pack_name
        assert len(pack_dependencies) > 0
        assert 'NonSupported' not in pack_dependencies
