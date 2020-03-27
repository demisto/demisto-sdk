import pytest
import json
import os
from demisto_sdk.commands.find_dependencies.find_dependencies import PackDependencies


@pytest.fixture(scope="module")
def id_set():
    id_set_path = os.path.join('test_data', 'id_set.json')

    with open(id_set_path, 'r') as id_set_file:
        id_set = json.load(id_set_file)
        yield id_set


class TestIdSetFilters:
    @pytest.mark.parametrize("item_section", ["scripts", "playbooks"])
    def test_search_for_pack_item_with_no_result(self, item_section, id_set):
        pack_id = "Non Existing Pack Name"
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
                    "pack": "Expanse"
                }
            }
        ]

        assert found_filtered_result == expected_result
