import json
import os
import yaml

import networkx as nx
import pytest
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
import demisto_sdk.commands.create_id_set.create_id_set as cis
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions


@pytest.fixture()
def id_set(repo):
    # id_set_path = os.path.normpath(
    #     os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files', 'id_set', 'id_set.json'))
    #
    # with open(id_set_path, 'r') as id_set_file:
    #     id_set = json.load(id_set_file)
    #     yield id_set
    repo.setup_content_repo(20)

    prisma_cloud_compute = repo.create_pack('PrismaCloudCompute')
    with open('test_content/PrismaCloudComputeParseAuditAlert.yml') as yml_file:
        yml = yaml.load(yml_file, Loader=yaml.FullLoader)
        prisma_cloud_compute.create_script("PrismaCloudComputeParseAuditAlert", yml)
    with open('test_content/PrismaCloudComputeParseCloudDiscoveryAlert.yml') as yml_file:
        yml = yaml.load(yml_file, Loader=yaml.FullLoader)
        prisma_cloud_compute.create_script("PrismaCloudComputeParseCloudDiscoveryAlert", yml)
    with open('test_content/PrismaCloudComputeParseComplianceAlert.yml') as yml_file:
        yml = yaml.load(yml_file, Loader=yaml.FullLoader)
        prisma_cloud_compute.create_script("PrismaCloudComputeParseComplianceAlert", yml)
    with open('test_content/PrismaCloudComputeParseVulnerabilityAlert.yml') as yml_file:
        yml = yaml.load(yml_file, Loader=yaml.FullLoader)
        prisma_cloud_compute.create_script("PrismaCloudComputeParseVulnerabilityAlert", yml)

    # script2 = prisma_cloud_compute.create_script("PrismaCloudComputeParseCloudDiscoveryAlert")
    # script2.create_default_script()

    # script3 = prisma_cloud_compute.create_script("PrismaCloudComputeParseComplianceAlert")
    # script4 = prisma_cloud_compute.create_script("PrismaCloudComputeParseVulnerabilityAlert")

    # repo.packs[0].layoutcontainers
    with ChangeCWD(repo.path):
        ids = cis.IDSetCreator()
        ids.create_id_set()
        return ids.id_set


def test_id_set(id_set):
    return id_set


