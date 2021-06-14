from collections import OrderedDict

import networkx as nx
import pytest

import demisto_sdk.commands.create_id_set.create_id_set as cis
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions


@pytest.fixture()
def id_set(repo):
    repo.setup_content_repo(5)

    prisma_cloud_compute = repo.create_pack('PrismaCloudCompute')
    prisma_cloud_compute.create_script('PrismaCloudComputeParseAuditAlert').create_default_script(
        'PrismaCloudComputeParseAuditAlert')
    prisma_cloud_compute.create_script('PrismaCloudComputeParseCloudDiscoveryAlert').create_default_script(
        'PrismaCloudComputeParseCloudDiscoveryAlert')
    prisma_cloud_compute.create_script('PrismaCloudComputeParseComplianceAlert').create_default_script(
        'PrismaCloudComputeParseComplianceAlert')
    prisma_cloud_compute.create_script('PrismaCloudComputeParseVulnerabilityAlert').create_default_script(
        'PrismaCloudComputeParseVulnerabilityAlert')
    prisma_cloud_compute.create_incident_type('Prisma Cloud Compute Cloud Discovery',
                                              {'id': 'Prisma Cloud Compute Cloud Discovery',
                                               'name': 'Prisma Cloud Compute Cloud Discovery',
                                               'preProcessingScript': '', 'color': 'test'})

    expanse = repo.create_pack('Expanse')
    expanse.create_playbook('ExpanseParseRawIncident').create_default_playbook('ExpanseParseRawIncident')

    get_server_url = repo.create_pack('GetServerURL')
    get_server_url.create_script('GetServerURL').create_default_script('GetServerURL')

    hello_world = repo.create_pack('HelloWorld')
    hello_world.create_script('HelloWorldScript').create_default_script('HelloWorldScript')
    hello_world.create_classifier('HelloWorld', {'id': 'HelloWorld', 'name': 'HelloWorld', 'transformer': '',
                                                 'keyTypeMap': {}, 'type': 'classification'})

    feedsslabusech = repo.create_pack('Feedsslabusech')
    feedsslabusech.create_integration('Feedsslabusech').create_default_integration(
        'Feedsslabusech', ['sslbl-get-indicators'])

    active_mq = repo.create_pack('ActiveMQ')
    active_mq.create_integration('ActiveMQ').create_default_integration('ActiveMQ', ['activemq-subscribe'])

    feed_alien_vault = repo.create_pack('FeedAlienVault')
    feed_alien_vault.create_integration('FeedAlienVault').create_default_integration(
        'FeedAlienVault', ['alienvault-get-indicators'])

    qradar = repo.create_pack('QRadar')
    qradar.create_integration('QRadar').create_default_integration('QRadar', ['qradar-searches'])

    active_directory_query = repo.create_pack('Active_Directory_Query')
    active_directory_query.create_integration('Active Directory Query').create_default_integration(
        'Active Directory Query', ['ad-get-user', 'ad-search'])
    active_directory_query.create_script('ADGetUser').create_default_script('ADGetUser')

    pcysys = repo.create_pack('Pcysys')
    pcysys.create_playbook('Pentera Run Scan').create_default_playbook('Pentera Run Scan')

    indeni = repo.create_pack('Indeni')
    indeni.create_playbook('Indeni Demo').create_default_playbook('Indeni Demo')

    slack = repo.create_pack('Slack')
    slack.create_playbook('Failed Login Playbook - Slack v2').create_default_playbook(
        'Failed Login Playbook - Slack v2')

    feed_aws = repo.create_pack('FeedAWS')
    feed_aws.create_integration('FeedAWS').create_default_integration('FeedAWS', ['aws-get-indicators'])

    feed_autofocus = repo.create_pack('FeedAutofocus')
    feed_autofocus.create_integration('FeedAutofocus').create_default_integration(
        'FeedAutofocus', ['autofocus-get-indicators'])

    ipinfo = repo.create_pack('ipinfo')
    ipinfo.create_integration('ipinfo').create_default_integration('ipinfo', ['ip'])

    digital_guardian = repo.create_pack('DigitalGuardian')
    digital_guardian.create_incident_field('digitalguardianusername', {'id': 'incident_digitalguardianusername',
                                                                       'name': 'Digital Guardian Username'})

    employee_offboarding = repo.create_pack('EmployeeOffboarding')
    employee_offboarding.create_incident_field('Google Display Name', {'id': 'incident_googledisplayname',
                                                                       'name': 'Google Display Name'})

    phishing = repo.create_pack('Phishing')
    phishing.create_incident_field('attachmentname', {'id': 'incident_attachmentname', 'name': 'Attachment Name'})
    phishing.create_incident_field('emailfrom', {'id': 'incident_emailfrom', 'name': 'Email From'})
    phishing.create_incident_field('emailsubject', {'id': 'incident_emailsubject', 'name': 'Email Subject'})
    phishing.create_script('CheckEmailAuthenticity').create_default_script('CheckEmailAuthenticity')

    common_types = repo.create_pack('CommonTypes')
    common_types.create_incident_field('accountid', {'id': 'incident_accountid', 'name': 'Account Id'})
    common_types.create_incident_field('country', {'id': 'incident_country', 'name': 'Country'})
    common_types.create_incident_field('Username', {'id': 'incident_username', 'name': 'Username'})
    common_types.create_incident_type('Network', {'id': 'Network', 'name': 'Network',
                                                  'preProcessingScript': '', 'color': 'test'})
    common_types.create_incident_type('Authentication', {'id': 'Authentication', 'name': 'Authentication',
                                                         'preProcessingScript': '', 'color': 'test'})
    common_types.create_indicator_field('accounttype', {'id': 'indicator_accounttype', 'name': 'Account Type'})
    common_types.create_indicator_field('adminname', {'id': 'indicator_adminname', 'name': 'adminname'})
    common_types.create_indicator_field('tags', {'id': 'indicator_tags', 'name': 'tags'})
    common_types.create_indicator_field('CommonTypes', {'id': 'CommonTypes', 'name': 'CommonTypes'})
    common_types.create_indicator_field('adminemail', {'id': 'indicator_adminemail', 'name': 'Admin Email'})
    common_types.create_indicator_type('accountRep', {'id': 'accountRep', 'details': 'accountRep', 'regex': ''})

    safe_breach = repo.create_pack('SafeBreach')
    safe_breach.create_indicator_field('safebreachremediationstatus', {'id': 'indicator_safebreachremediationstatus',
                                                                       'name': 'SafeBreach Remediation Status'})
    safe_breach.create_integration('SafeBreach').create_default_integration('SafeBreach',
                                                                            ['safebreach-get-remediation-data'])

    common_scripts = repo.create_pack('CommonScripts')
    common_scripts.create_script('ChangeContext').create_default_script('ChangeContext')
    common_scripts.create_script('Set').create_default_script('Set')
    common_scripts.create_script('SetAndHandleEmpty').create_default_script('SetAndHandleEmpty')
    common_scripts.create_script('AssignAnalystToIncident').create_default_script('AssignAnalystToIncident')
    common_scripts.create_script('EmailAskUser').create_default_script('EmailAskUser')
    common_scripts.create_script('ScheduleCommand').create_default_script('ScheduleCommand')
    common_scripts.create_script('DeleteContext').create_default_script('DeleteContext')

    calculate_time_difference = repo.create_pack('CalculateTimeDifference')
    calculate_time_difference.create_script('CalculateTimeDifference').create_default_script('CalculateTimeDifference')

    common_playbooks = repo.create_pack('CommonPlaybooks')
    common_playbooks.create_playbook('Block IP - Generic v2').create_default_playbook('Block IP - Generic v2')
    common_playbooks.create_playbook('IP Enrichment - Generic v2').create_default_playbook('IP Enrichment - Generic v2')
    common_playbooks.create_playbook('Active Directory - Get User Manager Details').\
        create_default_playbook('Active Directory - Get User Manager Details')

    feed_mitre_attack = repo.create_pack('FeedMitreAttack')
    feed_mitre_attack.create_indicator_type('MITRE ATT&CK',
                                            {'id': 'MITRE ATT&CK', 'details': 'MITRE ATT&CK', 'regex': ''})

    crisis_management = repo.create_pack('CrisisManagement')
    crisis_management.create_incident_type('HR Ticket', {'id': 'HR Ticket', 'name': 'HR Ticket',
                                                         'preProcessingScript': '', 'color': 'test'})
    crisis_management.create_indicator_field('Job_Title', {'id': 'indicator_jobtitle', 'name': 'Job Title'})

    carbon_black_enterprise_response = repo.create_pack('Carbon_Black_Enterprise_Response')
    carbon_black_enterprise_response.create_script('CBLiveFetchFiles').create_default_script('CBLiveFetchFiles')
    carbon_black_enterprise_response.create_script('CBAlerts').create_default_script('CBAlerts')

    claroty = repo.create_pack('Claroty')
    claroty.create_mapper('Claroty-mapper', {'id': 'Claroty-mapper', 'name': 'Claroty-mapper',
                                             'mapping': {}, 'type': 'mapping-incomming'})
    claroty.create_mapper('Claroty', {'id': 'Claroty', 'name': 'Claroty', 'mapping': {}, 'type': 'mapping-incomming'})
    claroty.create_mapper('Claroty - Incoming Mapper', {'id': 'Claroty - Incoming Mapper',
                                                        'name': 'Claroty - Incoming Mapper',
                                                        'mapping': {}, 'type': 'mapping-incomming'})
    claroty.create_incident_type('Claroty Integrity Incident', {'id': 'Claroty Integrity Incident',
                                                                'name': 'Claroty Integrity Incident',
                                                                'preProcessingScript': '', 'color': 'test'})

    ews = repo.create_pack('EWS')
    ews.create_mapper('EWS v2-mapper', {'id': 'EWS v2-mapper', 'name': 'EWS v2-mapper',
                                        'mapping': {}, 'type': 'mapping-incomming'})

    auto_focus = repo.create_pack('AutoFocus')
    auto_focus.create_playbook('Autofocus Query Samples, Sessions and Tags').create_default_playbook(
        'Autofocus Query Samples, Sessions and Tags')

    volatility = repo.create_pack('Volatility')
    volatility.create_script('AnalyzeMemImage').create_default_script('AnalyzeMemImage')

    pan_os = repo.create_pack('PAN-OS')
    pan_os.create_incident_type('FirewallUpgrade', {'id': 'FirewallUpgrade', 'name': 'FirewallUpgrade',
                                                    'preProcessingScript': '', 'color': 'test'})

    logzio = repo.create_pack('Logzio')
    logzio.create_incident_type('Logz.io Alert', {'id': 'Logz.io Alert', 'name': 'Logz.io Alert',
                                                  'preProcessingScript': '', 'color': 'test'})

    access_investigation = repo.create_pack('AccessInvestigation')
    access_investigation.create_incident_type('Access', {'id': 'Access', 'name': 'Access',
                                                         'preProcessingScript': '', 'color': 'test'})

    prisma_cloud = repo.create_pack('PrismaCloud')
    prisma_cloud.create_incident_type('AWS CloudTrail Misconfiguration', {'id': 'AWS CloudTrail Misconfiguration',
                                                                          'name': 'AWS CloudTrail Misconfiguration',
                                                                          'preProcessingScript': '', 'color': 'test'})

    brute_force = repo.create_pack('BruteForce')
    brute_force.create_incident_field('incident_accountgroups', {'id': 'incident_accountgroups',
                                                                 'name': 'incident_accountgroups'})

    complience = repo.create_pack('Compliance')
    complience.create_incident_field('emailaddress', {'id': 'incident_emailaddress', 'name': 'E-mail Address'})

    cortex_xdr = repo.create_pack('CortexXDR')
    cortex_xdr.create_classifier('Cortex XDR - IR', {'id': 'Cortex XDR - IR', 'name': 'Cortex XDR - IR',
                                                     'transformer': '', 'keyTypeMap': {}, 'type': 'classification'})

    impossible_traveler = repo.create_pack('ImpossibleTraveler')
    impossible_traveler.create_script('CalculateGeoDistance').create_default_script('CalculateGeoDistance')
    impossible_traveler.create_playbook('Impossible_Traveler').create_default_playbook('Impossible Traveler')
    impossible_traveler.create_test_playbook(
        'playbook-Impossible_Traveler_-_Test').create_default_test_playbook('Impossible Traveler - Test')
    impossible_traveler.create_layout('Impossible_Traveler', {"TypeName": "Impossible Traveler", "kind": "details",
                                                              "layout": {}, "typeId": "Impossible Traveler",})
    impossible_traveler.create_incident_field('Coordinates', {'id': 'incident_coordinates', 'name': 'Coordinates'})
    impossible_traveler.create_incident_field('Previous_Coordinates', {'id': 'incident_previouscoordinates',
                                                                       'name': 'Previous Coordinates',
                                                                       "associatedTypes": ["Impossible Traveler"]})
    impossible_traveler.create_incident_field('previouscountry', {'id': 'incident_previouscountry',
                                                                  'name': 'previouscountry'})
    impossible_traveler.create_incident_field('Previous_Sign_In_Date_Time',
                                              {'id': 'incident_previoussignindatetime',
                                               'name': 'Previous Sign In Date Time'})
    impossible_traveler.create_incident_field('Previous_Source_IP', {'id': 'incident_previoussourceip',
                                                                     'name': 'Previous Source IP'})
    impossible_traveler.create_incident_field('Sign_In_Date_Time', {'id': 'incident_signindatetime',
                                                                    'name': 'Sign In Date Time'})
    impossible_traveler.create_incident_field('Travel_Map_Link', {'id': 'incident_travelmaplink',
                                                                  'name': 'Travel Map Link'})
    impossible_traveler.create_incident_type('Impossible_Traveler', {'id': 'impossibletraveler',
                                                                     'name': 'Impossible Traveler',
                                                                     "playbookId": "Impossible Traveler",
                                                                     'preProcessingScript': '', 'color': 'test'})

    with ChangeCWD(repo.path):
        ids = cis.IDSetCreator()
        ids.create_id_set()
        return ids.id_set


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
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseCloudDiscoveryAlert": {
                    "name": "PrismaCloudComputeParseCloudDiscoveryAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseCloudDiscoveryAlert/PrismaCloudComputeParseCloudDiscoveryAlert.yml",
                    "fromversion": '5.0.0',
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseComplianceAlert": {
                    "name": "PrismaCloudComputeParseComplianceAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseComplianceAlert/PrismaCloudComputeParseComplianceAlert.yml",
                    "fromversion": '5.0.0',
                    "pack": "PrismaCloudCompute"
                }
            },
            {
                "PrismaCloudComputeParseVulnerabilityAlert": {
                    "name": "PrismaCloudComputeParseVulnerabilityAlert",
                    "file_path": "Packs/PrismaCloudCompute/Scripts/PrismaCloudComputeParseVulnerabilityAlert/PrismaCloudComputeParseVulnerabilityAlert.yml",
                    "fromversion": '5.0.0',
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
                'ExpanseParseRawIncident': OrderedDict([
                    ('name', 'ExpanseParseRawIncident'),
                    ('file_path', 'Packs/Expanse/Playbooks/ExpanseParseRawIncident.yml'),
                    ('fromversion', '5.0.0'),
                    ('pack', 'Expanse'),
                    ('implementing_scripts', ['DeleteContext']),
                    ('tests', ['No tests'])
                ])
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
