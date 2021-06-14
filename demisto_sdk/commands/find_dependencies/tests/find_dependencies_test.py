import json
import os
import yaml
from collections import OrderedDict
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
    common_playbooks.create_playbook('Active Directory - Get User Manager Details').create_default_playbook('Active Directory - Get User Manager Details')

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
    script = {'commonfields': {'id': 'CalculateGeoDistance', 'version': -1}, 'name': 'CalculateGeoDistance', 'type': 'python', 'subtype': 'python3', 'script': '-', 'tags': ['Utilities'], 'comment': 'Compute the distance between two sets of coordinates, in miles.', 'enabled': True, 'args': [{'name': 'src_coords', 'required': True, 'description': 'Latitude and Longitude coordinates for the first location.  Required format 1.23,4.56'}, {'name': 'dest_coords', 'required': True, 'description': 'Latitude and Longitude coordinates for the second location.  Required format 1.23,4.56'}], 'outputs': [{'contextPath': 'Geo.Distance', 'description': 'Distance between two sets of coordinates, in miles.'}, {'contextPath': 'Geo.Coordinates', 'description': 'List of coordinates used in the calculation.'}], 'scripttarget': 0, 'runonce': False, 'dockerimage': 'demisto/geopy:1.0.0.3443', 'runas': 'DBotWeakRole', 'tests': ['Impossible Traveler - Test'], 'fromversion': '5.0.0'}
    playbook = {'id': 'Impossible Traveler', 'version': -1, 'name': 'Impossible Traveler', 'description': 'This playbook investigates an event whereby a user has multiple application login attempts from various locations in a short time period (impossible traveler). The playbook gathers user, timestamp and IP information\nassociated with the multiple application login attempts.\n\nThe playbook then measures the time difference between the multiple login attempts and computes the distance between the two locations to verify whether it is possible the user could traverse the distance\nin the amount of time determined. Also, it takes steps to remediate the incident by blocking the offending IPs and disabling the user account, if chosen to do so.', 'starttaskid': '0', 'tasks': {'0': {'id': '0', 'taskid': '89164d19-18a8-41d4-8f40-cd6cde0b0135', 'type': 'start', 'task': {'id': '89164d19-18a8-41d4-8f40-cd6cde0b0135', 'version': -1, 'name': '', 'iscommand': False, 'brand': '', 'description': ''}, 'nexttasks': {'#none#': ['62', '61']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 520,\n    "y": -560\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '29': {'id': '29', 'taskid': 'fbd79de9-bdbb-4048-878b-f14aec5a8ef8', 'type': 'regular', 'task': {'id': 'fbd79de9-bdbb-4048-878b-f14aec5a8ef8', 'version': -1, 'name': 'Calculate geographical distance between logins', 'description': 'Compute the distance between two sets of coordinates in miles.', 'tags': ['geodistance'], 'scriptName': 'CalculateGeoDistance', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['63']}, 'scriptarguments': {'dest_coords': {'complex': {'root': 'SourceIPGeo', 'transformers': [{'operator': 'uniq'}]}}, 'src_coords': {'complex': {'root': 'PreviousSourceIPGeo', 'transformers': [{'operator': 'uniq'}]}}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -870,\n    "y": 1620\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '30': {'id': '30', 'taskid': '7b361c68-abe6-4c83-88b4-ca2bc253e297', 'type': 'regular', 'task': {'id': '7b361c68-abe6-4c83-88b4-ca2bc253e297', 'version': -1, 'name': 'Calculate time difference between logins', 'description': 'Calculate the time difference, in minutes.', 'tags': ['eventduration'], 'scriptName': 'CalculateTimeDifference', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['63']}, 'scriptarguments': {'end_time': {'complex': {'root': 'incident', 'accessor': 'signindatetime', 'transformers': [{'operator': 'uniq'}]}}, 'start_time': {'complex': {'root': 'incident', 'accessor': 'previoussignindatetime', 'transformers': [{'operator': 'uniq'}]}}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 330,\n    "y": 1620\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '32': {'id': '32', 'taskid': 'f2a7691c-df68-41af-8a05-825aed028836', 'type': 'title', 'task': {'id': 'f2a7691c-df68-41af-8a05-825aed028836', 'version': -1, 'name': 'Containment', 'type': 'title', 'iscommand': False, 'brand': '', 'description': ''}, 'nexttasks': {'#none#': ['36']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 300,\n    "y": 3265\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '34': {'id': '34', 'taskid': '3d27c29a-1136-4c00-89f6-ae243d901d7f', 'type': 'regular', 'task': {'id': '3d27c29a-1136-4c00-89f6-ae243d901d7f', 'version': -1, 'name': 'Disable user account', 'description': 'Disables the account of the offending user, using Active Directory.', 'script': '|||ad-disable-account', 'type': 'regular', 'iscommand': True, 'brand': ''}, 'nexttasks': {'#none#': ['38']}, 'scriptarguments': {'base-dn': {}, 'username': {'complex': {'root': 'incident', 'accessor': 'username'}}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 300,\n    "y": 4150\n  }\n}', 'note': True, 'timertriggers': [{'fieldname': 'remediationsla', 'action': 'start'}], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '36': {'id': '36', 'taskid': 'a7114ae3-88f9-4ee9-8e1d-6760bec70749', 'type': 'regular', 'task': {'id': 'a7114ae3-88f9-4ee9-8e1d-6760bec70749', 'version': -1, 'name': 'Update incident details and set severity', 'description': 'Updates the incident details to say that the user is an impossible traveler, and sets the incident severity to high.', 'script': 'Builtin|||setIncident', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'nexttasks': {'#none#': ['74']}, 'scriptarguments': {'addLabels': {}, 'affecteddata': {}, 'affecteddatatype': {}, 'affectedhosts': {}, 'affectedindividualscontactinformation': {}, 'affectedips': {}, 'app': {}, 'approximatenumberofaffecteddatasubjects': {}, 'assetid': {}, 'attachmentcount': {}, 'attachmentextension': {}, 'attachmenthash': {}, 'attachmentid': {}, 'attachmentitem': {}, 'attachmentname': {}, 'attachmentsize': {}, 'attachmenttype': {}, 'awsfindingid': {}, 'awsfindingtype': {}, 'awsinstanceid': {}, 'awsinstancename': {}, 'backupowner': {}, 'bugtraq': {}, 'campaigntargetcount': {}, 'campaigntargets': {}, 'city': {}, 'closeNotes': {}, 'closeReason': {}, 'companyaddress': {}, 'companycity': {}, 'companycountry': {}, 'companyhasinsuranceforthebreach': {}, 'companyname': {}, 'companypostalcode': {}, 'computername': {}, 'contactaddress': {}, 'contactname': {}, 'coordinates': {'complex': {'root': 'SourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'country': {}, 'countrywherebusinesshasitsmainestablishment': {}, 'countrywherethebreachtookplace': {}, 'criticalassets': {}, 'currentip': {}, 'customFields': {}, 'cve': {}, 'cvss': {}, 'dataencryptionstatus': {}, 'datetimeofthebreach': {}, 'daysbetweenreportcreation': {}, 'deleteEmptyField': {}, 'demoautomatedcondition': {}, 'demomanualcondition': {}, 'description': {}, 'dest': {}, 'destinationip': {}, 'destip': {}, 'destntdomain': {}, 'details': {'simple': 'A user has logged in from multiple geographical locations in too short an amount of time. The user is an impossible traveler according to the maximum miles per hour allowed.'}, 'detectedusers': {}, 'detectorid': {}, 'dpoemailaddress': {}, 'duration': {}, 'emailaddress': {}, 'emailauthenticitycheck': {}, 'emailbcc': {}, 'emailbody': {}, 'emailbodyformat': {}, 'emailbodyhtml': {}, 'emailcc': {}, 'emailclassification': {}, 'emailclientname': {}, 'emailfrom': {}, 'emailheaders': {}, 'emailhtml': {}, 'emailinreplyto': {}, 'emailkeywords': {}, 'emailmessageid': {}, 'emailreceived': {}, 'emailrecipient': {}, 'emailreplyto': {}, 'emailreturnpath': {}, 'emailsenderip': {}, 'emailsize': {}, 'emailsource': {}, 'emailsubject': {}, 'emailto': {}, 'emailtocount': {}, 'emailurlclicked': {}, 'endpointgrid': {}, 'epohost': {}, 'eposcanstatus': {}, 'eventid': {}, 'falses': {}, 'fetchid': {}, 'fetchtype': {}, 'filehash': {}, 'filename': {}, 'filepath': {}, 'findingid': {}, 'host': {}, 'hostid': {}, 'hostname': {}, 'htmlimage': {}, 'htmlrenderedimage': {}, 'id': {}, 'important': {}, 'importantfield': {}, 'infected': {}, 'internalip': {}, 'involvedusers': {}, 'isthedatasubjecttodpia': {}, 'jasontest': {}, 'labels': {}, 'likelyimpact': {}, 'maliciouscauseifthecauseisamaliciousattack': {}, 'malwarefamily': {}, 'mdtest': {}, 'measurestomitigate': {}, 'myfield': {}, 'name': {}, 'notes': {}, 'occurred': {}, 'owner': {}, 'phase': {'simple': 'Containment'}, 'phishingconfirmationstatus': {}, 'phishingsubtype': {}, 'possiblecauseofthebreach': {}, 'postalcode': {}, 'previouscoordinates': {'complex': {'root': 'PreviousSourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'previousip': {}, 'previoussignindatetime': {}, 'previoussourceip': {}, 'queue': {}, 'redlockpolicyname': {}, 'relateddomain': {}, 'replacePlaybook': {}, 'reporteduser': {}, 'reporteremailaddress': {}, 'reportingdepartment': {}, 'reportinguser': {}, 'requestor': {}, 'riskscore': {}, 'roles': {}, 'screenshot': {}, 'screenshot2': {}, 'sectorofaffectedparty': {}, 'securitygroupid': {}, 'selector': {}, 'serverip': {}, 'servername': {}, 'severity': {'simple': 'high'}, 'signature': {}, 'signindatetime': {}, 'single': {}, 'single2': {}, 'sizenumberofemployees': {}, 'sizeturnover': {}, 'sla': {}, 'slaField': {}, 'source': {}, 'sourceip': {}, 'src': {}, 'srcip': {}, 'srcntdomain': {}, 'srcuser': {}, 'systems': {}, 'telephoneno': {}, 'test': {}, 'test2': {}, 'testfield': {}, 'timeassignedtolevel2': {}, 'timefield1': {}, 'timelevel1': {}, 'travelmaplink': {'complex': {'root': 'TravelMap', 'transformers': [{'operator': 'uniq'}]}}, 'type': {}, 'urlsslverification': {}, 'user': {}, 'username': {}, 'vendorid': {}, 'vendorproduct': {}, 'vulnerabilitycategory': {}, 'whereisdatahosted': {}, 'whitelistrequest': {}, 'xdr': {}, 'xdralertcount': {}, 'xdralerts': {}, 'xdrassigneduseremail': {}, 'xdrassigneduserprettyname': {}, 'xdrdescription': {}, 'xdrdetectiontime': {}, 'xdrfileartifacts': {}, 'xdrhighseverityalertcount': {}, 'xdrincidentid': {}, 'xdrlowseverityalertcount': {}, 'xdrmediumseverityalertcount': {}, 'xdrnetworkartifacts': {}, 'xdrnotes': {}, 'xdrresolvecomment': {}, 'xdrstatus': {}, 'xdrurl': {}, 'xdrusercount': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 300,\n    "y": 3410\n  }\n}', 'note': False, 'timertriggers': [{'fieldname': 'detectionsla', 'action': 'stop'}], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '38': {'id': '38', 'taskid': '39db20af-3fdb-45dc-8905-a2042bb4c515', 'type': 'condition', 'task': {'id': '39db20af-3fdb-45dc-8905-a2042bb4c515', 'version': -1, 'name': 'Should the source IPs be blocked automatically', 'description': 'Checks whether the source IPs that the user used to login from can be blocked automatically, according to the playbook inputs.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['79'], 'yes': ['71']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isEqualString', 'left': {'value': {'complex': {'root': 'inputs.AutomaticallyBlockIPs'}}, 'iscontext': True}, 'right': {'value': {'simple': 'True'}}, 'ignorecase': True}]]}], 'view': '{\n  "position": {\n    "x": 300,\n    "y": 4330\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '49': {'id': '49', 'taskid': '9f5e52fe-9abb-4cbe-8a6d-3f1e09424888', 'type': 'playbook', 'task': {'id': '9f5e52fe-9abb-4cbe-8a6d-3f1e09424888', 'version': -1, 'name': 'IP Enrichment - Generic v2', 'playbookName': 'IP Enrichment - Generic v2', 'type': 'playbook', 'iscommand': False, 'brand': '', 'description': ''}, 'nexttasks': {'#none#': ['51']}, 'scriptarguments': {'IP': {'complex': {'root': 'IP', 'accessor': 'Address', 'transformers': [{'operator': 'uniq'}]}}, 'InternalRange': {}, 'ResolveIP': {'simple': 'True'}}, 'separatecontext': True, 'loop': {'iscommand': False, 'exitCondition': '', 'wait': 1, 'max': 0}, 'view': '{\n  "position": {\n    "x": 1680,\n    "y": -90\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '50': {'id': '50', 'taskid': '06854db3-617e-4bb3-8772-2c2b3f3bfdd7', 'type': 'title', 'task': {'id': '06854db3-617e-4bb3-8772-2c2b3f3bfdd7', 'version': -1, 'name': 'Travel Information Enrichment', 'type': 'title', 'iscommand': False, 'brand': '', 'description': ''}, 'nexttasks': {'#none#': ['49', '80', '91', '90']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 510,\n    "y": -230\n  }\n}', 'note': False, 'timertriggers': [{'fieldname': 'detectionsla', 'action': 'start'}], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '51': {'id': '51', 'taskid': 'd7cd290c-80c0-476d-85e9-0b8777bd4d5a', 'type': 'title', 'task': {'id': 'd7cd290c-80c0-476d-85e9-0b8777bd4d5a', 'version': -1, 'name': 'Investigation', 'type': 'title', 'iscommand': False, 'brand': '', 'description': ''}, 'nexttasks': {'#none#': ['52']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 500,\n    "y": 805\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '52': {'id': '52', 'taskid': '651c4db4-919c-46fb-8b2a-c1bc4640e6e5', 'type': 'condition', 'task': {'id': '651c4db4-919c-46fb-8b2a-c1bc4640e6e5', 'version': -1, 'name': 'Are there coordinates for the source IPs', 'description': 'Checks whether coordinates were retrieved for the IPs that the user used to login.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['54'], 'yes': ['58', '59']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isNotEmpty', 'left': {'value': {'complex': {'root': 'IP', 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.sourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Location'}}}}]}}, 'iscontext': True}}], [{'operator': 'isNotEmpty', 'left': {'value': {'complex': {'root': 'IP', 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.previoussourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Location'}}}}]}}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": 500,\n    "y": 945\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '54': {'id': '54', 'taskid': 'f104955a-88f7-4cb8-87c7-34572cd5daf8', 'type': 'regular', 'task': {'id': 'f104955a-88f7-4cb8-87c7-34572cd5daf8', 'version': -1, 'name': 'Manually investigate the incident', 'description': 'Manually investigate the incident. Try to understand the locations from which the user connected, and the time difference between the two logins. Contain the incident, if needed.', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['70']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 1380,\n    "y": 1130\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '58': {'id': '58', 'taskid': 'ebac010f-b093-4500-828f-11a42f9cbc4d', 'type': 'regular', 'task': {'id': 'ebac010f-b093-4500-828f-11a42f9cbc4d', 'version': -1, 'name': 'Save source IP geolocation data', 'description': "Saves the geolocation of the IP associated with the user's login.", 'scriptName': 'Set', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['73']}, 'scriptarguments': {'append': {}, 'key': {'simple': 'SourceIPGeo'}, 'value': {'complex': {'root': 'IP', 'filters': [[{'operator': 'isExists', 'left': {'value': {'simple': 'Geo.Location'}, 'iscontext': True}}]], 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.sourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Location'}}}}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -40,\n    "y": 1130\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '59': {'id': '59', 'taskid': '28eefc43-ae17-466c-8719-b0d9bc5efb2c', 'type': 'regular', 'task': {'id': '28eefc43-ae17-466c-8719-b0d9bc5efb2c', 'version': -1, 'name': 'Save previous source IP geolocation data', 'description': 'Saves the geolocation of the IP associated with the previous user login.', 'scriptName': 'Set', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['73']}, 'scriptarguments': {'append': {}, 'key': {'simple': 'PreviousSourceIPGeo'}, 'value': {'complex': {'root': 'IP', 'filters': [[{'operator': 'isExists', 'left': {'value': {'simple': 'Geo.Location'}, 'iscontext': True}}]], 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.previoussourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Location'}}}}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -510,\n    "y": 1130\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '61': {'id': '61', 'taskid': '1964cbf7-a1b1-417e-81b3-6ffca7076405', 'type': 'regular', 'task': {'id': '1964cbf7-a1b1-417e-81b3-6ffca7076405', 'version': -1, 'name': 'Get previous login IP location information', 'description': 'Gets geolocation information about the previous IP that the user logged in from.', 'script': '|||ip', 'type': 'regular', 'iscommand': True, 'brand': ''}, 'nexttasks': {'#none#': ['50']}, 'scriptarguments': {'days': {}, 'fullResponse': {}, 'include_inactive': {}, 'ip': {'complex': {'root': 'incident', 'accessor': 'previoussourceip', 'transformers': [{'operator': 'uniq'}]}}, 'long': {}, 'retries': {}, 'sampleSize': {}, 'threshold': {}, 'verbose': {}, 'wait': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 740,\n    "y": -400\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '62': {'id': '62', 'taskid': '5b5ea973-d7d3-4110-8659-5de212e778de', 'type': 'regular', 'task': {'id': '5b5ea973-d7d3-4110-8659-5de212e778de', 'version': -1, 'name': 'Get login IP location information', 'description': 'Gets geolocation information about the IP that the user logged in from.', 'script': '|||ip', 'type': 'regular', 'iscommand': True, 'brand': ''}, 'nexttasks': {'#none#': ['50']}, 'scriptarguments': {'days': {}, 'fullResponse': {}, 'include_inactive': {}, 'ip': {'complex': {'root': 'incident', 'accessor': 'sourceip', 'transformers': [{'operator': 'uniq'}]}}, 'long': {}, 'retries': {}, 'sampleSize': {}, 'threshold': {}, 'verbose': {}, 'wait': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 290,\n    "y": -400\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '63': {'id': '63', 'taskid': 'b5f9fe73-ecaa-4f9a-8799-d51cc0591cbf', 'type': 'condition', 'task': {'id': 'b5f9fe73-ecaa-4f9a-8799-d51cc0591cbf', 'version': -1, 'name': 'Did the user travel more than the allowed MPH', 'description': 'Checks whether the user traveled faster than the allowed speed in MPH.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['66'], 'yes': ['84']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'greaterThan', 'left': {'value': {'complex': {'root': 'Geo', 'accessor': 'Distance', 'transformers': [{'operator': 'division', 'args': {'by': {'value': {'simple': 'Time.Difference'}, 'iscontext': True}}}, {'operator': 'multiply', 'args': {'by': {'value': {'simple': '60'}}}}]}}, 'iscontext': True}, 'right': {'value': {'simple': 'inputs.MaxMilesPerHourAllowed'}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": -270,\n    "y": 1980\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '66': {'id': '66', 'taskid': '62ef2221-0863-4e24-8a14-de995bf906cb', 'type': 'regular', 'task': {'id': '62ef2221-0863-4e24-8a14-de995bf906cb', 'version': -1, 'name': 'Update incident details and set severity', 'description': 'Updates the incident details to say that the user is a legitimate traveler, and sets the incident severity to low.', 'script': 'Builtin|||setIncident', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'nexttasks': {'#none#': ['70']}, 'scriptarguments': {'addLabels': {}, 'affecteddata': {}, 'affecteddatatype': {}, 'affectedhosts': {}, 'affectedindividualscontactinformation': {}, 'affectedips': {}, 'app': {}, 'approximatenumberofaffecteddatasubjects': {}, 'assetid': {}, 'attachmentcount': {}, 'attachmentextension': {}, 'attachmenthash': {}, 'attachmentid': {}, 'attachmentitem': {}, 'attachmentname': {}, 'attachmentsize': {}, 'attachmenttype': {}, 'awsfindingid': {}, 'awsfindingtype': {}, 'awsinstanceid': {}, 'awsinstancename': {}, 'backupowner': {}, 'bugtraq': {}, 'campaigntargetcount': {}, 'campaigntargets': {}, 'city': {}, 'closeNotes': {}, 'closeReason': {}, 'companyaddress': {}, 'companycity': {}, 'companycountry': {}, 'companyhasinsuranceforthebreach': {}, 'companyname': {}, 'companypostalcode': {}, 'computername': {}, 'contactaddress': {}, 'contactname': {}, 'coordinates': {'complex': {'root': 'SourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'country': {}, 'countrywherebusinesshasitsmainestablishment': {}, 'countrywherethebreachtookplace': {}, 'criticalassets': {}, 'currentip': {}, 'customFields': {}, 'cve': {}, 'cvss': {}, 'dataencryptionstatus': {}, 'datetimeofthebreach': {}, 'daysbetweenreportcreation': {}, 'deleteEmptyField': {}, 'demoautomatedcondition': {}, 'demomanualcondition': {}, 'description': {}, 'dest': {}, 'destinationip': {}, 'destip': {}, 'destntdomain': {}, 'details': {'simple': 'The user logged in from two different locations within a reasonable time period.'}, 'detectedusers': {}, 'detectorid': {}, 'dpoemailaddress': {}, 'duration': {}, 'emailaddress': {}, 'emailauthenticitycheck': {}, 'emailbcc': {}, 'emailbody': {}, 'emailbodyformat': {}, 'emailbodyhtml': {}, 'emailcc': {}, 'emailclassification': {}, 'emailclientname': {}, 'emailfrom': {}, 'emailheaders': {}, 'emailhtml': {}, 'emailinreplyto': {}, 'emailkeywords': {}, 'emailmessageid': {}, 'emailreceived': {}, 'emailrecipient': {}, 'emailreplyto': {}, 'emailreturnpath': {}, 'emailsenderip': {}, 'emailsize': {}, 'emailsource': {}, 'emailsubject': {}, 'emailto': {}, 'emailtocount': {}, 'emailurlclicked': {}, 'endpointgrid': {}, 'epohost': {}, 'eposcanstatus': {}, 'eventid': {}, 'falses': {}, 'fetchid': {}, 'fetchtype': {}, 'filehash': {}, 'filename': {}, 'filepath': {}, 'findingid': {}, 'host': {}, 'hostid': {}, 'hostname': {}, 'htmlimage': {}, 'htmlrenderedimage': {}, 'id': {}, 'important': {}, 'importantfield': {}, 'infected': {}, 'internalip': {}, 'involvedusers': {}, 'isthedatasubjecttodpia': {}, 'jasontest': {}, 'labels': {}, 'likelyimpact': {}, 'maliciouscauseifthecauseisamaliciousattack': {}, 'malwarefamily': {}, 'mdtest': {}, 'measurestomitigate': {}, 'myfield': {}, 'name': {}, 'notes': {}, 'occurred': {}, 'owner': {}, 'phase': {'simple': 'No Response Needed (Legitimate Login)'}, 'phishingconfirmationstatus': {}, 'phishingsubtype': {}, 'possiblecauseofthebreach': {}, 'postalcode': {}, 'previouscoordinates': {'complex': {'root': 'PreviousSourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'previousip': {}, 'previoussignindatetime': {}, 'previoussourceip': {}, 'queue': {}, 'redlockpolicyname': {}, 'relateddomain': {}, 'replacePlaybook': {}, 'reporteduser': {}, 'reporteremailaddress': {}, 'reportingdepartment': {}, 'reportinguser': {}, 'requestor': {}, 'riskscore': {}, 'roles': {}, 'screenshot': {}, 'screenshot2': {}, 'sectorofaffectedparty': {}, 'securitygroupid': {}, 'selector': {}, 'serverip': {}, 'servername': {}, 'severity': {'simple': 'low'}, 'signature': {}, 'signindatetime': {}, 'single': {}, 'single2': {}, 'sizenumberofemployees': {}, 'sizeturnover': {}, 'sla': {}, 'slaField': {}, 'source': {}, 'sourceip': {}, 'src': {}, 'srcip': {}, 'srcntdomain': {}, 'srcuser': {}, 'systems': {}, 'telephoneno': {}, 'test': {}, 'test2': {}, 'testfield': {}, 'timeassignedtolevel2': {}, 'timefield1': {}, 'timelevel1': {}, 'travelmaplink': {'complex': {'root': 'TravelMap', 'transformers': [{'operator': 'uniq'}]}}, 'type': {}, 'urlsslverification': {}, 'user': {}, 'username': {}, 'vendorid': {}, 'vendorproduct': {}, 'vulnerabilitycategory': {}, 'whereisdatahosted': {}, 'whitelistrequest': {}, 'xdr': {}, 'xdralertcount': {}, 'xdralerts': {}, 'xdrassigneduseremail': {}, 'xdrassigneduserprettyname': {}, 'xdrdescription': {}, 'xdrdetectiontime': {}, 'xdrfileartifacts': {}, 'xdrhighseverityalertcount': {}, 'xdrincidentid': {}, 'xdrlowseverityalertcount': {}, 'xdrmediumseverityalertcount': {}, 'xdrnetworkartifacts': {}, 'xdrnotes': {}, 'xdrresolvecomment': {}, 'xdrstatus': {}, 'xdrurl': {}, 'xdrusercount': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -940,\n    "y": 3265\n  }\n}', 'note': False, 'timertriggers': [{'fieldname': 'detectionsla', 'action': 'stop'}], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '67': {'id': '67', 'taskid': '5aff0009-233a-4263-825c-bb3c0540d3e9', 'type': 'condition', 'task': {'id': '5aff0009-233a-4263-825c-bb3c0540d3e9', 'version': -1, 'name': 'Did the user login from whitelisted IP addresses', 'description': 'Checks whether both user login events originated from whitelisted IP addresses.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['32'], 'yes': ['69']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'in', 'left': {'value': {'complex': {'root': 'incident', 'accessor': 'sourceip', 'transformers': [{'operator': 'uniq'}]}}, 'iscontext': True}, 'right': {'value': {'complex': {'root': 'inputs.WhitelistedIPs', 'transformers': [{'operator': 'splitAndTrim', 'args': {'delimiter': {'value': {'simple': ','}}}}]}}, 'iscontext': True}}], [{'operator': 'in', 'left': {'value': {'complex': {'root': 'incident', 'accessor': 'sourceip', 'transformers': [{'operator': 'uniq'}]}}, 'iscontext': True}, 'right': {'value': {'complex': {'root': 'inputs.WhitelistedIPs', 'transformers': [{'operator': 'splitAndTrim', 'args': {'delimiter': {'value': {'simple': ','}}}}]}}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": 10,\n    "y": 3010\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '68': {'id': '68', 'taskid': 'e6335721-25ca-4a6b-8173-d10b03b301a3', 'type': 'condition', 'task': {'id': 'e6335721-25ca-4a6b-8173-d10b03b301a3', 'version': -1, 'name': 'Are there whitelisted IPs configured', 'description': 'Checks whether whitelisted IPs were configured.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['32'], 'yes': ['67']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isNotEmpty', 'left': {'value': {'simple': 'inputs.WhitelistedIPs'}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": 300,\n    "y": 2800\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '69': {'id': '69', 'taskid': 'a3ac527f-81e5-476b-8537-ce081304e047', 'type': 'regular', 'task': {'id': 'a3ac527f-81e5-476b-8537-ce081304e047', 'version': -1, 'name': 'Update incident details and set severity', 'description': 'Updates the incident details to say that the user is a legitimate traveler because the login events originated from whitelisted IP addresses, and sets the incident severity to low.', 'script': 'Builtin|||setIncident', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'nexttasks': {'#none#': ['70']}, 'scriptarguments': {'addLabels': {}, 'affecteddata': {}, 'affecteddatatype': {}, 'affectedhosts': {}, 'affectedindividualscontactinformation': {}, 'affectedips': {}, 'app': {}, 'approximatenumberofaffecteddatasubjects': {}, 'assetid': {}, 'attachmentcount': {}, 'attachmentextension': {}, 'attachmenthash': {}, 'attachmentid': {}, 'attachmentitem': {}, 'attachmentname': {}, 'attachmentsize': {}, 'attachmenttype': {}, 'awsfindingid': {}, 'awsfindingtype': {}, 'awsinstanceid': {}, 'awsinstancename': {}, 'backupowner': {}, 'bugtraq': {}, 'campaigntargetcount': {}, 'campaigntargets': {}, 'city': {}, 'closeNotes': {}, 'closeReason': {}, 'companyaddress': {}, 'companycity': {}, 'companycountry': {}, 'companyhasinsuranceforthebreach': {}, 'companyname': {}, 'companypostalcode': {}, 'computername': {}, 'contactaddress': {}, 'contactname': {}, 'coordinates': {'complex': {'root': 'SourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'country': {}, 'countrywherebusinesshasitsmainestablishment': {}, 'countrywherethebreachtookplace': {}, 'criticalassets': {}, 'currentip': {}, 'customFields': {}, 'cve': {}, 'cvss': {}, 'dataencryptionstatus': {}, 'datetimeofthebreach': {}, 'daysbetweenreportcreation': {}, 'deleteEmptyField': {}, 'demoautomatedcondition': {}, 'demomanualcondition': {}, 'description': {}, 'dest': {}, 'destinationip': {}, 'destip': {}, 'destntdomain': {}, 'details': {'simple': 'A user has logged in from multiple geographical locations in a short amount of time. However, they logged in from whitelisted IP addresses, so the login was considered legitimate.'}, 'detectedusers': {}, 'detectorid': {}, 'dpoemailaddress': {}, 'duration': {}, 'emailaddress': {}, 'emailauthenticitycheck': {}, 'emailbcc': {}, 'emailbody': {}, 'emailbodyformat': {}, 'emailbodyhtml': {}, 'emailcc': {}, 'emailclassification': {}, 'emailclientname': {}, 'emailfrom': {}, 'emailheaders': {}, 'emailhtml': {}, 'emailinreplyto': {}, 'emailkeywords': {}, 'emailmessageid': {}, 'emailreceived': {}, 'emailrecipient': {}, 'emailreplyto': {}, 'emailreturnpath': {}, 'emailsenderip': {}, 'emailsize': {}, 'emailsource': {}, 'emailsubject': {}, 'emailto': {}, 'emailtocount': {}, 'emailurlclicked': {}, 'endpointgrid': {}, 'epohost': {}, 'eposcanstatus': {}, 'eventid': {}, 'falses': {}, 'fetchid': {}, 'fetchtype': {}, 'filehash': {}, 'filename': {}, 'filepath': {}, 'findingid': {}, 'host': {}, 'hostid': {}, 'hostname': {}, 'htmlimage': {}, 'htmlrenderedimage': {}, 'id': {}, 'important': {}, 'importantfield': {}, 'infected': {}, 'internalip': {}, 'involvedusers': {}, 'isthedatasubjecttodpia': {}, 'jasontest': {}, 'labels': {}, 'likelyimpact': {}, 'maliciouscauseifthecauseisamaliciousattack': {}, 'malwarefamily': {}, 'mdtest': {}, 'measurestomitigate': {}, 'myfield': {}, 'name': {}, 'notes': {}, 'occurred': {}, 'owner': {}, 'phase': {'simple': 'No Response Needed (Whitelisted Login)'}, 'phishingconfirmationstatus': {}, 'phishingsubtype': {}, 'possiblecauseofthebreach': {}, 'postalcode': {}, 'previouscoordinates': {'complex': {'root': 'PreviousSourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'previousip': {}, 'previoussignindatetime': {}, 'previoussourceip': {}, 'queue': {}, 'redlockpolicyname': {}, 'relateddomain': {}, 'replacePlaybook': {}, 'reporteduser': {}, 'reporteremailaddress': {}, 'reportingdepartment': {}, 'reportinguser': {}, 'requestor': {}, 'riskscore': {}, 'roles': {}, 'screenshot': {}, 'screenshot2': {}, 'sectorofaffectedparty': {}, 'securitygroupid': {}, 'selector': {}, 'serverip': {}, 'servername': {}, 'severity': {'simple': 'low'}, 'signature': {}, 'signindatetime': {}, 'single': {}, 'single2': {}, 'sizenumberofemployees': {}, 'sizeturnover': {}, 'sla': {}, 'slaField': {}, 'source': {}, 'sourceip': {}, 'src': {}, 'srcip': {}, 'srcntdomain': {}, 'srcuser': {}, 'systems': {}, 'telephoneno': {}, 'test': {}, 'test2': {}, 'testfield': {}, 'timeassignedtolevel2': {}, 'timefield1': {}, 'timelevel1': {}, 'travelmaplink': {'complex': {'root': 'TravelMap', 'transformers': [{'operator': 'uniq'}]}}, 'type': {}, 'urlsslverification': {}, 'user': {}, 'username': {}, 'vendorid': {}, 'vendorproduct': {}, 'vulnerabilitycategory': {}, 'whereisdatahosted': {}, 'whitelistrequest': {}, 'xdr': {}, 'xdralertcount': {}, 'xdralerts': {}, 'xdrassigneduseremail': {}, 'xdrassigneduserprettyname': {}, 'xdrdescription': {}, 'xdrdetectiontime': {}, 'xdrfileartifacts': {}, 'xdrhighseverityalertcount': {}, 'xdrincidentid': {}, 'xdrlowseverityalertcount': {}, 'xdrmediumseverityalertcount': {}, 'xdrnetworkartifacts': {}, 'xdrnotes': {}, 'xdrresolvecomment': {}, 'xdrstatus': {}, 'xdrurl': {}, 'xdrusercount': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -430,\n    "y": 3265\n  }\n}', 'note': False, 'timertriggers': [{'fieldname': 'detectionsla', 'action': 'stop'}], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '70': {'id': '70', 'taskid': '51a959c2-f2f6-42ff-852c-781f4b88f3be', 'type': 'regular', 'task': {'id': '51a959c2-f2f6-42ff-852c-781f4b88f3be', 'version': -1, 'name': 'Close investigation', 'description': 'Closes the investigation.', 'script': 'Builtin|||closeInvestigation', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'scriptarguments': {'assetid': {}, 'closeNotes': {}, 'closeReason': {}, 'emailclassification': {}, 'id': {}, 'importantfield': {}, 'phishingsubtype': {}, 'test2': {}, 'timefield1': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 550,\n    "y": 4820\n  }\n}', 'note': False, 'timertriggers': [{'fieldname': 'remediationsla', 'action': 'stop'}], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '71': {'id': '71', 'taskid': '098f8f47-ab0a-44b5-8791-0d407f959f99', 'type': 'playbook', 'task': {'id': '098f8f47-ab0a-44b5-8791-0d407f959f99', 'version': -1, 'name': 'Block IP - Generic v2', 'playbookName': 'Block IP - Generic v2', 'type': 'playbook', 'iscommand': False, 'brand': '', 'description': ''}, 'nexttasks': {'#none#': ['70']}, 'scriptarguments': {'IP': {'complex': {'root': 'incident', 'accessor': 'sourceip', 'transformers': [{'operator': 'concat', 'args': {'prefix': {}, 'suffix': {'value': {'simple': ','}}}}, {'operator': 'concat', 'args': {'prefix': {}, 'suffix': {'value': {'simple': 'incident.previoussourceip'}, 'iscontext': True}}}, {'operator': 'splitAndTrim', 'args': {'delimiter': {'value': {'simple': ','}}}}]}}, 'IPBlacklistMiner': {}}, 'separatecontext': True, 'loop': {'iscommand': False, 'exitCondition': '', 'wait': 1, 'max': 0}, 'view': '{\n  "position": {\n    "x": 10,\n    "y": 4520\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '72': {'id': '72', 'taskid': 'e9ca09c0-257f-4b66-82f9-e23bff61c711', 'type': 'regular', 'task': {'id': 'e9ca09c0-257f-4b66-82f9-e23bff61c711', 'version': -1, 'name': 'Generate travel map link', 'description': 'Creates a travel map link and saves it in the context.', 'scriptName': 'Set', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['96']}, 'scriptarguments': {'append': {}, 'key': {'simple': 'TravelMap'}, 'value': {'complex': {'root': 'inputs.DefaultMapLink', 'transformers': [{'operator': 'replace', 'args': {'limit': {}, 'replaceWith': {'value': {'simple': 'PreviousSourceIPGeo'}, 'iscontext': True}, 'toReplace': {'value': {'simple': 'SOURCE'}}}}, {'operator': 'replace', 'args': {'limit': {}, 'replaceWith': {'value': {'simple': 'SourceIPGeo'}, 'iscontext': True}, 'toReplace': {'value': {'simple': 'DESTINATION'}}}}, {'operator': 'replace', 'args': {'limit': {}, 'replaceWith': {'value': {'simple': '_'}}, 'toReplace': {'value': {'simple': ','}}}}]}}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -270,\n    "y": 1470\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '73': {'id': '73', 'taskid': '5dad711b-cb0e-44d6-8590-5c614f67f1ea', 'type': 'title', 'task': {'id': '5dad711b-cb0e-44d6-8590-5c614f67f1ea', 'version': -1, 'name': 'Process Travel Data', 'type': 'title', 'iscommand': False, 'brand': '', 'description': ''}, 'nexttasks': {'#none#': ['30', '72', '29']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -270,\n    "y": 1300\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '74': {'id': '74', 'taskid': '7c3addd4-ff4e-4a28-81e5-1638ff78ac08', 'type': 'condition', 'task': {'id': '7c3addd4-ff4e-4a28-81e5-1638ff78ac08', 'version': -1, 'name': 'Can the user be disabled automatically', 'description': 'Checks whether the user can be disabled automatically, as configured in the playbook inputs.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['75'], 'yes': ['95']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isEqualString', 'left': {'value': {'complex': {'root': 'inputs.AutomaticallyDisableUser'}}, 'iscontext': True}, 'right': {'value': {'simple': 'True'}}, 'ignorecase': True}]]}], 'view': '{\n  "position": {\n    "x": 300,\n    "y": 3580\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '75': {'id': '75', 'taskid': '34d2d123-14a3-4df9-86f1-7882efa15006', 'type': 'condition', 'task': {'id': '34d2d123-14a3-4df9-86f1-7882efa15006', 'version': -1, 'name': 'Get approval for disabling user', 'description': 'You should now contain the incident of the offending user. Please get approval to automatically disable the user account in Active Directory.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'Approved': ['95'], 'Unapproved': ['76']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 730,\n    "y": 3760\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '76': {'id': '76', 'taskid': '15285aa7-279f-436a-8a41-46798ef04b6f', 'type': 'regular', 'task': {'id': '15285aa7-279f-436a-8a41-46798ef04b6f', 'version': -1, 'name': 'Manually disable user account', 'description': 'Please take manual steps to disable the user account, or expire his or her password.', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['38']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 730,\n    "y": 4150\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '79': {'id': '79', 'taskid': 'f0a8d131-1f51-4c25-8b94-9cad739b12a3', 'type': 'regular', 'task': {'id': 'f0a8d131-1f51-4c25-8b94-9cad739b12a3', 'version': -1, 'name': 'Manually block IPs', 'description': 'Please take manual steps to block the offending IPs.', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['70']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 550,\n    "y": 4520\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '80': {'id': '80', 'taskid': '154d7a46-5386-460e-8910-1950ff1f720d', 'type': 'condition', 'task': {'id': '154d7a46-5386-460e-8910-1950ff1f720d', 'version': -1, 'name': 'Can the account be enriched', 'description': 'Checks whether there is a username for the offending user in context, and whether Active Directory v2 is enabled.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['51'], 'yes': ['81']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isExists', 'left': {'value': {'complex': {'root': 'modules', 'filters': [[{'operator': 'isEqualString', 'left': {'value': {'simple': 'brand'}, 'iscontext': True}, 'right': {'value': {'simple': 'Active Directory Query v2'}}}], [{'operator': 'isEqualString', 'left': {'value': {'simple': 'state'}, 'iscontext': True}, 'right': {'value': {'simple': 'active'}}}]]}}, 'iscontext': True}}], [{'operator': 'isExists', 'left': {'value': {'simple': 'incident.username'}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": 70,\n    "y": -90\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '81': {'id': '81', 'taskid': '37665c74-3bde-4e06-8e0a-a9af77d1cb53', 'type': 'regular', 'task': {'id': '37665c74-3bde-4e06-8e0a-a9af77d1cb53', 'version': -1, 'name': 'Enrich offending user account', 'description': 'Gets details about the offending username from Active Directory.', 'tags': ['userinfo'], 'script': '|||ad-get-user', 'type': 'regular', 'iscommand': True, 'brand': ''}, 'nexttasks': {'#none#': ['94']}, 'scriptarguments': {'attributes': {}, 'custom-field-data': {}, 'custom-field-type': {}, 'dn': {}, 'email': {}, 'limit': {}, 'name': {}, 'user-account-control-out': {}, 'username': {'complex': {'root': 'incident', 'accessor': 'username', 'transformers': [{'operator': 'uniq'}]}}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 70,\n    "y": 80\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '84': {'id': '84', 'taskid': 'b144d5df-6b2c-41d2-81f4-8de96a5259f9', 'type': 'condition', 'task': {'id': 'b144d5df-6b2c-41d2-81f4-8de96a5259f9', 'version': -1, 'name': 'Can the manager be contacted for travel approval', 'description': 'Checks whether an email address was retrieved for the manger of the offending user.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['68'], 'yes': ['86']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isNotEmpty', 'left': {'value': {'complex': {'root': 'UserManagerEmail'}}, 'iscontext': True}}], [{'operator': 'isEqualString', 'left': {'value': {'complex': {'root': 'inputs.ContactUserManager'}}, 'iscontext': True}, 'right': {'value': {'simple': 'True'}}, 'ignorecase': True}]]}], 'view': '{\n  "position": {\n    "x": 300,\n    "y": 2150\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '86': {'id': '86', 'taskid': '968c5886-7ee0-499c-8fd6-c656e6b6937f', 'type': 'regular', 'task': {'id': '968c5886-7ee0-499c-8fd6-c656e6b6937f', 'version': -1, 'name': 'Ask manager if travel was expected', 'description': 'Ask a user a question via email and process the reply directly into the investigation.', 'scriptName': 'EmailAskUser', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['87']}, 'scriptarguments': {'additionalOptions': {}, 'attachIds': {}, 'bcc': {}, 'bodyType': {}, 'cc': {}, 'email': {'complex': {'root': 'UserManagerEmail', 'transformers': [{'operator': 'uniq'}]}}, 'message': {'simple': 'User ${incident.username} traveled ${Geo.Distance} miles in ${Time.Difference} minutes. Was this an expected event'}, 'option1': {}, 'option2': {}, 'persistent': {}, 'playbookTaskID': {}, 'replyAddress': {}, 'replyEntriesTag': {}, 'retries': {}, 'roles': {}, 'subject': {'simple': 'User ${incident.username} is an impossible traveler!'}, 'task': {'simple': 'TravelQuestion'}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 590,\n    "y": 2340\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '87': {'id': '87', 'taskid': '994657de-7b7a-4897-874c-be24fddac9d8', 'type': 'condition', 'task': {'id': '994657de-7b7a-4897-874c-be24fddac9d8', 'version': -1, 'name': 'Get manager response', 'description': 'Gets a response from the manager as to whether the travel done by the user was expected. The response is received from the email reply that the manager sends.', 'tags': ['TravelQuestion'], 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'No': ['68'], 'yes': ['88']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 590,\n    "y": 2520\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '88': {'id': '88', 'taskid': 'b9ea26ae-e772-4b55-8223-f6fbe74a5427', 'type': 'regular', 'task': {'id': 'b9ea26ae-e772-4b55-8223-f6fbe74a5427', 'version': -1, 'name': 'Update incident details and set severity', 'description': 'Updates the incident details to say that the manager of the user approved the travel, and sets the incident severity to low.', 'script': 'Builtin|||setIncident', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'nexttasks': {'#none#': ['70']}, 'scriptarguments': {'addLabels': {}, 'affecteddata': {}, 'affecteddatatype': {}, 'affectedhosts': {}, 'affectedindividualscontactinformation': {}, 'affectedips': {}, 'app': {}, 'approximatenumberofaffecteddatasubjects': {}, 'assetid': {}, 'attachmentcount': {}, 'attachmentextension': {}, 'attachmenthash': {}, 'attachmentid': {}, 'attachmentitem': {}, 'attachmentname': {}, 'attachmentsize': {}, 'attachmenttype': {}, 'awsfindingid': {}, 'awsfindingtype': {}, 'awsinstanceid': {}, 'awsinstancename': {}, 'backupowner': {}, 'bugtraq': {}, 'campaigntargetcount': {}, 'campaigntargets': {}, 'city': {}, 'closeNotes': {}, 'closeReason': {}, 'companyaddress': {}, 'companycity': {}, 'companycountry': {}, 'companyhasinsuranceforthebreach': {}, 'companyname': {}, 'companypostalcode': {}, 'computername': {}, 'contactaddress': {}, 'contactname': {}, 'coordinates': {'complex': {'root': 'SourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'country': {}, 'countrywherebusinesshasitsmainestablishment': {}, 'countrywherethebreachtookplace': {}, 'criticalassets': {}, 'currentip': {}, 'customFields': {}, 'cve': {}, 'cvss': {}, 'dataencryptionstatus': {}, 'datetimeofthebreach': {}, 'daysbetweenreportcreation': {}, 'deleteEmptyField': {}, 'demoautomatedcondition': {}, 'demomanualcondition': {}, 'description': {}, 'dest': {}, 'destinationip': {}, 'destip': {}, 'destntdomain': {}, 'details': {'simple': 'The user logged in from two different locations within a reasonable time period.'}, 'detectedusers': {}, 'detectorid': {}, 'dpoemailaddress': {}, 'duration': {}, 'emailaddress': {}, 'emailauthenticitycheck': {}, 'emailbcc': {}, 'emailbody': {}, 'emailbodyformat': {}, 'emailbodyhtml': {}, 'emailcc': {}, 'emailclassification': {}, 'emailclientname': {}, 'emailfrom': {}, 'emailheaders': {}, 'emailhtml': {}, 'emailinreplyto': {}, 'emailkeywords': {}, 'emailmessageid': {}, 'emailreceived': {}, 'emailrecipient': {}, 'emailreplyto': {}, 'emailreturnpath': {}, 'emailsenderip': {}, 'emailsize': {}, 'emailsource': {}, 'emailsubject': {}, 'emailto': {}, 'emailtocount': {}, 'emailurlclicked': {}, 'endpointgrid': {}, 'epohost': {}, 'eposcanstatus': {}, 'eventid': {}, 'falses': {}, 'fetchid': {}, 'fetchtype': {}, 'filehash': {}, 'filename': {}, 'filepath': {}, 'findingid': {}, 'host': {}, 'hostid': {}, 'hostname': {}, 'htmlimage': {}, 'htmlrenderedimage': {}, 'id': {}, 'important': {}, 'importantfield': {}, 'infected': {}, 'internalip': {}, 'involvedusers': {}, 'isthedatasubjecttodpia': {}, 'jasontest': {}, 'labels': {}, 'likelyimpact': {}, 'maliciouscauseifthecauseisamaliciousattack': {}, 'malwarefamily': {}, 'mdtest': {}, 'measurestomitigate': {}, 'myfield': {}, 'name': {}, 'notes': {}, 'occurred': {}, 'owner': {}, 'phase': {'simple': 'No Response Needed (Legitimate Login)'}, 'phishingconfirmationstatus': {}, 'phishingsubtype': {}, 'possiblecauseofthebreach': {}, 'postalcode': {}, 'previouscoordinates': {'complex': {'root': 'PreviousSourceIPGeo', 'transformers': [{'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'previousip': {}, 'previoussignindatetime': {}, 'previoussourceip': {}, 'queue': {}, 'redlockpolicyname': {}, 'relateddomain': {}, 'replacePlaybook': {}, 'reporteduser': {}, 'reporteremailaddress': {}, 'reportingdepartment': {}, 'reportinguser': {}, 'requestor': {}, 'riskscore': {}, 'roles': {}, 'screenshot': {}, 'screenshot2': {}, 'sectorofaffectedparty': {}, 'securitygroupid': {}, 'selector': {}, 'serverip': {}, 'servername': {}, 'severity': {'simple': 'low'}, 'signature': {}, 'signindatetime': {}, 'single': {}, 'single2': {}, 'sizenumberofemployees': {}, 'sizeturnover': {}, 'sla': {}, 'slaField': {}, 'source': {}, 'sourceip': {}, 'src': {}, 'srcip': {}, 'srcntdomain': {}, 'srcuser': {}, 'systems': {}, 'telephoneno': {}, 'test': {}, 'test2': {}, 'testfield': {}, 'timeassignedtolevel2': {}, 'timefield1': {}, 'timelevel1': {}, 'travelmaplink': {'complex': {'root': 'TravelMap', 'transformers': [{'operator': 'uniq'}]}}, 'type': {}, 'urlsslverification': {}, 'user': {}, 'username': {}, 'vendorid': {}, 'vendorproduct': {}, 'vulnerabilitycategory': {}, 'whereisdatahosted': {}, 'whitelistrequest': {}, 'xdr': {}, 'xdralertcount': {}, 'xdralerts': {}, 'xdrassigneduseremail': {}, 'xdrassigneduserprettyname': {}, 'xdrdescription': {}, 'xdrdetectiontime': {}, 'xdrfileartifacts': {}, 'xdrhighseverityalertcount': {}, 'xdrincidentid': {}, 'xdrlowseverityalertcount': {}, 'xdrmediumseverityalertcount': {}, 'xdrnetworkartifacts': {}, 'xdrnotes': {}, 'xdrresolvecomment': {}, 'xdrstatus': {}, 'xdrurl': {}, 'xdrusercount': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 940,\n    "y": 2800\n  }\n}', 'note': False, 'timertriggers': [{'fieldname': 'detectionsla', 'action': 'stop'}], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '89': {'id': '89', 'taskid': '354bc65e-950f-4ba9-8771-4953ae438540', 'type': 'regular', 'task': {'id': '354bc65e-950f-4ba9-8771-4953ae438540', 'version': -1, 'name': 'Create travel map image', 'description': 'Converts the contents of a URL to an image file or a PDF file.', 'script': '|||rasterize', 'type': 'regular', 'iscommand': True, 'brand': ''}, 'nexttasks': {'#none#': ['63']}, 'scriptarguments': {'height': {}, 'type': {}, 'url': {'complex': {'root': 'TravelMap', 'transformers': [{'operator': 'uniq'}]}}, 'wait_time': {'simple': '15'}, 'width': {}}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -500,\n    "y": 1800\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '90': {'id': '90', 'taskid': '290f01c1-5e82-4d10-890e-250d669ab805', 'type': 'condition', 'task': {'id': '290f01c1-5e82-4d10-890e-250d669ab805', 'version': -1, 'name': 'Is there a country for the source IP', 'description': 'Checks if there is a country associated with the source IP address.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['51'], 'yes': ['92']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isExists', 'left': {'value': {'complex': {'root': 'IP', 'filters': [[{'operator': 'isNotEmpty', 'left': {'value': {'simple': 'IP.Geo.Country'}, 'iscontext': True}}]], 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.sourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Country'}}}}, {'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": 1200,\n    "y": -90\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '91': {'id': '91', 'taskid': 'e5bac47f-93ef-4aae-89f0-3220a9b32ee2', 'type': 'condition', 'task': {'id': 'e5bac47f-93ef-4aae-89f0-3220a9b32ee2', 'version': -1, 'name': 'Is there a country for the previous source IP', 'description': 'Checks if there is a country associated with the previous source IP address.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['51'], 'yes': ['93']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isExists', 'left': {'value': {'complex': {'root': 'IP', 'filters': [[{'operator': 'isNotEmpty', 'left': {'value': {'simple': 'IP.Geo.Country'}, 'iscontext': True}}]], 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.previoussourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Country'}}}}, {'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": 730,\n    "y": -90\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '92': {'id': '92', 'taskid': '879713f5-f8e3-4a31-8704-0223c0764c1b', 'type': 'regular', 'task': {'id': '879713f5-f8e3-4a31-8704-0223c0764c1b', 'version': -1, 'name': 'Update incident details with source country', 'description': 'Updates the incident details with the country from which the user logged in.', 'script': 'Builtin|||setIncident', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'nexttasks': {'#none#': ['51']}, 'scriptarguments': {'account': {}, 'accountid': {}, 'addLabels': {}, 'affecteddata': {}, 'affecteddatatype': {}, 'affectedindividualscontactinformation': {}, 'agentid': {}, 'app': {}, 'approximatenumberofaffecteddatasubjects': {}, 'assetid': {}, 'attachmentcount': {}, 'attachmentextension': {}, 'attachmenthash': {}, 'attachmentid': {}, 'attachmentname': {}, 'attachmentsize': {}, 'attachmenttype': {}, 'blockedaction': {}, 'bugtraq': {}, 'city': {}, 'closeNotes': {}, 'closeReason': {}, 'commandline': {}, 'companyaddress': {}, 'companycity': {}, 'companycountry': {}, 'companyhasinsuranceforthebreach': {}, 'companyname': {}, 'companypostalcode': {}, 'contactaddress': {}, 'contactname': {}, 'coordinates': {}, 'country': {'complex': {'root': 'IP', 'filters': [[{'operator': 'isNotEmpty', 'left': {'value': {'simple': 'IP.Geo.Country'}, 'iscontext': True}}]], 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.sourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Country'}}}}, {'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'countrywherebusinesshasitsmainestablishment': {}, 'countrywherethebreachtookplace': {}, 'criticalassets': {}, 'customFields': {}, 'cve': {}, 'dataencryptionstatus': {}, 'datetimeofthebreach': {}, 'deleteEmptyField': {}, 'dest': {}, 'destinationip': {}, 'destntdomain': {}, 'details': {}, 'detectionendtime': {}, 'detectionid': {}, 'detectionticketed': {}, 'detectionupdatetime': {}, 'detectionurl': {}, 'devicename': {}, 'dpoemailaddress': {}, 'duration': {}, 'emailaddress': {}, 'emailauthenticitycheck': {}, 'emailbcc': {}, 'emailbody': {}, 'emailbodyformat': {}, 'emailbodyhtml': {}, 'emailcc': {}, 'emailclassification': {}, 'emailclientname': {}, 'emailfrom': {}, 'emailheaders': {}, 'emailhtml': {}, 'emailinreplyto': {}, 'emailkeywords': {}, 'emailmessageid': {}, 'emailreceived': {}, 'emailreplyto': {}, 'emailreturnpath': {}, 'emailsenderip': {}, 'emailsize': {}, 'emailsource': {}, 'emailsubject': {}, 'emailto': {}, 'emailtocount': {}, 'emailurlclicked': {}, 'extrahopapplianceid': {}, 'extrahophostname': {}, 'filehash': {}, 'filename': {}, 'filepath': {}, 'filesize': {}, 'firstseen': {}, 'id': {}, 'infectedhosts': {}, 'isolated': {}, 'isthedatasubjecttodpia': {}, 'labels': {}, 'lastmodifiedby': {}, 'lastmodifiedon': {}, 'lastseen': {}, 'likelyimpact': {}, 'maliciousbehavior': {}, 'maliciouscauseifthecauseisamaliciousattack': {}, 'measurestomitigate': {}, 'name': {}, 'occurred': {}, 'owner': {}, 'parentprocessid': {}, 'participants': {}, 'phase': {}, 'phishingsubtype': {}, 'pid': {}, 'policydeleted': {}, 'policydescription': {}, 'policydetails': {}, 'policyid': {}, 'policyrecommendation': {}, 'policyremediable': {}, 'policyseverity': {}, 'policytype': {}, 'possiblecauseofthebreach': {}, 'postalcode': {}, 'previouscoordinates': {}, 'previoussignindatetime': {}, 'previoussourceip': {}, 'prismacloudid': {}, 'prismacloudreason': {}, 'prismacloudrules': {}, 'prismacloudstatus': {}, 'prismacloudtime': {}, 'rating': {}, 'rawparticipants': {}, 'region': {}, 'regionid': {}, 'replacePlaybook': {}, 'reporteremailaddress': {}, 'resourceapiname': {}, 'resourcecloudtype': {}, 'resourceid': {}, 'resourcename': {}, 'resourcetype': {}, 'riskrating': {}, 'riskscore': {}, 'roles': {}, 'rrn': {}, 'sectorofaffectedparty': {}, 'severity': {}, 'signature': {}, 'signindatetime': {}, 'sizenumberofemployees': {}, 'sizeturnover': {}, 'skuname': {}, 'skutier': {}, 'sla': {}, 'slaField': {}, 'sourceip': {}, 'src': {}, 'srcntdomain': {}, 'srcos': {}, 'srcuser': {}, 'subscriptionassignedby': {}, 'subscriptioncreatedby': {}, 'subscriptioncreatedon': {}, 'subscriptiondescription': {}, 'subscriptionid': {}, 'subscriptionname': {}, 'subscriptiontype': {}, 'subscriptionupdatedby': {}, 'subscriptionupdatedon': {}, 'subtype': {}, 'systemdefault': {}, 'systems': {}, 'telephoneno': {}, 'terminatedaction': {}, 'trapsid': {}, 'travelmaplink': {}, 'triggeredsecurityprofile': {}, 'type': {}, 'urlsslverification': {}, 'user': {}, 'username': {}, 'vendorid': {}, 'vendorproduct': {}, 'vpcid': {}, 'vulnerabilitycategory': {}, 'whereisdatahosted': {}, 'xdralertcount': {}, 'xdralerts': {}, 'xdrassigneduseremail': {}, 'xdrassigneduserprettyname': {}, 'xdrdescription': {}, 'xdrdetectiontime': {}, 'xdrfileartifacts': {}, 'xdrhighseverityalertcount': {}, 'xdrincidentid': {}, 'xdrlowseverityalertcount': {}, 'xdrmediumseverityalertcount': {}, 'xdrnetworkartifacts': {}, 'xdrnotes': {}, 'xdrresolvecomment': {}, 'xdrstatus': {}, 'xdrurl': {}, 'xdrusercount': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 1200,\n    "y": 145\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '93': {'id': '93', 'taskid': '050e413d-74f0-46e7-8c07-502e88f1a5d1', 'type': 'regular', 'task': {'id': '050e413d-74f0-46e7-8c07-502e88f1a5d1', 'version': -1, 'name': 'Update incident details with previous source country', 'description': 'Updates the incident details with the country from which the user previously logged in.', 'script': 'Builtin|||setIncident', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'nexttasks': {'#none#': ['51']}, 'scriptarguments': {'account': {}, 'accountid': {}, 'addLabels': {}, 'affecteddata': {}, 'affecteddatatype': {}, 'affectedindividualscontactinformation': {}, 'agentid': {}, 'app': {}, 'approximatenumberofaffecteddatasubjects': {}, 'assetid': {}, 'attachmentcount': {}, 'attachmentextension': {}, 'attachmenthash': {}, 'attachmentid': {}, 'attachmentname': {}, 'attachmentsize': {}, 'attachmenttype': {}, 'blockedaction': {}, 'bugtraq': {}, 'city': {}, 'closeNotes': {}, 'closeReason': {}, 'commandline': {}, 'companyaddress': {}, 'companycity': {}, 'companycountry': {}, 'companyhasinsuranceforthebreach': {}, 'companyname': {}, 'companypostalcode': {}, 'contactaddress': {}, 'contactname': {}, 'coordinates': {}, 'country': {}, 'countrywherebusinesshasitsmainestablishment': {}, 'countrywherethebreachtookplace': {}, 'criticalassets': {}, 'customFields': {}, 'cve': {}, 'dataencryptionstatus': {}, 'datetimeofthebreach': {}, 'deleteEmptyField': {}, 'dest': {}, 'destinationip': {}, 'destntdomain': {}, 'details': {}, 'detectionendtime': {}, 'detectionid': {}, 'detectionticketed': {}, 'detectionupdatetime': {}, 'detectionurl': {}, 'devicename': {}, 'dpoemailaddress': {}, 'duration': {}, 'emailaddress': {}, 'emailauthenticitycheck': {}, 'emailbcc': {}, 'emailbody': {}, 'emailbodyformat': {}, 'emailbodyhtml': {}, 'emailcc': {}, 'emailclassification': {}, 'emailclientname': {}, 'emailfrom': {}, 'emailheaders': {}, 'emailhtml': {}, 'emailinreplyto': {}, 'emailkeywords': {}, 'emailmessageid': {}, 'emailreceived': {}, 'emailreplyto': {}, 'emailreturnpath': {}, 'emailsenderip': {}, 'emailsize': {}, 'emailsource': {}, 'emailsubject': {}, 'emailto': {}, 'emailtocount': {}, 'emailurlclicked': {}, 'extrahopapplianceid': {}, 'extrahophostname': {}, 'filehash': {}, 'filename': {}, 'filepath': {}, 'filesize': {}, 'firstseen': {}, 'id': {}, 'infectedhosts': {}, 'isolated': {}, 'isthedatasubjecttodpia': {}, 'labels': {}, 'lastmodifiedby': {}, 'lastmodifiedon': {}, 'lastseen': {}, 'likelyimpact': {}, 'maliciousbehavior': {}, 'maliciouscauseifthecauseisamaliciousattack': {}, 'measurestomitigate': {}, 'name': {}, 'occurred': {}, 'owner': {}, 'parentprocessid': {}, 'participants': {}, 'phase': {}, 'phishingsubtype': {}, 'pid': {}, 'policydeleted': {}, 'policydescription': {}, 'policydetails': {}, 'policyid': {}, 'policyrecommendation': {}, 'policyremediable': {}, 'policyseverity': {}, 'policytype': {}, 'possiblecauseofthebreach': {}, 'postalcode': {}, 'previouscoordinates': {}, 'previouscountry': {'complex': {'root': 'IP', 'filters': [[{'operator': 'isNotEmpty', 'left': {'value': {'simple': 'IP.Geo.Country'}, 'iscontext': True}}]], 'transformers': [{'operator': 'WhereFieldEquals', 'args': {'equalTo': {'value': {'simple': 'incident.previoussourceip'}, 'iscontext': True}, 'field': {'value': {'simple': 'Address'}}, 'getField': {'value': {'simple': 'Geo'}}}}, {'operator': 'getField', 'args': {'field': {'value': {'simple': 'Country'}}}}, {'operator': 'uniq'}, {'operator': 'atIndex', 'args': {'index': {'value': {'simple': '0'}}}}]}}, 'previoussignindatetime': {}, 'previoussourceip': {}, 'prismacloudid': {}, 'prismacloudreason': {}, 'prismacloudrules': {}, 'prismacloudstatus': {}, 'prismacloudtime': {}, 'rating': {}, 'rawparticipants': {}, 'region': {}, 'regionid': {}, 'replacePlaybook': {}, 'reporteremailaddress': {}, 'resourceapiname': {}, 'resourcecloudtype': {}, 'resourceid': {}, 'resourcename': {}, 'resourcetype': {}, 'riskrating': {}, 'riskscore': {}, 'roles': {}, 'rrn': {}, 'sectorofaffectedparty': {}, 'severity': {}, 'signature': {}, 'signindatetime': {}, 'sizenumberofemployees': {}, 'sizeturnover': {}, 'skuname': {}, 'skutier': {}, 'sla': {}, 'slaField': {}, 'sourceip': {}, 'src': {}, 'srcntdomain': {}, 'srcos': {}, 'srcuser': {}, 'subscriptionassignedby': {}, 'subscriptioncreatedby': {}, 'subscriptioncreatedon': {}, 'subscriptiondescription': {}, 'subscriptionid': {}, 'subscriptionname': {}, 'subscriptiontype': {}, 'subscriptionupdatedby': {}, 'subscriptionupdatedon': {}, 'subtype': {}, 'systemdefault': {}, 'systems': {}, 'telephoneno': {}, 'terminatedaction': {}, 'trapsid': {}, 'travelmaplink': {}, 'triggeredsecurityprofile': {}, 'type': {}, 'urlsslverification': {}, 'user': {}, 'username': {}, 'vendorid': {}, 'vendorproduct': {}, 'vpcid': {}, 'vulnerabilitycategory': {}, 'whereisdatahosted': {}, 'xdralertcount': {}, 'xdralerts': {}, 'xdrassigneduseremail': {}, 'xdrassigneduserprettyname': {}, 'xdrdescription': {}, 'xdrdetectiontime': {}, 'xdrfileartifacts': {}, 'xdrhighseverityalertcount': {}, 'xdrincidentid': {}, 'xdrlowseverityalertcount': {}, 'xdrmediumseverityalertcount': {}, 'xdrnetworkartifacts': {}, 'xdrnotes': {}, 'xdrresolvecomment': {}, 'xdrstatus': {}, 'xdrurl': {}, 'xdrusercount': {}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 730,\n    "y": 145\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '94': {'id': '94', 'taskid': 'b1de0ac1-d045-40f3-8def-512ad3c9be0d', 'type': 'playbook', 'task': {'id': 'b1de0ac1-d045-40f3-8def-512ad3c9be0d', 'version': -1, 'name': 'Active Directory - Get User Manager Details', 'description': "Takes an email address or a username of a user account in Active Directory, and returns the email address of the user's manager.", 'playbookName': 'Active Directory - Get User Manager Details', 'type': 'playbook', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['51']}, 'scriptarguments': {'UserEmail': {}, 'Username': {'complex': {'root': 'incident', 'accessor': 'username'}}}, 'separatecontext': True, 'loop': {'iscommand': False, 'exitCondition': '', 'wait': 1, 'max': 0}, 'view': '{\n  "position": {\n    "x": 70,\n    "y": 230\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': True, 'quietmode': 0}, '95': {'id': '95', 'taskid': 'ca38e4df-48b7-40a9-8cc3-8248b7ca5743', 'type': 'condition', 'task': {'id': 'ca38e4df-48b7-40a9-8cc3-8248b7ca5743', 'version': -1, 'name': 'Is Active Directory enabled', 'description': 'Checks whether the Active Directory Query v2 integration is enabled.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['76'], 'yes': ['34']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isExists', 'left': {'value': {'complex': {'root': 'modules', 'filters': [[{'operator': 'isEqualString', 'left': {'value': {'simple': 'brand'}, 'iscontext': True}, 'right': {'value': {'simple': 'Active Directory Query v2'}}}], [{'operator': 'isEqualString', 'left': {'value': {'simple': 'state'}, 'iscontext': True}, 'right': {'value': {'simple': 'active'}}}]]}}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": 300,\n    "y": 3945\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}, '96': {'id': '96', 'taskid': 'a4857973-adc0-4a7f-884d-271532c50b08', 'type': 'condition', 'task': {'id': 'a4857973-adc0-4a7f-884d-271532c50b08', 'version': -1, 'name': 'Is Rasterize enabled', 'description': 'Checks whether the Rasterize integration is enabled.', 'type': 'condition', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#default#': ['63'], 'yes': ['89']}, 'separatecontext': False, 'conditions': [{'label': 'yes', 'condition': [[{'operator': 'isExists', 'left': {'value': {'complex': {'root': 'modules', 'filters': [[{'operator': 'isEqualString', 'left': {'value': {'simple': 'modules.brand'}, 'iscontext': True}, 'right': {'value': {'simple': 'Rasterize'}}}], [{'operator': 'isEqualString', 'left': {'value': {'simple': 'modules.state'}, 'iscontext': True}, 'right': {'value': {'simple': 'active'}}}]]}}, 'iscontext': True}}]]}], 'view': '{\n  "position": {\n    "x": -270,\n    "y": 1620\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False, 'skipunavailable': False, 'quietmode': 0}}, 'view': '{\n  "linkLabelsPosition": {\n    "38_71_yes": 0.35,\n    "52_54_#default#": 0.43,\n    "52_58_yes": 0.84,\n    "52_59_yes": 0.9,\n    "63_66_#default#": 0.18,\n    "67_32_#default#": 0.44,\n    "67_69_yes": 0.76,\n    "68_32_#default#": 0.25,\n    "68_67_yes": 0.42,\n    "74_75_#default#": 0.33,\n    "74_95_yes": 0.48,\n    "75_76_Unapproved": 0.42,\n    "80_51_#default#": 0.33,\n    "80_81_yes": 0.56,\n    "84_86_yes": 0.44,\n    "87_68_No": 0.29,\n    "90_51_#default#": 0.21,\n    "90_92_yes": 0.46,\n    "91_51_#default#": 0.1,\n    "91_93_yes": 0.51,\n    "95_34_yes": 0.46,\n    "96_63_#default#": 0.31,\n    "96_89_yes": 0.52\n  },\n  "paper": {\n    "dimensions": {\n      "height": 5475,\n      "width": 3000,\n      "x": -940,\n      "y": -560\n    }\n  }\n}', 'inputs': [{'key': 'MaxMilesPerHourAllowed', 'value': {'simple': '600'}, 'required': False, 'description': 'The maximum miles per hour that is still considered reasonable. If the geographical distance and difference in time between logins is greater than this value, the user will be considered an impossible traveler.', 'playbookInputQuery': None}, {'key': 'WhitelistedIPs', 'value': {}, 'required': False, 'description': 'CSV of IP addresses that are allowed to be used across long distances.', 'playbookInputQuery': None}, {'key': 'AutomaticallyBlockIPs', 'value': {'simple': 'False'}, 'required': False, 'description': 'Whether to automatically block the source IPs that the login originated from. Can be False or True.', 'playbookInputQuery': None}, {'key': 'DefaultMapLink', 'value': {'simple': 'https://bing.com/maps/default.aspxrtp=pos.SOURCE~pos.DESTINATION'}, 'required': False, 'description': 'The default link from which to create a travel map. The "SOURCE" and "DESTINATION" words are replaced with the previous coordinates and current coordinates of the traveler, respectively.', 'playbookInputQuery': None}, {'key': 'AutomaticallyDisableUser', 'value': {'simple': 'False'}, 'required': False, 'description': 'Whether to automatically disable the impossible traveler account using Active Directory.', 'playbookInputQuery': None}, {'key': 'ContactUserManager', 'value': {'simple': 'False'}, 'required': False, 'description': 'Whether to ask the user manager for the legitimacy of the login events, in case of an alleged impossible traveler.', 'playbookInputQuery': None}], 'outputs': [{'contextPath': 'Account.Email.Address', 'description': 'The email address object associated with the Account', 'type': 'string'}, {'contextPath': 'DBotScore', 'description': 'Indicator, Score, Type, Vendor', 'type': 'unknown'}, {'contextPath': 'Account.ID', 'description': 'The unique Account DN (Distinguished Name)', 'type': 'string'}, {'contextPath': 'Account.Username', 'description': 'The Account username', 'type': 'string'}, {'contextPath': 'Account.Email', 'description': 'The email address associated with the Account'}, {'contextPath': 'Account.Type', 'description': 'Type of the Account entity', 'type': 'string'}, {'contextPath': 'Account.Groups', 'description': 'The groups the Account is a part of'}, {'contextPath': 'Account', 'description': 'Account object', 'type': 'unknown'}, {'contextPath': 'Account.DisplayName', 'description': 'The Account display name', 'type': 'string'}, {'contextPath': 'Account.Manager', 'description': "The Account's manager", 'type': 'string'}, {'contextPath': 'DBotScore.Indicator', 'description': 'The indicator value', 'type': 'string'}, {'contextPath': 'DBotScore.Type', 'description': "The indicator's type", 'type': 'string'}, {'contextPath': 'DBotScore.Vendor', 'description': "The indicator's vendor", 'type': 'string'}, {'contextPath': 'DBotScore.Score', 'description': "The indicator's score", 'type': 'number'}, {'contextPath': 'IP', 'description': 'The IP objects', 'type': 'unknown'}, {'contextPath': 'Endpoint', 'description': "The Endpoint's object", 'type': 'unknown'}, {'contextPath': 'Endpoint.Hostname', 'description': 'The hostname to enrich', 'type': 'string'}, {'contextPath': 'Endpoint.OS', 'description': 'Endpoint OS', 'type': 'string'}, {'contextPath': 'Endpoint.IP', 'description': 'List of endpoint IP addresses'}, {'contextPath': 'Endpoint.MAC', 'description': 'List of endpoint MAC addresses'}, {'contextPath': 'Endpoint.Domain', 'description': 'Endpoint domain name', 'type': 'string'}], 'fromversion': '5.0.0', 'tests': ['Impossible Traveler - Test']}
    test_playbook = {'id': 'Impossible Traveler - Test', 'version': -1, 'fromversion': '5.0.0', 'name': 'Impossible Traveler - Test', 'starttaskid': '0', 'tasks': {'0': {'id': '0', 'taskid': 'ee333755-7738-48f1-8adc-552a535ae108', 'type': 'start', 'task': {'id': 'ee333755-7738-48f1-8adc-552a535ae108', 'version': -1, 'name': '', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['3']}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 450,\n    "y": 70\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False}, '2': {'id': '2', 'taskid': '02e90978-27c5-4e96-8b10-6abbf5d406f9', 'type': 'regular', 'task': {'id': '02e90978-27c5-4e96-8b10-6abbf5d406f9', 'version': -1, 'name': 'Set impossible traveler data', 'script': 'Builtin|||setIncident', 'type': 'regular', 'iscommand': True, 'brand': 'Builtin'}, 'nexttasks': {'#none#': ['9', '10', '11']}, 'scriptarguments': {'addLabels': {}, 'affecteddata': {}, 'affecteddatatype': {}, 'affectedhosts': {}, 'affectedindividualscontactinformation': {}, 'affectedips': {}, 'app': {}, 'approximatenumberofaffecteddatasubjects': {}, 'assetid': {}, 'attachmentcount': {}, 'attachmentextension': {}, 'attachmenthash': {}, 'attachmentid': {}, 'attachmentitem': {}, 'attachmentname': {}, 'attachmentsize': {}, 'attachmenttype': {}, 'backupowner': {}, 'bugtraq': {}, 'campaigntargetcount': {}, 'campaigntargets': {}, 'city': {}, 'closeNotes': {}, 'closeReason': {}, 'companyaddress': {}, 'companycity': {}, 'companycountry': {}, 'companyhasinsuranceforthebreach': {}, 'companyname': {}, 'companypostalcode': {}, 'contactaddress': {}, 'contactname': {}, 'coordinates': {}, 'country': {}, 'countrywherebusinesshasitsmainestablishment': {}, 'countrywherethebreachtookplace': {}, 'criticalassets': {}, 'customFields': {}, 'cve': {}, 'cvss': {}, 'dataencryptionstatus': {}, 'datetimeofthebreach': {}, 'daysbetweenreportcreation': {}, 'deleteEmptyField': {}, 'dest': {}, 'destinationip': {'simple': '31.177.34.128'}, 'destntdomain': {}, 'details': {}, 'detectedusers': {}, 'dpoemailaddress': {}, 'duration': {}, 'emailaddress': {}, 'emailauthenticitycheck': {}, 'emailbcc': {}, 'emailbody': {}, 'emailbodyformat': {}, 'emailbodyhtml': {}, 'emailcc': {}, 'emailclassification': {}, 'emailclientname': {}, 'emailfrom': {}, 'emailfromdisplayname': {}, 'emailheaders': {}, 'emailhtml': {}, 'emailinreplyto': {}, 'emailkeywords': {}, 'emailmessageid': {}, 'emailreceived': {}, 'emailreplyto': {}, 'emailreturnpath': {}, 'emailsenderdomain': {}, 'emailsenderip': {}, 'emailsize': {}, 'emailsource': {}, 'emailsubject': {}, 'emailsubjectlanguage': {}, 'emailto': {}, 'emailtocount': {}, 'emailurlclicked': {}, 'eventid': {}, 'falses': {}, 'fetchid': {}, 'fetchtype': {}, 'filehash': {}, 'filename': {}, 'filepath': {}, 'hostid': {}, 'hostname': {}, 'htmlimage': {}, 'htmlrenderedimage': {}, 'id': {}, 'important': {}, 'importantfield': {}, 'isthedatasubjecttodpia': {}, 'labels': {}, 'likelyimpact': {}, 'maliciouscauseifthecauseisamaliciousattack': {}, 'malwarefamily': {}, 'mdtest': {}, 'measurestomitigate': {}, 'myfield': {}, 'name': {}, 'occurred': {}, 'owner': {}, 'phase': {}, 'phishingsubtype': {}, 'possiblecauseofthebreach': {}, 'postalcode': {}, 'previouscoordinates': {}, 'previoussignindatetime': {'simple': 'datetime.datetime(2019, 10, 31, 11, 49, 0, 989403, tzinfo=datetime.timezone.utc)'}, 'previoussourceip': {'simple': '104.196.188.170'}, 'relateddomain': {}, 'replacePlaybook': {}, 'reporteduser': {}, 'reporteremailaddress': {}, 'reportinguser': {}, 'roles': {}, 'screenshot': {}, 'screenshot2': {}, 'sectorofaffectedparty': {}, 'selector': {}, 'severity': {}, 'signature': {}, 'signindatetime': {'simple': 'datetime.datetime(2019, 10, 31, 11, 55, 0, 989403, tzinfo=datetime.timezone.utc)'}, 'single': {}, 'single2': {}, 'sizenumberofemployees': {}, 'sizeturnover': {}, 'sla': {}, 'slaField': {}, 'source': {}, 'sourceip': {'simple': '176.10.104.240'}, 'src': {}, 'srcntdomain': {}, 'srcuser': {}, 'systems': {}, 'telephoneno': {}, 'test': {}, 'test2': {}, 'testfield': {}, 'timeassignedtolevel2': {}, 'timefield1': {}, 'timelevel1': {}, 'type': {}, 'urlsslverification': {}, 'user': {}, 'username': {'simple': 'donotdelete'}, 'vendorid': {}, 'vendorproduct': {}, 'vulnerabilitycategory': {}, 'whereisdatahosted': {}, 'xdr': {}, 'xdralertcount': {}, 'xdralerts': {}, 'xdrassigneduseremail': {}, 'xdrassigneduserprettyname': {}, 'xdrdescription': {}, 'xdrdetectiontime': {}, 'xdrfileartifacts': {}, 'xdrhighseverityalertcount': {}, 'xdrincidentid': {}, 'xdrlowseverityalertcount': {}, 'xdrmediumseverityalertcount': {}, 'xdrnetworkartifacts': {}, 'xdrnotes': {}, 'xdrresolvecomment': {}, 'xdrstatus': {}, 'xdrurl': {}, 'xdrusercount': {}}, 'reputationcalc': 2, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 450,\n    "y": 370\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False}, '3': {'id': '3', 'taskid': '615ff182-d323-43c5-8958-7aa393d6d058', 'type': 'regular', 'task': {'id': '615ff182-d323-43c5-8958-7aa393d6d058', 'version': -1, 'name': 'Delete context', 'description': 'Delete field from context', 'scriptName': 'DeleteContext', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['2']}, 'scriptarguments': {'all': {'simple': 'yes'}, 'index': {}, 'key': {}, 'keysToKeep': {}, 'subplaybook': {}}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 450,\n    "y": 210\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False}, '7': {'id': '7', 'taskid': 'c129e988-4dc1-4886-8a99-62b88c42f943', 'type': 'title', 'task': {'id': 'c129e988-4dc1-4886-8a99-62b88c42f943', 'version': -1, 'name': 'Done', 'type': 'title', 'iscommand': False, 'brand': ''}, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 450,\n    "y": 760\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False}, '9': {'id': '9', 'taskid': 'c2c80c34-9f64-49b1-8284-604ecd4a8297', 'type': 'regular', 'task': {'id': 'c2c80c34-9f64-49b1-8284-604ecd4a8297', 'version': -1, 'name': 'Automatically unapprove user disable', 'description': 'Schedule a command to run inside the war room at a future time (once or reoccurring)', 'scriptName': 'ScheduleCommand', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['7']}, 'scriptarguments': {'command': {'simple': '!CompleteManualTask id=${incident.id} type=condition closing_option=UNAPPROVED'}, 'cron': {'simple': '*/1 * * * *'}, 'endDate': {}, 'times': {'simple': '10'}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": 880,\n    "y": 540\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False}, '10': {'id': '10', 'taskid': '21c43a27-3352-4272-8093-cea11b552409', 'type': 'regular', 'task': {'id': '21c43a27-3352-4272-8093-cea11b552409', 'version': -1, 'name': 'Automatically close manual investigation', 'description': 'Schedule a command to run inside the war room at a future time (once or reoccurring)', 'scriptName': 'ScheduleCommand', 'type': 'regular', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['7']}, 'scriptarguments': {'command': {'simple': '!CompleteManualTask id=${incident.id}'}, 'cron': {'simple': '*/2 * * * *'}, 'endDate': {}, 'times': {'simple': '10'}}, 'reputationcalc': 1, 'separatecontext': False, 'view': '{\n  "position": {\n    "x": -10,\n    "y": 540\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False}, '11': {'id': '11', 'taskid': '6b822678-dc93-4f5d-839b-a89697413e86', 'type': 'playbook', 'task': {'id': '6b822678-dc93-4f5d-839b-a89697413e86', 'version': -1, 'name': 'Impossible Traveler', 'playbookName': 'Impossible Traveler', 'type': 'playbook', 'iscommand': False, 'brand': ''}, 'nexttasks': {'#none#': ['7']}, 'separatecontext': True, 'view': '{\n  "position": {\n    "x": 450,\n    "y": 560\n  }\n}', 'note': False, 'timertriggers': [], 'ignoreworker': False}}, 'view': '{\n  "linkLabelsPosition": {},\n  "paper": {\n    "dimensions": {\n      "height": 755,\n      "width": 1270,\n      "x": -10,\n      "y": 70\n    }\n  }\n}', 'inputs': [], 'outputs': []}
    layout = {'TypeName': 'Impossible Traveler', 'kind': 'details', 'fromVersion': '5.0.0', 'layout': {'TypeName': '', 'id': 'Impossible Traveler', 'kind': 'details', 'modified': '2019-11-17T14:58:53.435100789Z', 'name': '', 'system': False, 'tabs': [{'id': 'caseinfoid', 'name': 'Incident Info', 'sections': [{'displayType': 'ROW', 'h': 2, 'i': 'caseinfoid-fce71720-98b0-11e9-97d7-ed26ef9e46c8', 'isVisible': True, 'items': [{'endCol': 2, 'fieldId': 'type', 'height': 24, 'id': 'incident-type-field', 'index': 0, 'startCol': 0}, {'endCol': 2, 'fieldId': 'severity', 'height': 24, 'id': 'incident-severity-field', 'index': 1, 'startCol': 0}, {'endCol': 2, 'fieldId': 'owner', 'height': 24, 'id': 'incident-owner-field', 'index': 2, 'startCol': 0}, {'endCol': 2, 'fieldId': 'dbotsource', 'height': 24, 'id': 'incident-source-field', 'index': 3, 'startCol': 0}, {'endCol': 2, 'fieldId': 'sourcebrand', 'height': 24, 'id': 'incident-sourceBrand-field', 'index': 4, 'startCol': 0}, {'endCol': 2, 'fieldId': 'sourceinstance', 'height': 24, 'id': 'incident-sourceInstance-field', 'index': 5, 'startCol': 0}, {'endCol': 2, 'fieldId': 'playbookid', 'height': 24, 'id': 'incident-playbookId-field', 'index': 6, 'startCol': 0}], 'moved': False, 'name': 'Case Details', 'static': False, 'w': 1, 'x': 0, 'y': 0}, {'h': 2, 'i': 'caseinfoid-61263cc0-98b1-11e9-97d7-ed26ef9e46c8', 'moved': False, 'name': 'Notes', 'static': False, 'type': 'notes', 'w': 1, 'x': 2, 'y': 0}, {'displayType': 'ROW', 'h': 2, 'i': 'caseinfoid-6aabad20-98b1-11e9-97d7-ed26ef9e46c8', 'moved': False, 'name': 'Work Plan', 'static': False, 'type': 'workplan', 'w': 1, 'x': 1, 'y': 0}, {'displayType': 'ROW', 'h': 2, 'i': 'caseinfoid-770ec200-98b1-11e9-97d7-ed26ef9e46c8', 'isVisible': True, 'moved': False, 'name': 'Linked Incidents', 'static': False, 'type': 'linkedIncidents', 'w': 1, 'x': 1, 'y': 4}, {'displayType': 'ROW', 'h': 2, 'i': 'caseinfoid-842632c0-98b1-11e9-97d7-ed26ef9e46c8', 'moved': False, 'name': 'Child Incidents', 'static': False, 'type': 'childInv', 'w': 1, 'x': 2, 'y': 4}, {'displayType': 'ROW', 'h': 2, 'i': 'caseinfoid-4a31afa0-98ba-11e9-a519-93a53c759fe0', 'moved': False, 'name': 'Evidence', 'static': False, 'type': 'evidence', 'w': 1, 'x': 2, 'y': 2}, {'displayType': 'ROW', 'h': 2, 'hideName': False, 'i': 'caseinfoid-7717e580-9bed-11e9-9a3f-8b4b2158e260', 'moved': False, 'name': 'Team Members', 'static': False, 'type': 'team', 'w': 1, 'x': 2, 'y': 6}, {'displayType': 'CARD', 'h': 2, 'i': 'caseinfoid-ac32f620-a0b0-11e9-b27f-13ae1773d289', 'items': [{'endCol': 1, 'fieldId': 'occurred', 'height': 24, 'id': 'incident-occurred-field', 'index': 0, 'startCol': 0}, {'endCol': 1, 'fieldId': 'dbotmodified', 'height': 24, 'id': 'incident-modified-field', 'index': 1, 'startCol': 0}, {'endCol': 2, 'fieldId': 'dbotduedate', 'height': 24, 'id': 'incident-dueDate-field', 'index': 2, 'startCol': 0}, {'endCol': 2, 'fieldId': 'dbotcreated', 'height': 24, 'id': 'incident-created-field', 'index': 0, 'startCol': 1}, {'endCol': 2, 'fieldId': 'dbotclosed', 'height': 24, 'id': 'incident-closed-field', 'index': 1, 'startCol': 1}], 'moved': False, 'name': 'Timeline Information', 'static': False, 'w': 1, 'x': 0, 'y': 2}, {'displayType': 'ROW', 'h': 2, 'i': 'caseinfoid-88e6bf70-a0b1-11e9-b27f-13ae1773d289', 'isVisible': True, 'items': [{'endCol': 2, 'fieldId': 'dbotclosed', 'height': 24, 'id': 'incident-dbotClosed-field', 'index': 0, 'startCol': 0}, {'endCol': 2, 'fieldId': 'closereason', 'height': 24, 'id': 'incident-closeReason-field', 'index': 1, 'startCol': 0}, {'endCol': 2, 'fieldId': 'closenotes', 'height': 24, 'id': 'incident-closeNotes-field', 'index': 2, 'startCol': 0}], 'moved': False, 'name': 'Closing Information', 'static': False, 'w': 1, 'x': 0, 'y': 4}, {'displayType': 'CARD', 'h': 2, 'i': 'caseinfoid-e54b1770-a0b1-11e9-b27f-13ae1773d289', 'isVisible': True, 'items': [{'endCol': 2, 'fieldId': 'details', 'height': 24, 'id': 'incident-details-field', 'index': 0, 'startCol': 0}], 'moved': False, 'name': 'Investigation Data', 'static': False, 'w': 1, 'x': 1, 'y': 2}], 'type': 'custom'}, {'id': 'relatedIncidents', 'name': 'Related Incidents', 'type': 'relatedIncidents'}, {'id': 'warRoom', 'name': 'War Room', 'type': 'warRoom'}, {'id': 'workPlan', 'name': 'Work Plan', 'type': 'workPlan'}, {'id': 'evidenceBoard', 'name': 'Evidence Board', 'type': 'evidenceBoard'}, {'id': 'canvas', 'name': 'Canvas', 'type': 'canvas'}, {'id': 'summary', 'name': 'Legacy Summary', 'type': 'summary'}, {'hidden': False, 'id': 'sl6z3tlmim', 'name': 'Investigation', 'sections': [{'displayType': 'ROW', 'h': 3, 'hideName': False, 'i': 'sl6z3tlmim-0309e3d0-0486-11ea-b103-7ba5e7ae90b3', 'items': [{'endCol': 2, 'fieldId': 'username', 'height': 24, 'id': '1f0181f0-0487-11ea-8cae-45b27192ac66', 'index': 0, 'startCol': 0}, {'endCol': 2, 'fieldId': 'previouscoordinates', 'height': 24, 'id': '0c9128f0-0486-11ea-b103-7ba5e7ae90b3', 'index': 1, 'startCol': 0}, {'endCol': 2, 'fieldId': 'coordinates', 'height': 24, 'id': '0b80f170-0486-11ea-b103-7ba5e7ae90b3', 'index': 2, 'startCol': 0}, {'endCol': 2, 'fieldId': 'previoussourceip', 'height': 24, 'id': '126b6ba0-0486-11ea-b103-7ba5e7ae90b3', 'index': 3, 'startCol': 0}, {'endCol': 2, 'fieldId': 'sourceip', 'height': 24, 'id': '151703a0-0486-11ea-b103-7ba5e7ae90b3', 'index': 4, 'startCol': 0}, {'dropEffect': 'move', 'endCol': 2, 'fieldId': 'previouscountry', 'height': 24, 'id': '91718fb0-094a-11ea-9384-35aa869eba47', 'index': 5, 'listId': 'sl6z3tlmim-0309e3d0-0486-11ea-b103-7ba5e7ae90b3', 'startCol': 0}, {'dropEffect': 'move', 'endCol': 2, 'fieldId': 'country', 'height': 24, 'id': '8e1b5fd0-094a-11ea-9384-35aa869eba47', 'index': 6, 'listId': 'sl6z3tlmim-0309e3d0-0486-11ea-b103-7ba5e7ae90b3', 'startCol': 0}, {'dropEffect': 'move', 'endCol': 2, 'fieldId': 'previoussignindatetime', 'height': 24, 'id': '24686960-0487-11ea-8cae-45b27192ac66', 'index': 7, 'listId': 'sl6z3tlmim-0309e3d0-0486-11ea-b103-7ba5e7ae90b3', 'startCol': 0}, {'endCol': 2, 'fieldId': 'signindatetime', 'height': 24, 'id': '237779b0-0487-11ea-8cae-45b27192ac66', 'index': 8, 'startCol': 0}, {'endCol': 2, 'fieldId': 'destinationip', 'height': 24, 'id': 'a07c53e0-0487-11ea-8cae-45b27192ac66', 'index': 9, 'startCol': 0}, {'dropEffect': 'move', 'endCol': 2, 'fieldId': 'travelmaplink', 'height': 24, 'id': 'b92f58e0-0489-11ea-b56e-27b3581f8973', 'index': 10, 'listId': 'sl6z3tlmim-0309e3d0-0486-11ea-b103-7ba5e7ae90b3', 'startCol': 0}], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'Travel Information', 'static': False, 'w': 1, 'x': 0, 'y': 0}, {'h': 4, 'hideName': False, 'i': 'sl6z3tlmim-bae81750-0487-11ea-8cae-45b27192ac66', 'items': [], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'Bad or Suspicious Indicators', 'query': 'reputation:Bad or reputation:Suspicious', 'queryType': 'input', 'static': False, 'type': 'indicators', 'w': 2, 'x': 1, 'y': 4}, {'h': 4, 'hideName': False, 'i': 'sl6z3tlmim-c0813250-0487-11ea-8cae-45b27192ac66', 'items': [], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'Travel Map', 'query': {'categories': ['attachments'], 'lastId': '', 'pageSize': 100, 'tags': [], 'users': []}, 'queryType': 'warRoomFilter', 'static': False, 'type': 'invTimeline', 'w': 1, 'x': 0, 'y': 3}, {'h': 4, 'hideName': False, 'i': 'sl6z3tlmim-e00e21a0-0487-11ea-8cae-45b27192ac66', 'items': [], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'Travel Distance & Time', 'query': {'tags': ['eventduration', 'geodistance']}, 'queryType': 'warRoomFilter', 'static': False, 'type': 'invTimeline', 'w': 1, 'x': 2, 'y': 0}, {'h': 4, 'hideName': False, 'i': 'sl6z3tlmim-0d156cc0-0489-11ea-aaf8-2db208b493bd', 'items': [], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'Work Plan', 'static': False, 'type': 'workplan', 'w': 1, 'x': 2, 'y': 8}, {'h': 2, 'hideName': False, 'i': 'sl6z3tlmim-8db43690-0489-11ea-b56e-27b3581f8973', 'items': [], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'Notes', 'static': False, 'type': 'notes', 'w': 1, 'x': 1, 'y': 8}, {'h': 2, 'hideName': False, 'i': 'sl6z3tlmim-9271bea0-0489-11ea-b56e-27b3581f8973', 'items': [], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'Evidence', 'static': False, 'type': 'evidence', 'w': 1, 'x': 0, 'y': 7}, {'h': 4, 'hideName': False, 'i': 'sl6z3tlmim-25f2dd20-048b-11ea-b56e-27b3581f8973', 'items': [], 'maxW': 3, 'minH': 1, 'minW': 1, 'moved': False, 'name': 'User Details', 'query': {'tags': ['userinfo']}, 'queryType': 'warRoomFilter', 'static': False, 'type': 'invTimeline', 'w': 1, 'x': 1, 'y': 0}], 'type': 'custom'}], 'typeId': 'Impossible Traveler', 'version': -1}, 'typeId': 'Impossible Traveler', 'version': -1, 'toVersion': '5.9.9'}
    impossible_traveler.create_script('CalculateGeoDistance', script)
    impossible_traveler.create_playbook('Impossible_Traveler', playbook)
    impossible_traveler.create_test_playbook('playbook-Impossible_Traveler_-_Test', test_playbook)
    impossible_traveler.create_layout('Impossible_Traveler', layout)
    impossible_traveler.create_incident_field('Coordinates', {'id': 'incident_coordinates', 'name': 'Coordinates'})
    impossible_traveler.create_incident_field('Previous_Coordinates', {'id': 'incident_previouscoordinates',
                                                                       'name': 'Previous Coordinates', "associatedTypes": ["Impossible Traveler"]})
    impossible_traveler.create_incident_field('previouscountry', {'id': 'incident_previouscountry',
                                                                  'name': 'previouscountry'})
    impossible_traveler.create_incident_field('Previous_Sign_In_Date_Time',
                                              {'id': 'incident_previoussignindatetime',
                                               'name': 'Previous Sign In Date Time'})
    impossible_traveler.create_incident_field('Previous_Source_IP', {'id': 'incident_previoussourceip',
                                                                     'name': 'Previous Source IP'})
    impossible_traveler.create_incident_field('Sign_In_Date_Time', {'id': 'incident_signindatetime',
                                                                    'name': 'Sign In Date Time'})
    impossible_traveler.create_incident_field('Travel_Map_Link', {'id': 'incident_travelmaplink', 'name': 'Travel Map Link'})
    impossible_traveler.create_incident_type('Impossible_Traveler', {'id': 'impossibletraveler',
                                                                     'name': 'Impossible Traveler',
                                                                     "playbookId": "Impossible Traveler",
                                                                     'preProcessingScript': '', 'color': 'test'})

    with ChangeCWD(repo.path):
        ids = cis.IDSetCreator()
        ids.create_id_set()
        return ids.id_set


# def test_id_set(repo):
#     pack = repo.create_pack('pack')
#     with open('test_content/playbook-Block_IP_-_Generic_v2.yml') as yml_file:
#         yml = yaml.load(yml_file, Loader=yaml.FullLoader)
#         pack.create_script('CalculateGeoDistancey', yml)
#     return yml


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
