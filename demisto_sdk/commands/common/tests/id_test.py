from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.hook_validations.id import IDSetValidations
from TestSuite.test_tools import ChangeCWD

CONFIG = Configuration()

# Layouts tests consts:
LAYOUTS_CONTAINER_DATA = {'my_layoutscontainer': {
    'id': 'my_layoutscontainer',
    'name': 'my_layoutscontainer',
    'indicatorsDetails': {
            "tabs": [
                {
                    "id": "tjlpilelnw",
                    "name": "Profile",
                    "sections": [
                        {
                            "description": "Incidents that affected the user profile.",
                            "h": 2,
                            "i": "tjlpilelnw-978b0c1e-6739-432d-82d1-3b6641eed99f-tjlpilelnw",
                            "maxW": 3,
                            "minH": 1,
                            "minW": 2,
                            "moved": False,
                            "name": "User incidents",
                            "static": False,
                            "query": "script_to_test",
                            "queryType": "script",
                            "type": "dynamicIndicator",
                            "w": 1,
                            "x": 0,
                            "y": 0
                        }
                    ]
                }
            ]
    }}}
LAYOUT_DATA = {'my-layout': {
    'typename': 'my-layout',
    'scripts': ['script_to_test']
}}


def test_is_incident_type_using_real_playbook__happy_flow():
    """
    Given
        - incident type which has an existing default playbook id.
        - id_set.json

    When
        - is_playbook_found is called with an id_set.json

    Then
        - Ensure that the playbook is in the id set.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    incident_type_data = {
        "Zimperium Event": {
            "playbooks": "Zimperium Incident Enrichment"
        }
    }
    validator.playbook_set = [{'Zimperium Incident Enrichment': {
        'name': 'Zimperium Incident Enrichment',
        'file_path': 'Packs/Zimperium/Playbooks/Zimperium_Incident_Enrichment.yml',
        'fromversion': '5.0.0'}
    }]

    assert validator._is_incident_type_default_playbook_found(incident_type_data=incident_type_data) is True, \
        "The incident type default playbook id does not exist in the id set"


def test_is_incident_type_using_real_playbook__no_matching_playbook_id():
    """
    Given
        - incident type which has a non existing default playbook id.
        - id_set.json

    When
        - is_playbook_found is called with an id_set.json

    Then
        - Ensure that the playbook is in the id set.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    incident_type_data = {
        "Zimperium Event": {
            "playbooks": "a fake playbook id"
        }
    }
    validator.playbook_set = [{'Zimperium Incident Enrichment': {
        'name': 'Zimperium Incident Enrichment',
        'file_path': 'Packs/Zimperium/Playbooks/Zimperium_Incident_Enrichment.yml',
        'fromversion': '5.0.0'}
    }]

    assert validator._is_incident_type_default_playbook_found(incident_type_data=incident_type_data) is False


def test_is_incident_field_using_existing_script_positive():
    """
    Given
        - incident field which has an existing script id.
        - id_set.json

    When
        - is_incident_field_scripts_found is called with an id_set.json

    Then
        - Ensure that the script is in the id set - i.e is_incident_field_scripts_found returns True.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    incident_field_data = {'Incident_field_test': {
        'id': 'Incident_field_test',
        'name': 'Incident_field_test',
        'scripts': ['script_to_test']
    }
    }
    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
                "fromversion": "5.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_incident_field_scripts_found(incident_field_data=incident_field_data) is True, \
        "The incident field's script id is in the id set thus result should be True."


def test_is_incident_field_using_existing_script_negative():
    """
    Given
        - incident field which has a script id that doesn't exist.
        - id_set.json

    When
        - is_incident_field_scripts_found is called with an id_set.json

    Then
        - Ensure that the script is not in the id set - i.e is_incident_field_scripts_found returns False.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    incident_field_data = {'Incident_field_test': {
        'id': 'Incident_field_test',
        'name': 'Incident_field_test',
        'scripts': ['a fake script id']
    }
    }

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
                "fromversion": "5.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_incident_field_scripts_found(incident_field_data=incident_field_data) is False, \
        "The incident field's script id is not in the id set thus result should be False."


def test_is_incident_field_using_existing_script_no_scripts():
    """
    Given
        - incident field without scripts.
        - id_set.json

    When
        - is_incident_field_scripts_found is called with an id_set.json

    Then
        - Ensure is_incident_field_scripts_found returns True.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    incident_field_data = {'Incident_field_test': {
        'id': 'Incident_field_test',
        'name': 'Incident_field_test'
    }
    }

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
                "fromversion": "5.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_incident_field_scripts_found(incident_field_data=incident_field_data) is True, \
        "The incident field doesn't have any scripts thus the result should be True."


def test_is_layouts_container_using_existing_script_positive():
    """
    Given
        - layouts container which has an existing script id.
        - id_set.json

    When
        - is_layouts_container_scripts_found is called with an id_set.json

    Then
        - Ensure that the script is in the id set - i.e is_layouts_container_scripts_found returns True.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
                "fromversion": "6.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_layouts_container_scripts_found(layouts_container_data=LAYOUTS_CONTAINER_DATA) is True, \
        "The layouts container's script id is in the id set thus result should be True."


