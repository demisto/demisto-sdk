import json
import os
from pathlib import Path
from typing import List

import demisto_sdk.commands.create_id_set.create_id_set as cis
import networkx as nx
import pytest
from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions


def create_a_pack_entity(pack, entity_type: FileType = None, entity_id: str = None, entity_name: str = None,
                         commands: List[str] = None):
    """
    Given
        - A Pack.

    When
        - add an entity to the pack.

    Then
        - Adds the entity to the pack with basic data.
    """
    if entity_type == FileType.SCRIPT:
        pack.create_script(entity_id).create_default_script(entity_id)
    elif entity_type == FileType.INTEGRATION:
        pack.create_integration(entity_id).create_default_integration(entity_id, commands)
    elif entity_type == FileType.PLAYBOOK:
        pack.create_playbook(entity_id).create_default_playbook(entity_id)
    elif entity_type == FileType.TEST_PLAYBOOK:
        pack.create_test_playbook(entity_id).create_default_test_playbook(entity_id)
    elif entity_type == FileType.CLASSIFIER:
        content = {'id': entity_id, 'name': entity_name, 'transformer': '', 'keyTypeMap': {}, 'type': 'classification'}
        pack.create_classifier(entity_id, content)
    elif entity_type == FileType.LAYOUT:
        content = {"typeId": entity_id, "TypeName": entity_id, "kind": "details", "layout": {}}
        pack.create_layout(entity_id, content)
    elif entity_type == FileType.LAYOUTS_CONTAINER:
        content = {"id": entity_id, "name": entity_name, "group": "incident", "detailsV2": {}}
        pack.create_layout(entity_id, content)
    elif entity_type == FileType.MAPPER:
        content = {'id': entity_id, 'name': entity_name, 'mapping': {}, 'type': 'mapping-incomming'}
        pack.create_mapper(entity_id, content)
    elif entity_type == FileType.INCIDENT_FIELD:
        content = {'id': f'incident_{entity_id}', 'name': entity_name}
        pack.create_incident_field(entity_id, content)
    elif entity_type == FileType.INCIDENT_TYPE:
        content = {'id': entity_id, 'name': entity_name, 'preProcessingScript': '', 'color': 'test'}
        pack.create_incident_type(entity_id, content)
    elif entity_type == FileType.INDICATOR_FIELD:
        content = {'id': f'indicator_{entity_id}', 'name': entity_name}
        pack.create_indicator_field(entity_id, content)
    elif entity_type == FileType.REPUTATION:
        content = {'id': entity_id, 'details': entity_name, 'regex': ''}
        pack.create_indicator_type(entity_id, content)
    elif entity_type == FileType.GENERIC_DEFINITION:
        content = {'id': entity_id, 'details': entity_name, "auditable": True}
        pack.create_generic_definition(entity_id, content)
    elif entity_type == FileType.GENERIC_TYPE:
        content = {'id': entity_id, 'details': entity_name, "color": "#8052f4", "definitionId": "assets"}
        pack.create_generic_type(entity_id, content)
    elif entity_type == FileType.GENERIC_MODULE:
        content = {'id': entity_id, 'details': entity_name, "views": [], "definitionId": "assets"}
        pack.create_generic_module(entity_id, content)
    elif entity_type == FileType.GENERIC_FIELD:
        content = {'id': entity_id, 'details': entity_name, "definitionId": "assets"}
        pack.create_generic_field(entity_id, content)


@pytest.fixture(scope="module")
def id_set():
    with open("Content/Tests/id_set.json", 'r') as id_set_file:
        id_set = json.load(id_set_file)
        yield id_set


