from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.hook_validations.id import IDSetValidations
from TestSuite.test_tools import ChangeCWD

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
            "SubPlaybook_version_5_5"
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
    playbook_with_invalid_sub_playbook_version = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "5.0.0",
        "pack": "Example",
        "implementing_playbooks": [
            "SubPlaybook_version_5_5"
        ]
    }}
    playbook_with_invalid_integration_version = {"Example Playbook": {
        "name": "Example Playbook",
        "file_path": playbook_path,
        "fromversion": "3.0.0",
        "pack": "Example",
        "command_to_integration": {
            "test-command": [
                "Integration_version_4",
                "Integration_version_5"
            ]
        }
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
    id_set = {
        'playbooks': [
            {
                'SubPlaybook_version_5': {
                    'fromversion': "5.0.0",
                    "file_path": playbook_path,
                }
            },
            {
                'SubPlaybook_no_version': {
                    'fromversion': "",
                    "file_path": playbook_path,
                }
            },
            {
                'SubPlaybook_version_5_5': {
                    'fromversion': "5.5.0",
                    "file_path": playbook_path,
                }
            },
            {
                'Example Playbook': {
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

    def test_are_playbook_entities_versions_valid(self, repo, mocker):
        """

        Given
            - an id_set file
            - a Playbook those entities:
                * implementing_scripts
                * implementing_playbooks
                * command_to_integration

        When
            - _are_playbook_entities_versions_valid is called

        Then
            - Validates that each entity version match the playbook version.

        """
        pack = repo.create_pack("Pack1")
        self.validator.playbook_set = self.id_set["playbooks"]
        self.validator.integration_set = self.id_set["integrations"]
        self.validator.script_set = self.id_set["scripts"]

        with ChangeCWD(repo.path):

            is_sub_playbook_invalid = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_sub_playbook_not_in_id_set, pack.path)
            assert not is_sub_playbook_invalid

            # all playbook's entities has valid versions
            is_playbook_version_valid = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_valid_versions, pack.path)
            assert is_playbook_version_valid

            # playbook uses scripts with invalid versions
            is_script_version_invalid = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_scripts_version, pack.path)
            assert not is_script_version_invalid

            # playbook uses sub playbooks with invalid versions
            is_sub_playbook_version_invalid = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_sub_playbook_version, pack.path)
            assert not is_sub_playbook_version_invalid

            # playbook uses integration's commands with invalid versions
            mocker.patch.object(self.validator, 'handle_error', return_value=True)
            is_integration_version_invalid = self.validator._are_playbook_entities_versions_valid(
                self.playbook_with_invalid_integration_version, self.playbook_path)
            assert not is_integration_version_invalid