def test_is_layouts_container_using_existing_script_negative():
    """
    Given
        - layouts container which has a script that doesn't exist.
        - id_set.json

    When
        - is_layouts_container_scripts_found is called with an id_set.json

    Then
        - Ensure that the script is not in the id set - i.e is_layouts_container_scripts_found returns False.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.script_set = [{"other_script_id": {
        "name": "other_script_id",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-other_script_id.yml",
                "fromversion": "6.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_layouts_container_scripts_found(layouts_container_data=LAYOUTS_CONTAINER_DATA) is False, \
        "The layouts container's script id is not in the id set thus result should be False."


def test_is_layouts_container_using_existing_script_no_scripts():
    """
    Given
        - layouts container which has no scripts.
        - id_set.json

    When
        - is_layouts_container_scripts_found is called with an id_set.json

    Then
        - Ensure that is_layouts_container_scripts_found returns True.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    layouts_container_data_without_scripts = {'my_layoutscontainer': {
        'id': 'my_layoutscontainer',
        'name': 'my_layoutscontainer',
        'indicatorsDetails': {
            "tabs": [
                {
                    "id": "tjlpilelnw",
                    "name": "Profile",
                    "sections": [
                        {
                            "description": "Incidents that affected the user profile.",
                            "h": 2,
                            "i": "tjlpilelnw-978b0c1e-6739-432d-82d1-3b6641eed99f-tjlpilelnw",
                            "maxW": 3,
                            "minH": 1,
                            "minW": 2,
                            "moved": False,
                            "name": "User incidents",
                            "static": False,
                            "type": "dynamicIndicator",
                            "w": 1,
                            "x": 0,
                            "y": 0
                        }
                    ]
                }
            ]
        }}}

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
                "fromversion": "6.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_layouts_container_scripts_found(layouts_container_data=layouts_container_data_without_scripts)\
        is True, "The layouts container's doesn't have any scripts thus result should be False."


