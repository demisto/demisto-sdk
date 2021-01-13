from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.hook_validations.id import IDSetValidator

CONFIG = Configuration()


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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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


def test_is_non_real_command_found__happy_flow():
    """
    Given
        - script which has a valid command.

    When
        - is_non_real_command_found is called

    Then
        - Ensure that the scripts depend-on commands are valid.
    """
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

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