def create_content_repo():
    os.makedirs('Content')
    repo = Repo(Path('Content'))

    # Create 5 packs with all entities
    repo.setup_content_repo(5)

    # Create a pack called 'PrismaCloudCompute' with 4 scripts and 1 incident_type.
    prisma_cloud_compute = repo.create_pack('PrismaCloudCompute')
    prisma_cloud_compute_scripts = ['PrismaCloudComputeParseAuditAlert',
                                    'PrismaCloudComputeParseCloudDiscoveryAlert',
                                    'PrismaCloudComputeParseComplianceAlert',
                                    'PrismaCloudComputeParseVulnerabilityAlert']
    for script in prisma_cloud_compute_scripts:
        create_a_pack_entity(prisma_cloud_compute, FileType.SCRIPT, script)
    create_a_pack_entity(prisma_cloud_compute, FileType.INCIDENT_TYPE, 'Prisma Cloud Compute Cloud Discovery',
                         'Prisma Cloud Compute Cloud Discovery')

    # Create a pack called 'Expanse' with 1 playbook.
    expanse = repo.create_pack('Expanse')
    create_a_pack_entity(expanse, FileType.PLAYBOOK, 'Expanse_Incident_Playbook')

    # Create a pack called 'GetServerURL' with 1 script.
    get_server_url = repo.create_pack('GetServerURL')
    create_a_pack_entity(get_server_url, FileType.SCRIPT, 'GetServerURL')

    # Create a pack called 'HelloWorld' with 1 script and 1 classifier.
    hello_world = repo.create_pack('HelloWorld')
    create_a_pack_entity(hello_world, FileType.SCRIPT, 'HelloWorldScript')
    create_a_pack_entity(hello_world, FileType.CLASSIFIER, 'HelloWorld', 'HelloWorld')

    # Create a pack called 'Feedsslabusech' with 1 integration.
    feedsslabusech = repo.create_pack('Feedsslabusech')
    create_a_pack_entity(feedsslabusech, FileType.INTEGRATION, 'Feedsslabusech', commands=['sslbl-get-indicators'])

    # Create a pack called 'ActiveMQ' with 1 integration.
    active_mq = repo.create_pack('ActiveMQ')
    create_a_pack_entity(active_mq, FileType.INTEGRATION, 'ActiveMQ', commands=['activemq-subscribe'])

    # Create a pack called 'FeedAlienVault' with 1 integration.
    feed_alien_vault = repo.create_pack('FeedAlienVault')
    create_a_pack_entity(feed_alien_vault, FileType.INTEGRATION, 'FeedAlienVault',
                         commands=['alienvault-get-indicators'])

    # Create a pack called 'QRadar' with 1 integration.
    qradar = repo.create_pack('QRadar')
    create_a_pack_entity(qradar, FileType.INTEGRATION, 'QRadar', commands=['qradar-searches'])

    # Create a pack called 'Active_Directory_Query' with 1 integration and 1 script.
    active_directory_query = repo.create_pack('Active_Directory_Query')
    create_a_pack_entity(active_directory_query, FileType.INTEGRATION, 'Active Directory Query',
                         commands=['ad-get-user', 'ad-search'])
    create_a_pack_entity(active_directory_query, FileType.SCRIPT, 'ADGetUser')

    # Create a pack called 'Pcysys' with 1 playbook.
    pcysys = repo.create_pack('Pcysys')
    create_a_pack_entity(pcysys, FileType.PLAYBOOK, 'Pentera Run Scan')

    # Create a pack called 'Indeni' with 1 playbook.
    indeni = repo.create_pack('Indeni')
    create_a_pack_entity(indeni, FileType.PLAYBOOK, 'Indeni Demo')

    # Create a pack called 'Pcysys' with 1 playbook.
    slack = repo.create_pack('Slack')
    create_a_pack_entity(slack, FileType.PLAYBOOK, 'Failed Login Playbook - Slack v2')

    # Create a pack called 'FeedAWS' with 1 integration.
    feed_aws = repo.create_pack('FeedAWS')
    create_a_pack_entity(feed_aws, FileType.INTEGRATION, 'FeedAWS', commands=['aws-get-indicators'])

    # Create a pack called 'FeedAutoFocus' with 1 integration.
    feed_autofocus = repo.create_pack('FeedAutofocus')
    create_a_pack_entity(feed_autofocus, FileType.INTEGRATION, 'FeedAutofocus', commands=['autofocus-get-indicators'])

    # Create a pack called 'ipinfo' with 1 integration.
    ipinfo = repo.create_pack('ipinfo')
    create_a_pack_entity(ipinfo, FileType.INTEGRATION, 'ipinfo', commands=['ip'])

    # Create a pack called 'DigitalGuardian' with 1 incident_field.
    digital_guardian = repo.create_pack('DigitalGuardian')
    create_a_pack_entity(digital_guardian, FileType.INCIDENT_FIELD, 'digitalguardianusername',
                         'Digital Guardian Username')

    # Create a pack called 'EmployeeOffboarding' with 1 incident_field.
    employee_offboarding = repo.create_pack('EmployeeOffboarding')
    create_a_pack_entity(employee_offboarding, FileType.INCIDENT_FIELD, 'googledisplayname', 'Google Display Name')

    # Create a pack called 'Phishing' with 3 incident_fields and 1 script.
    phishing = repo.create_pack('Phishing')
    create_a_pack_entity(phishing, FileType.INCIDENT_FIELD, 'attachmentname', 'Attachment Name')
    create_a_pack_entity(phishing, FileType.INCIDENT_FIELD, 'emailfrom', 'Email From')
    create_a_pack_entity(phishing, FileType.INCIDENT_FIELD, 'emailsubject', 'Email Subject')
    create_a_pack_entity(phishing, FileType.SCRIPT, 'CheckEmailAuthenticity')

    # Create a pack called 'CommonTypes' with 3 incident_fields 2 incident_types 5 indicator_fields 1 indicator_type.
    common_types = repo.create_pack('CommonTypes')
    ct_incident_field_ids = ['accountid', 'country', 'username']
    ct_incident_field_names = ['Account Id', 'Country', 'Username']
    ct_incident_type_ids = ['Network', 'Authentication']
    ct_incident_type_names = ['Network', 'Authentication']
    ct_indicator_field_ids = ['accounttype', 'adminname', 'tags', 'commontypes', 'adminemail']
    ct_indicator_field_names = ['Account Type', 'Admin Name', 'Tags', 'Common Types', 'Admin Email']
    for field_id, field_name in zip(ct_incident_field_ids, ct_incident_field_names):
        create_a_pack_entity(common_types, FileType.INCIDENT_FIELD, field_id, field_name)
    for field_id, field_name in zip(ct_incident_type_ids, ct_incident_type_names):
        create_a_pack_entity(common_types, FileType.INCIDENT_TYPE, field_id, field_name)
    for field_id, field_name in zip(ct_indicator_field_ids, ct_indicator_field_names):
        create_a_pack_entity(common_types, FileType.INDICATOR_FIELD, field_id, field_name)
    create_a_pack_entity(common_types, FileType.REPUTATION, 'accountrep', 'Account Rep')

    # Create a pack called 'SafeBreach' with 1 incident_field and 1 integration.
    safe_breach = repo.create_pack('SafeBreach')
    create_a_pack_entity(safe_breach, FileType.INDICATOR_FIELD, 'safebreachremediationstatus',
                         'SafeBreach Remediation Status')
    create_a_pack_entity(safe_breach, FileType.INTEGRATION, 'SafeBreach', commands=['safebreach-get-remediation-data'])

    # Create a pack called 'CommonScripts' with 7 scripts.
    common_scripts = repo.create_pack('CommonScripts')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'ChangeContext')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'Set')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'SetAndHandleEmpty')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'AssignAnalystToIncident')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'EmailAskUser')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'ScheduleCommand')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'DeleteContext')
    create_a_pack_entity(common_scripts, FileType.SCRIPT, 'IsInCidrRanges')

    # Create a pack called 'CalculateTimeDifference' with 1 script.
    calculate_time_difference = repo.create_pack('CalculateTimeDifference')
    create_a_pack_entity(calculate_time_difference, FileType.SCRIPT, 'CalculateTimeDifference')

    # Create a pack called 'CommonPlaybooks' with 3 playbooks.
    common_playbooks = repo.create_pack('CommonPlaybooks')
    create_a_pack_entity(common_playbooks, FileType.PLAYBOOK, 'Block IP - Generic v2')
    create_a_pack_entity(common_playbooks, FileType.PLAYBOOK, 'IP Enrichment - Generic v2')
    create_a_pack_entity(common_playbooks, FileType.PLAYBOOK, 'Active Directory - Get User Manager Details')

    # Create a pack called 'FeedMitreAttack' with 1 indicator_type.
    feed_mitre_attack = repo.create_pack('FeedMitreAttack')
    create_a_pack_entity(feed_mitre_attack, FileType.REPUTATION, 'MITRE ATT&CK', 'MITRE ATT&CK')

    # Create a pack called 'CrisisManagement' with 1 incident_type and 1 incident_field.
    crisis_management = repo.create_pack('CrisisManagement')
    create_a_pack_entity(crisis_management, FileType.INCIDENT_TYPE, 'HR Ticket', 'HR Ticket')
    create_a_pack_entity(crisis_management, FileType.INDICATOR_FIELD, 'jobtitle', 'Job Title')

    # Create a pack called 'Carbon_Black_Enterprise_Response' with 2 scripts.
    carbon_black_enterprise_response = repo.create_pack('Carbon_Black_Enterprise_Response')
    create_a_pack_entity(carbon_black_enterprise_response, FileType.SCRIPT, 'CBLiveFetchFiles')
    create_a_pack_entity(carbon_black_enterprise_response, FileType.SCRIPT, 'CBAlerts')

    # Create a pack called 'Claroty' with 3 mappers and 1 incident_type.
    claroty = repo.create_pack('Claroty')
    create_a_pack_entity(claroty, FileType.MAPPER, 'CBAlerts-mapper', 'Claroty-mapper')
    create_a_pack_entity(claroty, FileType.MAPPER, 'Claroty', 'Claroty')
    create_a_pack_entity(claroty, FileType.MAPPER, 'CBAlerts - Incoming Mapper', 'Claroty - Incoming Mapper')
    create_a_pack_entity(claroty, FileType.INCIDENT_TYPE, 'Claroty Integrity Incident', 'Claroty Integrity Incident')

    # Create a pack called 'EWS' with 1 mapper.
    ews = repo.create_pack('EWS')
    create_a_pack_entity(ews, FileType.MAPPER, 'EWS v2-mapper', 'EWS v2-mapper')

    # Create a pack called 'AutoFocus' with 1 playbook.
    auto_focus = repo.create_pack('AutoFocus')
    create_a_pack_entity(auto_focus, FileType.PLAYBOOK, 'Autofocus Query Samples, Sessions and Tags',
                         'Autofocus Query Samples, Sessions and Tags')

    # Create a pack called 'Volatility' with 1 script.
    volatility = repo.create_pack('Volatility')
    create_a_pack_entity(volatility, FileType.SCRIPT, 'AnalyzeMemImage')

    # Create a pack called 'PAN-OS' with 1 incident_type.
    pan_os = repo.create_pack('PAN-OS')
    create_a_pack_entity(pan_os, FileType.INCIDENT_TYPE, 'FirewallUpgrade', 'FirewallUpgrade')

    # Create a pack called 'Logzio' with 1 incident_type.
    logzio = repo.create_pack('Logzio')
    create_a_pack_entity(logzio, FileType.INCIDENT_TYPE, 'Logz.io Alert', 'Logz.io Alert')

    # Create a pack called 'AccessInvestigation' with 1 incident_type.
    access_investigation = repo.create_pack('AccessInvestigation')
    create_a_pack_entity(access_investigation, FileType.INCIDENT_TYPE, 'Access', 'Access')

    # Create a pack called 'PrismaCloud' with 1 incident_type.
    prisma_cloud = repo.create_pack('PrismaCloud')
    create_a_pack_entity(prisma_cloud, FileType.INCIDENT_TYPE, 'AWS CloudTrail Misconfiguration',
                         'AWS CloudTrail Misconfiguration')

    # Create a pack called 'BruteForce' with 1 incident_field.
    brute_force = repo.create_pack('BruteForce')
    create_a_pack_entity(brute_force, FileType.INCIDENT_FIELD, 'accountgroups', 'Account Groups')

    # Create a pack called 'Compliance' with 1 incident_field.
    complience = repo.create_pack('Compliance')
    create_a_pack_entity(complience, FileType.INCIDENT_FIELD, 'emailaddress', 'E-mail Address')

    # Create a pack called 'CortexXDR' with 1 classifier.
    cortex_xdr = repo.create_pack('CortexXDR')
    create_a_pack_entity(cortex_xdr, FileType.CLASSIFIER, 'Cortex XDR - IR', 'Cortex XDR - IR')

    # Create a pack called 'ImpossibleTraveler' with:
    # 1 integration 1 playbook 1 test_playbook 1 layout 7 incident_fields 1 incident type
    impossible_traveler = repo.create_pack('ImpossibleTraveler')
    create_a_pack_entity(impossible_traveler, FileType.SCRIPT, 'CalculateGeoDistance')
    create_a_pack_entity(impossible_traveler, FileType.PLAYBOOK, 'Impossible Traveler')
    create_a_pack_entity(impossible_traveler, FileType.TEST_PLAYBOOK, 'Impossible Traveler - Test')
    create_a_pack_entity(impossible_traveler, FileType.LAYOUT, 'Impossible Traveler')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_FIELD, 'coordinates' 'Coordinates')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_FIELD, 'previouscoordinates' 'Previous Coordinates')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_FIELD, 'previouscountry' 'Previou Country')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_FIELD,
                         'previoussignindatetime' 'Previous Sign In Date Time')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_FIELD, 'previoussourceiP' 'Previous Source IP')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_FIELD, 'signindatetime' 'Sign In Date Time')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_FIELD, 'travelmaplink' 'Travel Map Link')
    create_a_pack_entity(impossible_traveler, FileType.INCIDENT_TYPE, 'impossibletraveler' 'Impossible Traveler')

    # Create a pack called 'pack_with_definition' with 1 generic definition.
    definition_pack = repo.create_pack('pack_with_definition')
    create_a_pack_entity(definition_pack, FileType.GENERIC_DEFINITION, 'assets', 'assets')

    # Create a pack called 'pack_with_module' with 1 generic module.
    pack_with_module = repo.create_pack('pack_with_module')
    create_a_pack_entity(pack_with_module, FileType.GENERIC_MODULE, 'module_id', 'module_id')

    # Create a pack called 'pack_with_generic_field' with 1 generic field.
    pack_with_generic_field = repo.create_pack('pack_with_generic_field')
    create_a_pack_entity(pack_with_generic_field, FileType.GENERIC_FIELD, 'generic_field_id', 'generic_field_id')

    # Create a pack called 'pack_with_generic_type' with 1 generic type.
    pack_with_generic_type = repo.create_pack('pack_with_generic_type')
    create_a_pack_entity(pack_with_generic_type, FileType.GENERIC_TYPE, 'generic_type_id', 'generic_type_id')

    incident_layout = {
        "detailsV2": {
            "tabs": [
                {
                    "id": "caseinfoid",
                    "name": "Incident Info",
                    "sections": [
                        {
                            "items": [
                                {
                                    "endCol": 2,
                                    "fieldId": "incident_example",
                                    "height": 22,
                                    "id": "example",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0
                                }
                            ]
                        }
                    ],
                    "type": "custom"
                },
            ]
        },
        "group": "incident",
        "id": "example",
        "name": "example",
        "system": "false",
        "version": -1,
        "fromVersion": "6.0.0",
        "description": ""
    }
    indicator_layout = {
        "group": "indicator",
        "id": "example",
        "indicatorsDetails": {
            "tabs": [
                {
                    "sections": [
                        {
                            "items": [
                                {
                                    "endCol": 2,
                                    "fieldId": "indicator_example",
                                    "height": 22,
                                    "id": "example",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0
                                }
                            ]
                        }
                    ],
                    "type": "custom"
                }
            ]
        },
        "name": "example",
        "system": "false",
        "version": -1,
        "fromVersion": "6.0.0",
    }
    generic_layout = {
        "detailsV2": {
            "tabs": [
                {
                    "id": "caseinfoid",
                    "name": "Incident Info",
                    "sections": [
                        {
                            "items": [
                                {
                                    "endCol": 2,
                                    "fieldId": "incident_example",
                                    "height": 22,
                                    "id": "example",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0
                                }
                            ]
                        }
                    ],
                    "type": "custom"
                },
            ]
        },
        "group": "generic",
        "id": "generic_layout_id",
        "name": "generic_layout_id",
        "system": "false",
        "version": -1,
        "fromVersion": "6.0.0",
        "description": "",
        "definitionId": "assets"
    }

    pack1 = repo.create_pack('pack1')
    create_a_pack_entity(pack1, FileType.INCIDENT_FIELD, 'example', 'example')
    pack2 = repo.create_pack('pack2')
    create_a_pack_entity(pack2, FileType.INDICATOR_FIELD, 'example', 'example')
    pack3 = repo.create_pack('pack3')
    pack3.create_layoutcontainer('example', incident_layout)
    pack4 = repo.create_pack('pack4')
    pack4.create_layoutcontainer('example', indicator_layout)
    pack5 = repo.create_pack('pack5')
    pack5.create_layout(pack5, generic_layout)

    with ChangeCWD(repo.path):
        ids = cis.IDSetCreator()
        ids.create_id_set()