class TestIdSetFilters:
    @pytest.mark.parametrize("item_section", ["scripts", "playbooks"])
    def test_search_for_pack_item_with_no_result(self, item_section, id_set):
        pack_id = "Non Existing Pack"
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set[item_section])

        assert len(found_filtered_result) == 0

    @pytest.mark.parametrize("pack_id", ["pack_0", "pack_1", "pack_2"])
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
        """
        Given
            - A script entry in the id_set depending on a script.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the script depends on.
            - Should recognize the pack.
        """
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
                                                                      verbose=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    @pytest.mark.parametrize("dependency_integration_command,expected_result",
                             [("sslbl-get-indicators", {("Feedsslabusech", True)}),
                              ("activemq-subscribe", {("ActiveMQ", True)}),
                              ("alienvault-get-indicators", {("FeedAlienVault", True)})
                              ])
    def test_collect_scripts_depends_on_integration(self, dependency_integration_command, expected_result, id_set):
        """
        Given
            - A script entry in the id_set depending on integration commands.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the script depends on.
            - Should recognize the pack.
        """
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
                                                                      verbose=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_depends_on_two_scripts(self, id_set):
        """
        Given
            - A script entry in the id_set depending on 2 scripts.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the script depends on.
            - Should recognize both packs.
        """
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
                                                                      verbose=False,
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
                                                                      verbose=False,
                                                                      exclude_ignored_dependencies=False
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_depends_on_two_integrations(self, id_set):
        """
        Given
            - A script entry in the id_set depending on 2 integrations.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the script depends on.
            - Should recognize both packs.
        """
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
                                                                      verbose=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_command_to_integration(self, id_set):
        """
        Given
            - A script entry in the id_set containing command_to_integration.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the pack that the script depends on.
            - Should recognize the pack.
        """
        expected_result = {('Active_Directory_Query', True)}

        test_input = [
            {
                "DummyScript": {
                    "name": "ADGetUser",
                    "file_path": "Packs/Active_Directory_Query/Scripts/script-ADGetUser.yml",
                    "depends_on": [
                    ],
                    "command_to_integration": {
                        "ad-search": "activedir"
                    },
                    "pack": "Active_Directory_Query"
                }
            }
        ]

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_script_executions(self, id_set):
        """
        Given
            - A script entry in the id_set containing a script_executions, e.g: demisto.executeCommand(<command>).

        When
            - Building dependency graph for pack.

        Then
            - Extracting the pack that the script depends on.
            - Should recognize the pack.
        """
        expected_result = {('Active_Directory_Query', True)}

        test_input = [
            {
                "DummyScript": {
                    "name": "ADIsUserMember",
                    "file_path": "Packs/DeprecatedContent/Scripts/script-ADIsUserMember.yml",
                    "deprecated": False,
                    "depends_on": [
                    ],
                    "script_executions": [
                        "ADGetUser",
                    ],
                    "pack": "Active_Directory_Query"
                }
            }
        ]

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_command_to_integrations_and_script_executions(self, id_set):
        """
        Given
            - A script entry in the id_set containing command_to_integrations with a reputation command
             and script_executions.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the script depends on.
            - Should recognize the mandatory pack and ignore the packs that implement the file command.
        """
        expected_result = {
            ('Active_Directory_Query', True)
        }

        test_input = [
            {
                "DummyScript": {
                    "name": "double_dependency",
                    "file_path": "Packs/DeprecatedContent/Scripts/script-ADIsUserMember.yml",
                    "deprecated": False,
                    "depends_on": [
                    ],
                    "command_to_integration": {
                        "file": "many integrations"
                    },
                    "script_executions": [
                        "ADGetUser",
                    ],
                    "pack": "Active_Directory_Query"
                }
            }
        ]

        found_result = PackDependencies._collect_scripts_dependencies(pack_scripts=test_input,
                                                                      id_set=id_set,
                                                                      verbose=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_scripts_depends_on_with_two_inputs(self, id_set):
        """
        Given
            - 2 scripts entries in the id_set depending on different integrations.

        When
            - Building dependency graph for the packs.

        Then
            - Extracting the packs that the scripts depends on.
            - Should recognize both packs.
        """
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
                                                                      verbose=False,
                                                                      )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    @pytest.mark.parametrize("generic_command", ['ip', 'domain', 'url', 'file', 'email', 'cve', 'cve-latest',
                                                 'cve-search', 'send-mail', 'send-notification'])
    def test_collect_detection_of_optional_dependencies(self, generic_command, id_set):
        """
        Given
            - Scripts that depends on generic commands

        When
            - Building dependency graph for the packs.

        Then
            - Extracting the packs that the scripts depends on.
            - Should NOT recognize packs.
        """
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
                                                                          verbose=False,
                                                                          )

        assert len(dependencies_set) == 0


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
                                                                        verbose=False,
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
                                                                        verbose=False,
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
                                                                        verbose=False,
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
                                                                            verbose=False,
                                                                            )

        assert len(found_result_set) == 1
        found_result = found_result_set.pop()
        assert found_result[0] == pack_name
        assert found_result[1]

    @pytest.mark.parametrize("integration_command", ["ip", "domain", "url", "cve"])
    def test_collect_detection_of_optional_dependencies_in_playbooks(self, integration_command, id_set):
        """
        Given
            - Playbooks that are using generic commands

        When
            - Building dependency graph for the packs.

        Then
            - Extracting the packs that the scripts depends on.
            - Should NOT recognize packs.
        """
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
                                                                            verbose=False,
                                                                            )

        assert len(found_result_set) == 0

    def test_collect_playbooks_dependencies_on_incident_fields(self, id_set):
        """
        Given
            - A playbook entry in the id_set.

        When
            - Collecting playbook dependencies.

        Then
            - The incident fields from the DigitalGuardian and EmployeeOffboarding packs
             should result in an optional dependency.
        """
        expected_result = {("DigitalGuardian", False), ("EmployeeOffboarding", False)}
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
                                                                        verbose=False,
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_playbooks_dependencies_on_incident_fields__phishing_pack(self, id_set):
        """
        Given
            - A playbook entry in the id_set which is using incident fields from the Phishing pack.

        When
            - Collecting playbook dependencies.

        Then
            - The incident fields from the Phishing pack should result in an optional dependency.
        """
        expected_result = {("Phishing", False)}
        test_input = [
            {
                "search_and_delete_emails_-_ews": {
                    "name": "Search And Delete Emails - EWS",
                    "file_path": "Packs/EWS/Playbooks/playbook-Search_And_Delete_Emails_-_EWS.yml",
                    "fromversion": "5.0.0",
                    "tests": [
                        "No test"
                    ],
                    "pack": "EWS",
                    "incident_fields": [
                        "attachmentname",
                        "emailfrom",
                        "emailsubject"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose=False,
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_playbooks_dependencies_on_incident_fields__commontypes_pack(self, id_set):
        """
        Given
            - A playbook entry in the id_set which is using incident fields from the CommonTYpes pack.

        When
            - Collecting playbook dependencies.

        Then
            - The incident fields from the Phishing pack should result in an mandatory dependency.
        """
        expected_result = {("CommonTypes", True)}
        test_input = [
            {
                "search_and_delete_emails_-_ews": {
                    "name": "Search And Delete Emails - EWS",
                    "file_path": "Packs/EWS/Playbooks/playbook-Search_And_Delete_Emails_-_EWS.yml",
                    "fromversion": "5.0.0",
                    "tests": [
                        "No test"
                    ],
                    "pack": "EWS",
                    "incident_fields": [
                        "accountid"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose=False,
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_playbooks_dependencies_on_indicator_fields(self, id_set):
        """
        Given
            - A playbook entry in the id_set which is using Indicator fields from the CommonTypes pack.

        When
            - Collecting playbook dependencies.

        Then
            - The indicator field accounttype should result in a mandatory dependency to the CommonTypes pack.
        """
        expected_result = {('CommonScripts', True), ('SafeBreach', True), ('CommonTypes', True)}
        test_input = [
            {
                "SafeBreach - Compare and Validate Insight Indicators": {
                    "name": "SafeBreach - Compare and Validate Insight Indicators",
                    "file_path": "Packs/SafeBreach/Playbooks/SafeBreach_Compare_and_Validate_Insight_Indicators.yml",
                    "fromversion": "5.5.0",
                    "implementing_scripts": [
                        "ChangeContext",
                        "Set",
                        "SetAndHandleEmpty"
                    ],
                    "command_to_integration": {
                        "safebreach-get-remediation-data": ""
                    },
                    "tests": [
                        "No tests (auto formatted)"
                    ],
                    "pack": "SafeBreach",
                    "indicator_fields": [
                        "accounttype",
                        "safebreachremediationstatus"
                    ]
                }
            },
        ]

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose=False,
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
                                                                        verbose=False,
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
                                                                      verbose=False,
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
                                                                      verbose=False,
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
            verbose=False,
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
            # script dependencies
            ("CommonScripts", False), ("Carbon_Black_Enterprise_Response", False)
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
            verbose=False,
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
            verbose=False,
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
            verbose=False,

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
            - Extracting the packs that the classifier depends on as optional dependencies.
        """
        expected_result = {("Claroty", False), ("PAN-OS", False), ("Logzio", False)}

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
            verbose=False,
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_classifier_dependencies__commontypes_pack(self, id_set):
        """
        Given
            - A classifier entry in the id_set with an incident type from the CommonTypes pack.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the classifier depends on a mandatory dependencies.
        """
        expected_result = {("CommonTypes", True)}

        test_input = [
            {
                "Dummy Classifier": {
                    "name": "Dummy Classifier",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "incident_types": [
                        "Network"
                    ],
                }
            }
        ]

        found_result = PackDependencies._collect_classifiers_dependencies(
            pack_classifiers=test_input,
            id_set=id_set,
            verbose=False,
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
            - Extracting the packs that the mapper depends on as optional dependencies.
        """
        expected_result = {("AccessInvestigation", False), ("CommonTypes", True), ("PrismaCloud", False),
                           ("BruteForce", False)}

        test_input = [
            {
                "Dummy Mapper": {
                    "name": "Dummy Mapper",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "incident_types": [
                        "Access",
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
            verbose=False,
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_mapper_dependencies__commontypes_pack(self, id_set):
        """
        Given
            - A mapper entry in the id_set with an incident type from the CommonTypes pack.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the mapper depends on a mandatory dependencies.
        """
        expected_result = {("CommonTypes", True)}

        test_input = [
            {
                "Dummy Mapper": {
                    "name": "Dummy Mapper",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "incident_types": [
                        "Authentication"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_mappers_dependencies(
            pack_mappers=test_input,
            id_set=id_set,
            verbose=False,
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnWidgets:
    def test_collect_widgets_dependencies(self, id_set):
        """
        Given
            - A mapper entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the mapper depends on.
        """
        expected_result = {('CommonScripts', True)}

        test_input = [
            {
                "Dummy_widget": {
                    "name": "Dummy Widget",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "scripts": [
                        "AssignAnalystToIncident"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_widget_dependencies(
            pack_widgets=test_input,
            id_set=id_set,
            verbose=False,
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnDashboard:
    def test_collect_dashboard_dependencies(self, id_set):
        """
        Given
            - A dashboard entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the dashboard depends on.
        """
        expected_result = {('CommonScripts', True)}

        test_input = [
            {
                "Dummy_dashboard": {
                    "name": "Dummy Widget",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "scripts": [
                        "AssignAnalystToIncident"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_widget_dependencies(
            pack_widgets=test_input,
            id_set=id_set,
            verbose=False,
            header='Dashboards',
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnReports:
    def test_collect_report_dependencies(self, id_set):
        """
        Given
            - A report entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the report depends on.
        """
        expected_result = {('CommonScripts', True)}

        test_input = [
            {
                "Dummy_report": {
                    "name": "Dummy Widget",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "scripts": [
                        "AssignAnalystToIncident"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_widget_dependencies(
            pack_widgets=test_input,
            id_set=id_set,
            verbose=False,
            header='Reports',
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


def test_find_dependencies_using_pack_metadata(mocker):
    """
        Given
            - A dict of dependencies from id set.
        When
            - Running PackDependencies.update_dependencies_from_pack_metadata.
        Then
            - Assert the dependencies in the given dict is updated.
    """
    mock_pack_meta_file = {
        "dependencies": {
            "dependency_pack1": {
                "mandatory": False,
                "display_name": "dependency pack 1"
            },
            "dependency_pack2": {
                "mandatory": False,
                "display_name": "dependency pack 2"
            },
            "dependency_pack3": {
                "mandatory": False,
                "display_name": "dependency pack 3"
            }
        }
    }

    dependencies_from_id_set = {
        "dependency_pack1": {
            "mandatory": False,
            "display_name": "dependency pack 1"
        },
        "dependency_pack2": {
            "mandatory": True,
            "display_name": "dependency pack 2"
        },
        "dependency_pack3": {
            "mandatory": True,
            "display_name": "dependency pack 3"
        },
        "dependency_pack4": {
            "mandatory": True,
            "display_name": "dependency pack 4"
        }
    }

    mocker.patch('demisto_sdk.commands.find_dependencies.find_dependencies.PackDependencies.get_metadata_from_pack',
                 return_value=mock_pack_meta_file)

    first_level_dependencies = PackDependencies.update_dependencies_from_pack_metadata('', dependencies_from_id_set)

    assert not first_level_dependencies.get("dependency_pack2", {}).get("mandatory")
    assert not first_level_dependencies.get("dependency_pack3", {}).get("mandatory")
    assert first_level_dependencies.get("dependency_pack4", {}).get("mandatory")


class TestDependencyGraph:
    @pytest.mark.parametrize('source_node, expected_nodes_in, expected_nodes_out',
                             [('pack1', ['pack1', 'pack2', 'pack3'], ['pack4']),
                              ('pack2', ['pack2', 'pack3'], ['pack4', 'pack1'])]
                             )
    def test_get_dependencies_subgraph_by_dfs(self, source_node, expected_nodes_in, expected_nodes_out):
        """
        Given
            - A directional graph and a source node.
        When
            - Extracting it's DFS subgraph.
        Then
            - Assert all nodes that are reachable from the source are in the subgraph
            - Assert all nodes that are not reachable from the source are not in the subgraph
        """
        graph = nx.DiGraph()
        graph.add_node('pack1')
        graph.add_node('pack2')
        graph.add_node('pack3')
        graph.add_node('pack4')
        graph.add_edge('pack1', 'pack2')
        graph.add_edge('pack2', 'pack3')
        dfs_graph = PackDependencies.get_dependencies_subgraph_by_dfs(graph, source_node)
        for i in expected_nodes_in:
            assert i in dfs_graph.nodes()
        for i in expected_nodes_out:
            assert i not in dfs_graph.nodes()

    def test_build_all_dependencies_graph(self, id_set, mocker):
        """
        Given
            - A list of packs and their dependencies
        When
            - Creating the dependencies graph using build_all_dependencies_graph method
        Then
            - Assert all the dependencies are correct
            - Assert all the mandatory dependencies are correct
        """

        def mock_find_pack_dependencies(pack_id, *_, **__):
            dependencies = {'pack1': [('pack2', True), ('pack3', False)],
                            'pack2': [('pack3', False), ('pack2', True)],
                            'pack3': [],
                            'pack4': [('pack6', False)]}
            return dependencies[pack_id]

        mocker.patch(
            'demisto_sdk.commands.find_dependencies.find_dependencies.PackDependencies._find_pack_dependencies',
            side_effect=mock_find_pack_dependencies
        )
        pack_ids = ['pack1', 'pack2', 'pack3', 'pack4']
        dependency_graph = PackDependencies.build_all_dependencies_graph(pack_ids, {}, False)

        # Asserting Dependencies (mandatory and non-mandatory)
        assert [n for n in dependency_graph.neighbors('pack1')] == ['pack2', 'pack3']
        assert [n for n in dependency_graph.neighbors('pack2')] == ['pack3']
        assert [n for n in dependency_graph.neighbors('pack3')] == []
        assert [n for n in dependency_graph.neighbors('pack4')] == ['pack6']

        # Asserting mandatory dependencies
        nodes = dependency_graph.nodes(data=True)
        assert nodes['pack1']['mandatory_for_packs'] == []
        assert nodes['pack2']['mandatory_for_packs'] == ['pack1']
        assert nodes['pack3']['mandatory_for_packs'] == []
        assert nodes['pack4']['mandatory_for_packs'] == []

    def test_build_dependency_graph(self, id_set):
        pack_name = "ImpossibleTraveler"
        found_graph = PackDependencies.build_dependency_graph(pack_id=pack_name,
                                                              id_set=id_set,
                                                              verbose=False,
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
                                                              verbose=False,
                                                              exclude_ignored_dependencies=False
                                                              )
        root_of_graph = [n for n in found_graph.nodes if found_graph.in_degree(n) == 0][0]
        pack_dependencies = [n for n in found_graph.nodes if found_graph.in_degree(n) > 0]

        assert root_of_graph == pack_name
        assert len(pack_dependencies) > 0
        assert 'NonSupported' not in pack_dependencies
