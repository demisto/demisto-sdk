from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.hook_validations.id import IDSetValidator

CONFIG = Configuration()


def test_validness_in_set():
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

    obj_data = {
        "test": {
            "name": "test"
        }
    }
    obj_set = [
        obj_data,
    ]

    assert validator._is_valid_in_id_set(file_path="test", obj_data=obj_data, obj_set=obj_set), \
        "The id validator couldn't find id as valid one"


def test_obj_not_found_in_set():
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

    obj_data = {
        "test": {
            "name": "test"
        }
    }
    actual_obj_set = {
        "test": {
            "name": "test",
            "fromversion": "1.2.2"
        }
    }
    obj_set = [
        actual_obj_set,
    ]

    assert validator._is_valid_in_id_set(file_path="test", obj_data=obj_data, obj_set=obj_set) is False, \
        "The id validator couldn't find id as valid one"


def test_obj_data_mismatch_in_set():
    validator = IDSetValidator(is_circle=False, is_test_run=True, configuration=CONFIG)

    obj_data = {
        "test": {
            "name": "test"
        }
    }
    actual_obj_set = {
        "test": {
            "name": "not test",
        }
    }
    obj_set = [
        actual_obj_set,
    ]

    assert validator._is_valid_in_id_set(file_path="test", obj_data=obj_data, obj_set=obj_set) is False, \
        "The id validator couldn't find id as valid one"


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

    assert validator._is_playbook_found(incident_type_data=incident_type_data) is True, \
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

    assert validator._is_playbook_found(incident_type_data=incident_type_data) is False


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