def test_is_layout_using_existing_script_positive():
    """
    Given
        - layout which has an existing script id.
        - id_set.json

    When
        - is_layout_scripts_found is called with an id_set.json

    Then
        - Ensure that the script is in the id set - i.e is_layout_scripts_found returns True.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
                "fromversion": "6.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_layout_scripts_found(layout_data=LAYOUT_DATA) is True, \
        "The layout's script id is in the id set thus result should be True."


def test_is_layout_using_existing_script_negative():
    """
    Given
        - layout which has has a script that doesn't exist.
        - id_set.json

    When
        - is_layout_scripts_found is called with an id_set.json

    Then
        - Ensure that the script is not in the id set - i.e is_layout_scripts_found returns False.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.script_set = [{"other_script_id": {
        "name": "other_script_id",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-other_script_id.yml",
                "fromversion": "6.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_layout_scripts_found(layout_data=LAYOUT_DATA) is False, \
        "The layout's script id is not in the id set thus result should be False."


def test_is_layout_using_existing_script_no_scripts():
    """
    Given
        - layout which has no scripts.
        - id_set.json

    When
        - is_layout_scripts_found is called with an id_set.json

    Then
        - Ensure that is_layout_scripts_found returns True.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    layout_data_without_scripts = {'my-layout': {
        'typename': 'my-layout',
        'scripts': []
    }}

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
                "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
                "fromversion": "6.0.0",
                "pack": "DeveloperTools"
    }
    }]

    assert validator._is_layout_scripts_found(layout_data=layout_data_without_scripts) is True, \
        "The layout doesn't have any scripts thus result should be True."


def test_is_layout_using_existing_script_ignore_builtin_scripts():
    """
    Given
        - layout which has a builtin script id.
        - id_set.json

    When
        - is_layout_scripts_found is called with an id_set.json

    Then
        - Ensure that the builtin script is ignored - i.e is_layout_scripts_found returns True.
    """

    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
        "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
        "fromversion": "6.0.0",
        "pack": "DeveloperTools"
    }
    }]

    layout_data = {'my-layout': {
        'typename': 'my-layout',
        'scripts': ['Builtin|||removeIndicatorField']
    }}

    assert validator._is_layout_scripts_found(layout_data=layout_data) is True, \
        "The layout's script id is a builtin script therefore ignored and thus the result should be True."


def test_is_layout_using_script_validate_integration_commands_scripts():
    """
    Given
        - layout which has an integration command script id .
        - id_set.json

    When
        - is_layout_scripts_found is called with an id_set.json

    Then
        - Ensure that the integration command script is not ignored - i.e is_layout_scripts_found returns True.
    """

    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
        "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
        "fromversion": "6.0.0",
        "pack": "DeveloperTools"
    }
    }]
    validator.integration_set = [{
            "SlackV2": {
                "name": "SlackV2",
                "file_path": "Packs/Slack/Integrations/Slack/Slack.yml",
                "fromversion": "5.0.0",
                "commands": [
                    "send-notification",
                    "slack-send"
                ],
                "pack": "Slack"
            }
        },
        {
            "Mail Sender (New)": {
                "name": "Mail Sender (New)",
                "file_path": "Packs/MailSenderNew/Integrations/MailSenderNew/MailSenderNew.yml",
                "commands": [
                    "send-mail"
                ],
                "tests": [
                    "Mail Sender (New) Test"
                ],
                "pack": "MailSenderNew"
            }
        }
    ]

    layout_data = {'my-layout': {
        'typename': 'my-layout',
        'scripts': ['SlackV2|||send-notification', 'Mail Sender (New)|||send-mail']
    }}

    assert validator._is_layout_scripts_found(layout_data=layout_data) is True, \
        "The layout's script id is an integration command which is real command."


def test_is_layout_using_script_validate_integration_commands_scripts_on_wrong_command():
    """
    Given
        - layout which has an integration command script id which is not existing in the id_set.json .
        - id_set.json

    When
        - is_layout_scripts_found is called with an id_set.json

    Then
        - Ensure that the integration command script is not ignored - i.e is_layout_scripts_found returns False.
    """

    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.script_set = [{"script_to_test": {
        "name": "script_to_test",
        "file_path": "Packs/DeveloperTools/TestPlaybooks/script-script_to_test.yml",
        "fromversion": "6.0.0",
        "pack": "DeveloperTools"
    }
    }]
    validator.integration_set = [{
            "SlackV2": {
                "name": "SlackV2",
                "file_path": "Packs/Slack/Integrations/Slack/Slack.yml",
                "fromversion": "5.0.0",
                "commands": [
                    "slack-send"
                ],
                "pack": "Slack"
            }
        },
        {
            "Mail Sender (New)": {
                "name": "Mail Sender (New)",
                "file_path": "Packs/MailSenderNew/Integrations/MailSenderNew/MailSenderNew.yml",
                "commands": [
                    "send-mail"
                ],
                "tests": [
                    "Mail Sender (New) Test"
                ],
                "pack": "MailSenderNew"
            }
        }
    ]

    layout_data = {'my-layout': {
        'typename': 'my-layout',
        'scripts': ['SlackV2|||send-notification', 'Mail Sender (New)|||send-mail']
    }}

    assert validator._is_layout_scripts_found(layout_data=layout_data) is False, \
        "The layout's script id is an integration command which is not real command."


def test_is_non_real_command_found__happy_flow():
    """
    Given
        - script which has a valid command.

    When
        - is_non_real_command_found is called

    Then
        - Ensure that the scripts depend-on commands are valid.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    script_data = {
        'name': 'OktaUpdateUser',
        'fidepends-le_path': 'Packs/DeprecatedContent/Scripts/script-OktaUpdateUser.yml',
        'fromversion': '5.0.0', 'deprecated': True, 'depends_on': ['okta-update-user'],
        'tests': ['No test - deprecated script with no test prior'], 'pack': 'DeprecatedContent'
    }

    assert validator._is_non_real_command_found(script_data=script_data) is True, \
        "The script has a non real command"


def test_is_non_real_command_found__bad_command_name():
    """
    Given
        - script which has a non valid command.

    When
        - is_non_real_command_found is called

    Then
        - Ensure that the scripts depend-on commands are non valid.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    script_data = {
        'name': 'OktaUpdateUser',
        'fidepends-le_path': 'Packs/DeprecatedContent/Scripts/script-OktaUpdateUser.yml',
        'fromversion': '5.0.0', 'deprecated': True, 'depends_on': ['okta-update-user', 'okta-update-user-copy'],
        'tests': ['No test - deprecated script with no test prior'], 'pack': 'DeprecatedContent'
    }

    assert validator._is_non_real_command_found(script_data=script_data) is False, \
        "The script has a non real command"


def test_is_non_real_command_found__no_depend_on_name():
    """
    Given
        - script which has no executeCommand.

    When
        - is_non_real_command_found is called

    Then
        - Ensure that the scripts depend-on commands are valid.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    script_data = {
        'name': 'OktaUpdateUser',
        'fidepends-le_path': 'Packs/CommonScripts/Scripts/NoExecuteCommand.yml',
        'fromversion': '5.0.0', 'deprecated': True,
        'tests': ['No test'], 'pack': 'CommonScripts'
    }

    assert validator._is_non_real_command_found(script_data=script_data) is True, \
        "The script has a non real command"


def test_is_integration_classifier_and_mapper_found__exist():
    """
    Given
        - integration which has classifier and mapper.

    When
        - _is_integration_handled_in_classifier_and_mapper is called

    Then
        - Ensure that the integration classifier and mapper were found.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.mappers_set = [{
        "Claroty-mapper":
            {
                "name": "Claroty - Incoming Mapper",
                "file_path": "Packs/Claroty/Classifiers/classifier-mapper-incoming-Claroty.json",
                "fromversion": "6.0.0",
                "pack": "Claroty",
                "incident_types": [
                    "Claroty Integrity Incident",
                    "Claroty Security Incident",
                    "Claroty IT Incident"
                ],
                "incident_fields": [
                    "Claroty Related Assets",
                    "Claroty Category",
                    "Claroty Alert Status",
                    "Claroty Network ID",
                    "Claroty Resource ID",
                    "Claroty Alert Type",
                    "Claroty Alert Resolved"
                ]
            }
    }]

    validator.classifiers_set = [
        {"Claroty":
            {
                "name": "Claroty - Classifier",
                "file_path": "Packs/Claroty/Classifiers/classifier-Claroty.json",
                "fromversion": "6.0.0",
                "pack": "Claroty",
                "incident_types": [
                    "Claroty Integrity Incident",
                    "Claroty Security Incident"
                ]
            }
         }
    ]

    integration_data = {
        "name": "Claroty",
        "file_path": "Packs/Claroty/Integrations/Claroty/Claroty.yml",
        "fromversion": "5.0.0",
        "commands": [
            "claroty-get-assets",
            "claroty-query-alerts",
            "claroty-resolve-alert",
            "claroty-get-single-alert"
        ],
        "pack": "Claroty",
        "classifiers": "Claroty",
        "mappers": [
            "Claroty-mapper"
        ]

    }

    assert validator._is_integration_classifier_and_mapper_found(integration_data=integration_data) is True, \
        "The incident classifier and mapper were not found"


def test_is_integration_classifier_and_mapper_found__mapper_not_exist():
    """
    Given
        - integration which has classifier and mapper.

    When
        - _is_integration_handled_in_classifier_and_mapper is called

    Then
        - Ensure that the integration mapper was not found.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.mappers_set = [{
        "Claroty-mapper_wrong":
            {
                "name": "Claroty - Incoming Mapper",
                "file_path": "Packs/Claroty/Classifiers/classifier-mapper-incoming-Claroty.json",
                "fromversion": "6.0.0",
                "pack": "Claroty",
                "incident_types": [
                    "Claroty Integrity Incident",
                    "Claroty Security Incident",
                    "Claroty IT Incident"
                ],
                "incident_fields": [
                    "Claroty Related Assets",
                    "Claroty Category",
                    "Claroty Alert Status",
                    "Claroty Network ID",
                    "Claroty Resource ID",
                    "Claroty Alert Type",
                    "Claroty Alert Resolved"
                ]
            }
    }]

    validator.classifiers_set = [{
        "Claroty":
            {
                "name": "Claroty - Classifier",
                "file_path": "Packs/Claroty/Classifiers/classifier-Claroty.json",
                "fromversion": "6.0.0",
                "pack": "Claroty",
                "incident_types": [
                    "Claroty Integrity Incident",
                    "Claroty Security Incident"
                ]
            }
    }
    ]

    integration_data = {
        "name": "Claroty",
        "file_path": "Packs/Claroty/Integrations/Claroty/Claroty.yml",
        "fromversion": "5.0.0",
        "commands": [
            "claroty-get-assets",
            "claroty-query-alerts",
            "claroty-resolve-alert",
            "claroty-get-single-alert"
        ],
        "pack": "Claroty",
        "classifiers": "Claroty",
        "mappers": [
            "Claroty-mapper"
        ]

    }

    assert validator._is_integration_classifier_and_mapper_found(integration_data=integration_data) is False, \
        "The incident mapper was found"


def test_is_integration_classifier_and_mapper_found__classifier_not_exist():
    """
    Given
        - integration which has classifier and mapper.

    When
        - _is_integration_handled_in_classifier_and_mapper is called

    Then
        - Ensure that the integration classifier was not found.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.mappers_set = [{
        "Claroty-mapper":
            {
                "name": "Claroty - Incoming Mapper",
                "file_path": "Packs/Claroty/Classifiers/classifier-mapper-incoming-Claroty.json",
                "fromversion": "6.0.0",
                "pack": "Claroty",
                "incident_types": [
                    "Claroty Integrity Incident",
                    "Claroty Security Incident",
                    "Claroty IT Incident"
                ],
                "incident_fields": [
                    "Claroty Related Assets",
                    "Claroty Category",
                    "Claroty Alert Status",
                    "Claroty Network ID",
                    "Claroty Resource ID",
                    "Claroty Alert Type",
                    "Claroty Alert Resolved"
                ]
            }
    }]

    validator.classifiers_set = [{
        "Claroty_wrong_classifier":
            {
                "name": "Claroty - Classifier",
                "file_path": "Packs/Claroty/Classifiers/classifier-Claroty.json",
                "fromversion": "6.0.0",
                "pack": "Claroty",
                "incident_types": [
                    "Claroty Integrity Incident",
                    "Claroty Security Incident"
                ]
            }
    }
    ]

    integration_data = {
        "name": "Claroty",
        "file_path": "Packs/Claroty/Integrations/Claroty/Claroty.yml",
        "fromversion": "5.0.0",
        "commands": [
            "claroty-get-assets",
            "claroty-query-alerts",
            "claroty-resolve-alert",
            "claroty-get-single-alert"
        ],
        "pack": "Claroty",
        "classifiers": "Claroty",
        "mappers": [
            "Claroty-mapper"
        ]

    }

    assert validator._is_integration_classifier_and_mapper_found(integration_data=integration_data) is False, \
        "The incident classifier was found"


def test_is_classifier_incident_types_found__exists():
    """
    Given
        - classifier which has incident types.

    When
        - _is_classifier_incident_types_found is called

    Then
        - Ensure that the classifier incident types were found.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.incident_types_set = [
        {
            "Claroty Integrity Incident": {
                "name": "Claroty Integrity Incident",
                "file_path": "Packs/Claroty/IncidentTypes/incidenttype-Claroty_Integrity_Incident.json",
                "fromversion": "5.0.0",
                "pack": "Claroty",
                "playbooks": "Claroty Incident"
            }
        },
        {
            "Claroty Security Incident": {
                "name": "Claroty Security Incident",
                "file_path": "Packs/Claroty/IncidentTypes/incidenttype-Claroty_Security_Incident.json",
                "fromversion": "5.0.0",
                "pack": "Claroty",
                "playbooks": "Claroty Incident"
            }
        }
    ]

    classifier_data = {
        "name": "Claroty - Classifier",
        "file_path": "Packs/Claroty/Classifiers/classifier-Claroty.json",
        "fromversion": "6.0.0",
        "pack": "Claroty",
        "incident_types": [
            "Claroty Integrity Incident",
            "Claroty Security Incident"
        ]
    }

    assert validator._is_classifier_incident_types_found(classifier_data=classifier_data) is True, \
        "The classifier incidenttypes were not found"


def test_is_classifier_incident_types_found__missing_classifier():
    """
    Given
        - classifier which has incident types.

    When
        - _is_classifier_incident_types_found is called

    Then
        - Ensure that the missing incident type was not found.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.incident_types_set = [
        {
            "Claroty Security Incident": {
                "name": "Claroty Security Incident",
                "file_path": "Packs/Claroty/IncidentTypes/incidenttype-Claroty_Security_Incident.json",
                "fromversion": "5.0.0",
                "pack": "Claroty",
                "playbooks": "Claroty Incident"
            }
        }
    ]

    classifier_data = {
        "name": "Claroty - Classifier",
        "file_path": "Packs/Claroty/Classifiers/classifier-Claroty.json",
        "fromversion": "6.0.0",
        "pack": "Claroty",
        "incident_types": [
            "Claroty Integrity Incident",
            "Claroty Security Incident"
        ]
    }

    assert validator._is_classifier_incident_types_found(classifier_data=classifier_data) is False, \
        "The classifier incidenttypes was found"


def test_is_mapper_incident_types_found__exists():
    """
    Given
        - mapper which has incident types.

    When
        - _is_mapper_incident_types_found is called

    Then
        - Ensure that the mapper incident types were found.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.incident_types_set = [
        {
            "Claroty Integrity Incident": {
                "name": "Claroty Integrity Incident",
                "file_path": "Packs/Claroty/IncidentTypes/incidenttype-Claroty_Integrity_Incident.json",
                "fromversion": "5.0.0",
                "pack": "Claroty",
                "playbooks": "Claroty Incident"
            }
        },
        {
            "Claroty Security Incident": {
                "name": "Claroty Security Incident",
                "file_path": "Packs/Claroty/IncidentTypes/incidenttype-Claroty_Security_Incident.json",
                "fromversion": "5.0.0",
                "pack": "Claroty",
                "playbooks": "Claroty Incident"
            }
        }
    ]

    mapper_data = {
        "name": "Claroty - Incoming Mapper",
        "file_path": "Packs/Claroty/Classifiers/classifier-mapper-incoming-Claroty.json",
        "fromversion": "6.0.0",
        "pack": "Claroty",
        "incident_types": [
            "Claroty Integrity Incident",
            "Claroty Security Incident"
        ],
        "incident_fields": [
            "Claroty Related Assets",
            "Claroty Category",
            "Claroty Alert Status",
            "Claroty Network ID",
            "Claroty Resource ID",
            "Claroty Alert Type",
            "Claroty Alert Resolved"
        ]
    }

    assert validator._is_mapper_incident_types_found(mapper_data=mapper_data) is True, \
        "The mapper incidenttypes were not found"


def test_is_mapper_incident_types_found__missing_classifier():
    """
    Given
        - mapper which has incident types.

    When
        - _is_mapper_incident_types_found is called

    Then
        - Ensure that the missing incident type was not found.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.incident_types_set = [
        {
            "Claroty Security Incident": {
                "name": "Claroty Security Incident",
                "file_path": "Packs/Claroty/IncidentTypes/incidenttype-Claroty_Security_Incident.json",
                "fromversion": "5.0.0",
                "pack": "Claroty",
                "playbooks": "Claroty Incident"
            }
        }
    ]

    mapper_data = {
        "name": "Claroty - Incoming Mapper",
        "file_path": "Packs/Claroty/Classifiers/classifier-mapper-incoming-Claroty.json",
        "fromversion": "6.0.0",
        "pack": "Claroty",
        "incident_types": [
            "Claroty Integrity Incident",
            "Claroty Security Incident"
        ],
        "incident_fields": [
            "Claroty Related Assets",
            "Claroty Category",
            "Claroty Alert Status",
            "Claroty Network ID",
            "Claroty Resource ID",
            "Claroty Alert Type",
            "Claroty Alert Resolved"
        ]
    }

    assert validator._is_mapper_incident_types_found(mapper_data=mapper_data) is False, \
        "The mapper incidenttypes was found"


def test_is_unique_file_valid_in_set(pack):
    """
    Given
        - pack with pack_metadata file.
    When
        - is_unique_file_valid_in_set is called
    Then
        - Ensure it is valid and no error is returned.
    """
    pack_metadata_data = {
        "VMware": {
            "name": "VMware",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }
    pack.pack_metadata.write_json(pack_metadata_data)
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)
    is_valid, error = validator.is_unique_file_valid_in_set(pack_path=pack.path)
    assert is_valid
    assert not error


def test_new_valid_is_pack_display_name_already_exist():
    """
    Given
        - pack_metadata file with a pack name that does not exist in our repo.
    When
        - _is_pack_display_name_already_exist is called
    Then
        - Ensure it is valid and no error is returned.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.packs_set = {
        "VMware": {
            "name": "VMware",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }

    pack_metadata_data = {
        "VMware": {
            "name": "VMware",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }
    is_valid, error = validator._is_pack_display_name_already_exist(pack_metadata_data=pack_metadata_data)
    assert is_valid
    assert not error


def test_valid_is_pack_display_name_already_exist():
    """
    Given
        - pack_metadata file with a pack name that does not exist in our repo.
    When
        - _is_pack_display_name_already_exist is called
    Then
        - Ensure it is valid and no error is returned.
    """

    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.packs_set = {
        "VMware": {
            "name": "VMware",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }

    pack_metadata_data = {
        "VMware2": {
            "name": "VMware2",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }
    is_valid, error = validator._is_pack_display_name_already_exist(pack_metadata_data=pack_metadata_data)
    assert is_valid
    assert not error


def test_invalid_is_pack_display_name_already_exist():
    """
    Given
        - pack_metadata file with a pack name that already exists in our repo.
    When
        - _is_pack_display_name_already_exist is called
    Then
        - Ensure it is invalid and the error message is returned.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.packs_set = {
        "VMware": {
            "name": "VMware",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }

    pack_metadata_data = {
        "VMwareV2": {
            "name": "VMware",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }
    is_valid, error = validator._is_pack_display_name_already_exist(pack_metadata_data=pack_metadata_data)
    assert not is_valid
    assert error == ("A pack named: VMware already exists in content repository, change the pack's "
                     "name in the metadata file.", 'PA122')


def test_new_invalid_is_pack_display_name_already_exist():
    """
    Given
        - pack_metadata file with a pack name that already exists in our repo.
    When
        - _is_pack_display_name_already_exist is called
    Then
        - Ensure it is invalid and the error message is returned.
    """
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)

    validator.packs_set = {
        "CiscoEmailSecurity": {
            "name": "Cisco Email Security",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }

    pack_metadata_data = {
        "CiscoEmailSecurityV2": {
            "name": "Cisco Email Security",
            "current_version": "1.1.0",
            "author": "Cortex XSOAR",
            "certification": "certified",
            "tags": [],
            "use_cases": [],
            "categories": [
                "IT Services"
            ],
            "id": "VMware"
        }
    }
    is_valid, error = validator._is_pack_display_name_already_exist(pack_metadata_data=pack_metadata_data)
    assert not is_valid
    assert error == ("A pack named: Cisco Email Security already exists in content repository, change the pack's "
                     "name in the metadata file.", 'PA122')


class TestPlaybookEntitiesVersionsValid:
    validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)
    playbook_path = "Packs/Example/Playbooks/playbook-Example_Playbook.yml"
    playbook_with_valid_versions = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "5.5.0",
        "pack": "Example",
        "implementing_scripts": [
            "Script_version_5",
            "Script_no_version",
            "Script_version_5_5"
        ],
        "implementing_playbooks": [
            "SubPlaybook_version_5",
            "SubPlaybook_no_version",
            "SubPlaybook_version_5_5",
            "playbook_dup"
        ],
        "command_to_integration": {
            "test-command": [
                "Integration_version_5",
                "Integration_version_4"
            ]
        }
    }}

    playbook_with_invalid_scripts_version = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "5.0.0",
        "pack": "Example",
        "implementing_scripts": [
            "Script_version_5_5"
        ]
    }}
    playbook_with_invalid_sub_playbook_version_from_version_5_0_0 = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "5.0.0",
        "pack": "Example",
        "implementing_playbooks": [
            "SubPlaybook_version_5_5",
            "playbook_dup"
        ]
    }}
    playbook_with_invalid_sub_playbook_version_from_version_6_0_0 = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "6.0.0",
        "pack": "Example",
        "implementing_playbooks": [
            "SubPlaybook_version_6_5"
        ]
    }}
    playbook_with_sub_playbook_not_in_id_set = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "5.0.0",
        "pack": "Example",
        "implementing_playbooks": [
            "SubPlaybook_not_in_id_set"
        ]
    }}
    playbook_with_valid_sub_playbook_name = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "5.0.0",
        "pack": "Example",
        "implementing_playbooks": [
            "SubPlaybook_version_5_5"
        ]
    }}
    playbook_with_invalid_sub_playbook_name = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "5.0.0",
        "pack": "Example",
        "implementing_playbooks": [
            "SubPlaybook_version_5_5 "
        ]
    }}
    id_set = {
        'playbooks': [
            {
                'playbook_dup': {
                    'name': 'test',
                    'fromversion': "5.0.0",
                    'toversion': "5.9.9",
                    "file_path": playbook_path,
                    "command_to_integration": {
                        "test-command": [
                            "Integration_version_4",
                            "Integration_version_5"
                        ]
                    }
                }
            },
            {
                'playbook_dup': {
                    'name': 'test',
                    'fromversion': "6.0.0",
                    "file_path": playbook_path,
                    "command_to_integration": {
                        "test-command": [
                            "Integration_version_4",
                            "Integration_version_5"
                        ]
                    }
                }
            },
            {
                'SubPlaybook_version_5': {
                    'name': 'SubPlaybook_version_5',
                    'fromversion': "5.0.0",
                    "file_path": playbook_path,
                }
            },
            {
                'SubPlaybook_no_version': {
                    'name': 'SubPlaybook_no_version',
                    'fromversion': "",
                    "file_path": playbook_path,
                }
            },
            {
                'SubPlaybook_version_5_5': {
                    'name': 'SubPlaybook_version_5_5',
                    'fromversion': "5.5.0",
                    "file_path": playbook_path,
                }
            },
            {
                'SubPlaybook_version_6_5': {
                    'name': 'SubPlaybook_version_6_5',
                    'fromversion': "6.5.0",
                    "file_path": playbook_path,
                }
            },
            {
                'Example Playbook': {
                    'name': 'test',
                    'fromversion': "5.5.0",
                    "file_path": playbook_path,
                    "command_to_integration": {
                        "test-command": [
                            "Integration_version_4",
                            "Integration_version_5"
                        ]
                    }
                }
            }
        ],
        'integrations': [
            {
                'Integration_version_5': {
                    'fromversion': "5.0.0"
                }
            },
            {
                'Integration_version_4': {
                    'fromversion': "4.0.0"
                }
            }
        ],
        'scripts': [
            {
                'Script_version_5': {
                    'fromversion': "5.0.0"
                }
            },
            {
                'Script_no_version': {
                    'fromversion': ""
                }
            },
            {
                'Script_version_5_5': {
                    'fromversion': "5.5.0"
                }
            }
        ],
    }

    def test_are_playbook_entities_versions_valid_scripts_and_subplaybooks(self, repo, mocker):
        """

        Given
            - an id_set file
            - a Playbook those entities:
                * implementing_scripts
                * implementing_playbooks

        When
            - _are_playbook_entities_versions_valid is called

        Then
            - Validates that each entity version match the playbook version.

        """
        pack = repo.create_pack("Pack1")
        playbook = pack.create_playbook('MyPlay')
        playbook.create_default_playbook()
        self.validator.playbook_set = self.id_set["playbooks"]
        self.validator.integration_set = self.id_set["integrations"]
        self.validator.script_set = self.id_set["scripts"]

        with ChangeCWD(repo.path):
            is_sub_playbook_invalid, error = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_sub_playbook_not_in_id_set, playbook.yml.path)
            assert not is_sub_playbook_invalid
            assert "do not exist in the id_set" in error

            # all playbook's entities has valid versions
            is_playbook_version_valid, error = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_valid_versions, playbook.yml.path)
            assert is_playbook_version_valid
            assert error is None

            # playbook uses scripts with invalid versions
            is_script_version_invalid, error = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_scripts_version, playbook.yml.path)
            assert not is_script_version_invalid

            # playbook uses sub playbooks with invalid versions
            is_sub_playbook_version_invalid, error = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_sub_playbook_version_from_version_5_0_0, playbook.yml.path)
            assert not is_sub_playbook_version_invalid

    def test_are_playbook_entities_versions_valid_skip_unavailable(self, repo, mocker):
        """
        Given
            - an id_set file
            - a Playbook that is implemented by sub-playbooks with mismatched fromversions:
                - once with skipunavailable, and from version 5.0.0 - should fail
                - once with skipunavailable, and from version 6.0.0 - shouldn't fail
                - once without skipunavailable - should fail

        When
            - _are_playbook_entities_versions_valid is called

        Then
            - Validates that validation fails when skipunavailable is not set and passes otherwise
        """
        pack = repo.create_pack("Pack1")
        playbook = pack.create_playbook('MyPlay')
        playbook.create_default_playbook()
        playbook_data = playbook.yml.read_dict()

        self.validator.playbook_set = self.id_set["playbooks"]
        self.validator.integration_set = self.id_set["integrations"]
        self.validator.script_set = self.id_set["scripts"]

        with ChangeCWD(repo.path):
            # playbook uses sub playbooks with invalid versions, skipunavailable is set but
            # mainplaybook fromversion is 5.0.0 - should fail
            playbook_data['tasks'] = {
                '0': {
                    'id': '0',
                    'task': {
                        'playbookName': 'SubPlaybook_version_5_5'
                    },
                    'skipunavailable': True
                }
            }
            playbook.yml.write_dict(playbook_data)
            is_sub_playbook_version_invalid, error = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_sub_playbook_version_from_version_5_0_0, playbook.yml.path)
            assert not is_sub_playbook_version_invalid

            # playbook uses sub playbooks with invalid versions, skipunavailable is set and
            # mainplaybook fromversion is 6.0.0 - shouldn't fail
            playbook_data['tasks'] = {
                '0': {
                    'id': '0',
                    'task': {
                        'playbookName': 'SubPlaybook_version_6_5'
                    },
                    'skipunavailable': True
                }
            }
            playbook.yml.write_dict(playbook_data)
            is_sub_playbook_version_invalid, error = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_sub_playbook_version_from_version_6_0_0, playbook.yml.path)
            assert is_sub_playbook_version_invalid

            # playbook uses sub playbooks with invalid versions but no skipunavailable
            playbook_data['tasks'] = {
                '0': {
                    'id': '0',
                    'task': {
                        'playbookName': 'SubPlaybook_version_5_5'
                    },
                    'skipunavailable': False
                }
            }
            playbook.yml.write_dict(playbook_data)
            is_sub_playbook_version_invalid, error = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_sub_playbook_version_from_version_5_0_0, playbook.yml.path)
            assert not is_sub_playbook_version_invalid

    def test_are_playbook_entities_versions_valid_integration_commands(self, repo, mocker):
        """

        Given
            - an id_set file
            - a Playbook those entities:
                * command_to_integration

        When
            - _are_playbook_entities_versions_valid is called

        Then
            - Validates that integrations version match the playbook version.
        """
        pack = repo.create_pack("Pack1")
        playbook = pack.create_playbook('MyPlay')
        playbook.create_default_playbook()

        # setup validator
        validator = IDSetValidations(is_circle=False, is_test_run=True, configuration=CONFIG)
        validator.playbook_set = [{
            playbook.name: {
                'name': playbook.name,
                'fromversion': "5.5.0",
                "file_path": playbook.yml.path,
                "command_to_integration": {
                    "test-command": [
                        "Integration_version_4",
                        "Integration_version_5"
                    ]
                }
            }
        }]

        validator.integration_set = self.id_set["integrations"]
        validator.script_set = self.id_set["scripts"]

        playbook_with_invalid_integration_version = {playbook.name: {
            "name": playbook.name,
            "file_path": playbook.yml.path,
            "fromversion": "3.0.0",
            "pack": "Example",
            "command_to_integration": {
                "test-command": [
                    "Integration_version_4",
                    "Integration_version_5"
                ]
            }
        }}

        playbook_with_valid_integration_version = {playbook.name: {
            "name": playbook.name,
            "file_path": playbook.yml.path,
            "fromversion": "5.0.0",
            "pack": "Example",
            "command_to_integration": {
                "test-command": [
                    "Integration_version_4",
                    "Integration_version_5"
                ]
            }
        }}

        with ChangeCWD(repo.path):
            # playbook uses integration's commands with invalid versions
            mocker.patch.object(validator, 'handle_error', return_value=True)
            is_integration_version_invalid, error = validator._are_playbook_entities_versions_valid(
                playbook_with_invalid_integration_version, playbook.yml.path)
            assert not is_integration_version_invalid

            # playbook uses integration's commands with valid versions
            mocker.patch.object(validator, 'handle_error', return_value=True)
            is_integration_version_invalid, error = validator._are_playbook_entities_versions_valid(
                playbook_with_valid_integration_version, playbook.yml.path)
            assert is_integration_version_invalid

    def test_playbook_sub_playbook_exist(self, repo, mocker):
        """

        Given
        - A playbook with sub playbook
        - An id_set file.

        When
        - validating playbook - sub playbook exists in id_set

        Then
        - In case sub playbook names does not exist in id_set , prints a warning.
        """
        pack = repo.create_pack("Pack1")
        self.validator.playbook_set = self.id_set["playbooks"]

        with ChangeCWD(repo.path):
            # playbook uses existing sub playbooks
            is_subplaybook_name_exist = self.validator.is_subplaybook_name_valid(
                self.playbook_with_valid_sub_playbook_name, pack.path)
            assert is_subplaybook_name_exist

    def test_playbook_sub_playbook_not_exist(self, repo, mocker):
        """

        Given
        - A playbook with sub playbook names
        - An id_set file.

        When
        - validating playbook - sub playbook does not exist in id_set

        Then
        - In case playbook name does not exist in id_set , prints a warning.
        """
        pack = repo.create_pack("Pack1")
        self.validator.playbook_set = self.id_set["playbooks"]

        with ChangeCWD(repo.path):
            # playbook uses existing sub playbooks
            is_subplaybook_name_exist = self.validator.is_subplaybook_name_valid(
                self.playbook_with_invalid_sub_playbook_name, pack.path)
            assert not is_subplaybook_name_exist