def setup_module():
    create_content_repo()


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
                    "fromversion": '5.0.0',
                    "docker_image": "demisto/python3:3.8.3.8715",
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseCloudDiscoveryAlert": {
                    "name": "PrismaCloudComputeParseCloudDiscoveryAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseCloudDiscoveryAlert/PrismaCloudComputeParseCloudDiscoveryAlert.yml",
                    "fromversion": '5.0.0',
                    "docker_image": "demisto/python3:3.8.3.8715",
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseComplianceAlert": {
                    "name": "PrismaCloudComputeParseComplianceAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseComplianceAlert/PrismaCloudComputeParseComplianceAlert.yml",
                    "fromversion": '5.0.0',
                    "docker_image": "demisto/python3:3.8.3.8715",
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseVulnerabilityAlert": {
                    "name": "PrismaCloudComputeParseVulnerabilityAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseVulnerabilityAlert/PrismaCloudComputeParseVulnerabilityAlert.yml",
                    "fromversion": '5.0.0',
                    "docker_image": "demisto/python3:3.8.3.8715",
                    "pack": "PrismaCloudCompute"
                }
            }
        ]

        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['scripts'])

        assert IsEqualFunctions.is_lists_equal(found_filtered_result, expected_result)

    @pytest.mark.parametrize("pack_id", ["pack_0", "pack_1", "pack_2"])
    def test_search_for_pack_playbook_item(self, pack_id, id_set):
        found_filtered_result = PackDependencies._search_for_pack_items(pack_id, id_set['playbooks'])

        assert len(found_filtered_result) > 0

    def test_search_for_specific_pack_playbook_item(self, id_set):
        pack_id = "Expanse"

        expected_result = [
            {
                "Expanse_Incident_Playbook": {
                    "name": "Expanse_Incident_Playbook",
                    "file_path": "Packs/Expanse/Playbooks/Expanse_Incident_Playbook.yml",
                    "fromversion": "5.0.0",
                    "implementing_scripts": [
                        'DeleteContext'
                    ],
                    "tests": [
                        "No tests"
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
                    "docker_image": "demisto/python3:3.8.3.8715",
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

    def test_collect_playbooks_dependencies_on_filter(self, id_set):
        """
        Given
            - A playbook entry in the id_set with filter from the CommonScripts pack.
            -

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the playbook depends on.
        """
        expected_result = {("CommonScripts", True)}

        test_input = [
            {
                'Dummy Playbook': {
                    'name': 'Dummy Playbook',
                    'file_path': 'dummy_path',
                    'fromversion': 'dummy_version',
                    "filters": ["IsInCidrRanges"]
                }
            },
        ]

        found_result = PackDependencies._collect_playbooks_dependencies(pack_playbooks=test_input,
                                                                        id_set=id_set,
                                                                        verbose=False,
                                                                        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnLayout:
    @pytest.mark.parametrize('pack, expected_dependencies', [
        ('pack3', 'pack1'),  # pack3 has a layout of type incident that depends in an incident of pack1
        ('pack4', 'pack2')  # pack4 has a layout of type indicator that depends in an indicator of pack2
    ])
    def test_layouts_dependencies(self, pack, expected_dependencies):
        dependencies = PackDependencies.find_dependencies(pack, id_set_path="Content/Tests/id_set.json",
                                                          update_pack_metadata=False)
        assert list(dependencies.keys())[0] == expected_dependencies

    def test_collect_incident_layouts_dependencies(self, id_set):
        """
        Given
            - A layout entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the layout depends on.
        """
        expected_result = {("PrismaCloudCompute", True)}

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

    def test_collect_indicator_layouts_dependencies(self, id_set):
        """
        Given
            - A layout entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the layout depends on.
        """
        expected_result = {("FeedMitreAttack", True), ("CommonTypes", True), ("CrisisManagement", True)}

        test_input = [
            {
                "Dummy Layout": {
                    "typeID": "dummy_layout",
                    "name": "Dummy Layout",
                    "pack": "dummy_pack",
                    "kind": "indicatorsDetails",
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
                    "kind": "indicatorsDetails",
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

    def test_collect_generic_layouts_dependencies(self, id_set):
        """
        Given
            - A layout entry in the id_set that is related to generic definition

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the layout depends on.
        """
        expected_result = {("pack_with_generic_field", True)}

        test_input = [
            {
                "Dummy Layout": {
                    "typeID": "dummy_layout",
                    "name": "Dummy Layout",
                    "pack": "dummy_pack",
                    "kind": "indicatorsDetails",
                    "path": "dummy_path",
                    "definitionId": "assets",
                    "incident_and_indicator_types": [
                        "generic_type_id"
                    ],
                    "incident_and_indicator_fields": [
                        "generic_field_id"
                    ]
                }
            }
        ]

        found_result = PackDependencies._collect_layouts_dependencies(pack_layouts=test_input,
                                                                      id_set=id_set,
                                                                      verbose=False,
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

    def test_collect_classifier_dependencies_on_filter(self, id_set):
        """
        Given
            - A classifier entry in the id_set with filter from the CommonScripts pack.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the classifier depends on a mandatory dependencies.
        """
        expected_result = {("CommonScripts", True)}

        test_input = [
            {
                "Dummy Classifier": {
                    "name": "Dummy Classifier",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "filters": ["IsInCidrRanges"]
                }
            }
        ]

        found_result = PackDependencies._collect_classifiers_dependencies(
            pack_classifiers=test_input,
            id_set=id_set,
            verbose=False,
        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)

    def test_collect_generic_classifier_dependencies(self, id_set):
        """
        Given
            - A classifier entry in the id_set that has generic definition
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the classifier depends on as optional dependencies.
        """
        expected_result = {("pack_with_generic_type", True)}

        test_input = [
            {
                "Dummy Classifier": {
                    "name": "Dummy Classifier",
                    "fromversion": "5.0.0",
                    "definitionId": "assets",
                    "pack": "dummy_pack",
                    "incident_types": ["generic_type_id"],
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
        print(found_result)
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

    def test_collect_mapper_dependencies_on_filter(self, id_set):
        """
        Given
            - A mapper entry in the id_set with filter from the CommonScripts pack.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the mapper depends on a mandatory dependencies.
        """
        expected_result = {("CommonScripts", True)}

        test_input = [
            {
                "Dummy Mapper": {
                    "name": "Dummy Mapper",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "filters": ["IsInCidrRanges"]
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


class TestDependsOnGenericField:
    def test_collect_generic_field_dependencies(self, id_set):
        """
        Given
            - a generic field entry in the id_set.

        When
            - Building dependency graph for pack.

        Then
            - Extracting the packs that the generic field depends on.
        """
        expected_result = {
            ("Volatility", True), ("pack_with_definition", True), ("pack_with_generic_type", True)
        }

        test_input = [
            {
                "Dummy Generic Field": {
                    "name": "Dummy Generic Field",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "definitionId": "assets",
                    "generic_types": ["generic_type_id"],
                    "scripts": ["AnalyzeMemImage"],
                }
            }
        ]

        found_result = PackDependencies._collect_generic_fields_dependencies(
            pack_generic_fields=test_input,
            id_set=id_set,
            verbose=False,
        )
        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnGenericType:
    def test_collect_generic_type_dependencies(self, id_set):
        """
        Given
            - A generic type entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the generic type depends on.
        """
        expected_result = {("pack_with_definition", True), ("Volatility", True), ("pack5", True)}

        test_input = [
            {
                "Dummy Generic Type": {
                    "name": "Dummy Generic Type",
                    "fromversion": "5.0.0",
                    "pack": "dummy_pack",
                    "scripts": "AnalyzeMemImage",
                    "definitionId": "assets",
                    "layout": "generic_layout_id"
                }
            }
        ]

        found_result = PackDependencies._collect_generic_types_dependencies(
            pack_generic_types=test_input,
            id_set=id_set,
            verbose=False,

        )

        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)


class TestDependsOnGenericModules:
    def test_collect_generic_module_dependencies(self, id_set):
        """
        Given
            - A generic module entry in the id_set.
        When
            - Building dependency graph for pack.
        Then
            - Extracting the packs that the generic module depends on.
        """
        expected_result = {("pack_with_definition", True), ("pack_4", True)}

        test_input = [
            {
                "dummy generic module": {
                    "name": "dummy generic module",
                    "file_path": "path.json",
                    "fromversion": "6.5.0",
                    "pack": "dummy pack",
                    "definitionIds": ["assets"],
                    "views": {
                        "Vulnerability Management": {
                            "title": "Risk Base Vulnerability Management",
                            "dashboards": ["pack_4 - dashboard"]
                        }
                    }
                }
            }
        ]

        found_result = PackDependencies._collect_generic_modules_dependencies(
            pack_generic_modules=test_input,
            id_set=id_set,
            verbose=False,
        )
        assert IsEqualFunctions.is_sets_equal(found_result, expected_result)
