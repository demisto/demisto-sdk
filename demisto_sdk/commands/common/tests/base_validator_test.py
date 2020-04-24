import pytest
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.tests.constants_test import (
    INVALID_INTEGRATION_WITH_NO_TEST_PLAYBOOK, SCRIPT_WITH_PLAYBOOK,
    VALID_INTEGRATION_TEST_PATH, VALID_TEST_PLAYBOOK_PATH)

HAS_TESTS_KEY_UNPUTS = [
    (VALID_INTEGRATION_TEST_PATH, 'integration', True),
    (INVALID_INTEGRATION_WITH_NO_TEST_PLAYBOOK, 'integration', False)
]


@pytest.mark.parametrize('file_path, schema, expected', HAS_TESTS_KEY_UNPUTS)
def test_yml_has_test_key(file_path, schema, expected):
    # type: (str, str, bool) -> None
    """
        Given
        - A yml file test playbook list and the yml file type

        When
        - Checking if file has test playbook exists

        Then
        -  Ensure the method 'yml_has_test_key' return answer accordingly
    """
    structure_validator = StructureValidator(file_path, predefined_scheme=schema)
    validator = BaseValidator(structure_validator)
    tests = structure_validator.current_file.get('tests')
    assert validator.yml_has_test_key(tests, schema) == expected


FIND_TEST_MATCH_INPUT = [
    (
        {'integrations': 'integration1', 'playbookID': 'playbook1'},
        'integration1',
        'playbook1',
        'integration',
        True
    ),
    (
        {'integrations': 'integration1', 'playbookID': 'playbook1'},
        'integration2',
        'playbook1',
        'integration',
        False
    ),
    (
        {'integrations': ['integration1', 'integration2'], 'playbookID': 'playbook1'},
        'integration1',
        'playbook1',
        'integration',
        True
    ),
    (
        {'integrations': ['integration1', 'integration2'], 'playbookID': 'playbook1'},
        'integration3',
        'playbook1',
        'integration',
        False
    ),
    (
        {'integrations': ['integration1', 'integration2'], 'playbookID': 'playbook1'},
        'integration1',
        'playbook2',
        'integration',
        False
    ),
    (
        {'playbookID': 'playbook1'},
        'playbook',
        'playbook1',
        'playbook',
        True
    ),
    (
        {'playbookID': 'playbook1'},
        'some-script',
        'playbook1',
        'script',
        True
    ),

]


@pytest.mark.parametrize('test_config, integration_id, test_playbook_id, file_type, expected', FIND_TEST_MATCH_INPUT)
def test_find_test_match(test_config, integration_id, test_playbook_id, expected, file_type):
    # type: (dict, str, str, bool, str) -> None
    """
        Given
        - A test configuration from 'conf.json' file. test-playbook id and a content item id

        When
        - checking if the test configuration matches the content item and the test-playbook

        Then
        -  Ensure the method 'find_test_match' return answer accordingly
    """
    assert BaseValidator.find_test_match(test_config, test_playbook_id, integration_id, file_type) == expected


NOT_REGISTERED_TESTS_INPUT = [
    (
        VALID_INTEGRATION_TEST_PATH,
        'integration',
        [{'integrations': 'PagerDuty v2', 'playbookID': 'PagerDuty Test'}],
        []
    ),
    (
        VALID_INTEGRATION_TEST_PATH,
        'integration',
        [{'integrations': 'test', 'playbookID': 'PagerDuty Test'}],
        ['PagerDuty Test']
    ),
    (
        VALID_INTEGRATION_TEST_PATH,
        'integration',
        [{'integrations': 'PagerDuty v2', 'playbookID': 'Playbook'}],
        ['PagerDuty Test']
    ),
    (
        VALID_TEST_PLAYBOOK_PATH,
        'playbook',
        [{'integrations': 'Account Enrichment', 'playbookID': 'PagerDuty Test'}],
        []
    ),
    (
        VALID_TEST_PLAYBOOK_PATH,
        'playbook',
        [{'integrations': 'Account Enrichment', 'playbookID': 'Playbook'}],
        ['PagerDuty Test']
    ),
    (
        SCRIPT_WITH_PLAYBOOK,
        'script',
        [{'integrations': 'TestCreateDuplicates', 'playbookID': 'PagerDuty Test'}],
        []
    ),
    (
        SCRIPT_WITH_PLAYBOOK,
        'script',
        [{'integrations': 'TestCreateDuplicates', 'playbookID': 'other test'}],
        ['PagerDuty Test']
    )

]


@pytest.mark.parametrize('file_path, schema, conf_json_data, expected', NOT_REGISTERED_TESTS_INPUT)
def test_get_not_registered_tests(file_path, schema, conf_json_data, expected):
    # type: (str, str, list, list) -> None
    """
        Given
        - A content item with test playbooks configured on it

        When
        - Checking if the test playbooks are configured in 'conf.json' file

        Then
        -  Ensure the method 'get_not_registered_tests' return all test playbooks that are not configured
    """
    structure_validator = StructureValidator(file_path, predefined_scheme=schema)
    validator = BaseValidator(structure_validator)
    tests = structure_validator.current_file.get('tests')
    integration_id = validator._get_file_id(structure_validator.scheme_name)
    assert validator.get_not_registered_tests(conf_json_data, integration_id, tests) == expected
