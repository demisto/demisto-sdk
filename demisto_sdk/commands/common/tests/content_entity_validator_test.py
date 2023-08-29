from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

import pytest

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    EXCLUDED_DISPLAY_NAME_WORDS,
    MODELING_RULE,
    PARSING_RULE,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.tools import (
    get_not_registered_tests,
    is_test_config_match,
)
from demisto_sdk.tests.constants_test import (
    INVALID_INTEGRATION_WITH_NO_TEST_PLAYBOOK,
    INVALID_PLAYBOOK_PATH,
    VALID_INTEGRATION_TEST_PATH,
    VALID_PLAYBOOK_ID_PATH,
    VALID_TEST_PLAYBOOK_MARKETPLACES_PATH,
    VALID_TEST_PLAYBOOK_PATH,
)
from TestSuite.test_tools import ChangeCWD

HAS_TESTS_KEY_UNPUTS = [
    (VALID_INTEGRATION_TEST_PATH, "integration", True),
    (INVALID_INTEGRATION_WITH_NO_TEST_PLAYBOOK, "integration", False),
]


@pytest.mark.parametrize("file_path, schema, expected", HAS_TESTS_KEY_UNPUTS)
def test_yml_has_test_key(file_path: str, schema: str, expected: bool) -> None:
    """
    Given
    - A yml file test playbook list and the yml file type

    When
    - Checking if file has test playbook exists

    Then
    -  Ensure the method 'yml_has_test_key' return answer accordingly
    """
    structure_validator = StructureValidator(file_path, predefined_scheme=schema)
    validator = ContentEntityValidator(structure_validator)
    tests = structure_validator.current_file.get("tests")
    assert validator.yml_has_test_key(tests, schema) == expected


FIND_TEST_MATCH_INPUT = [
    (
        {"integrations": "integration1", "playbookID": "playbook1"},
        "integration1",
        "playbook1",
        "integration",
        True,
    ),
    (
        {"integrations": "integration1", "playbookID": "playbook1"},
        "integration2",
        "playbook1",
        "integration",
        False,
    ),
    (
        {"integrations": ["integration1", "integration2"], "playbookID": "playbook1"},
        "integration1",
        "playbook1",
        "integration",
        True,
    ),
    (
        {"integrations": ["integration1", "integration2"], "playbookID": "playbook1"},
        "integration3",
        "playbook1",
        "integration",
        False,
    ),
    ({"playbookID": "playbook1"}, "", "playbook1", "playbook", True),
]


@pytest.mark.parametrize(
    "test_config, integration_id, test_playbook_id, file_type, expected",
    FIND_TEST_MATCH_INPUT,
)
def test_find_test_match(
    test_config: dict,
    integration_id: str,
    test_playbook_id: str,
    expected: bool,
    file_type: str,
) -> None:
    """
    Given
    - A test configuration from 'conf.json' file. test-playbook id and a content item id

    When
    - checking if the test configuration matches the content item and the test-playbook

    Then
    -  Ensure the method 'find_test_match' return answer accordingly
    """
    assert (
        is_test_config_match(test_config, test_playbook_id, integration_id) == expected
    )


NOT_REGISTERED_TESTS_INPUT = [
    (
        VALID_INTEGRATION_TEST_PATH,
        "integration",
        [{"integrations": "PagerDuty v2", "playbookID": "PagerDuty Test"}],
        "PagerDuty v2",
        [],
    ),
    (
        VALID_INTEGRATION_TEST_PATH,
        "integration",
        [{"integrations": "test", "playbookID": "PagerDuty Test"}],
        "PagerDuty v2",
        ["PagerDuty Test"],
    ),
    (
        VALID_INTEGRATION_TEST_PATH,
        "integration",
        [{"integrations": "PagerDuty v2", "playbookID": "Playbook"}],
        "PagerDuty v3",
        ["PagerDuty Test"],
    ),
    (
        VALID_TEST_PLAYBOOK_PATH,
        "playbook",
        [{"integrations": "Account Enrichment", "playbookID": "PagerDuty Test"}],
        "Account Enrichment",
        [],
    ),
    (
        VALID_TEST_PLAYBOOK_PATH,
        "playbook",
        [{"integrations": "Account Enrichment", "playbookID": "Playbook"}],
        "Account Enrichment",
        ["PagerDuty Test"],
    ),
]


@pytest.mark.parametrize(
    "file_path, schema, conf_json_data, content_item_id, expected",
    NOT_REGISTERED_TESTS_INPUT,
)
def test_get_not_registered_tests(
    file_path: str,
    schema: str,
    conf_json_data: list,
    content_item_id: str,
    expected: list,
) -> None:
    """
    Given
    - A content item with test playbooks configured on it

    When
    - Checking if the test playbooks are configured in 'conf.json' file

    Then
    -  Ensure the method 'get_not_registered_tests' return all test playbooks that are not configured
    """
    structure_validator = StructureValidator(file_path, predefined_scheme=schema)
    tests = structure_validator.current_file.get("tests")
    assert (
        get_not_registered_tests(conf_json_data, content_item_id, schema, tests)
        == expected
    )


def test_entity_valid_name_valid(repo, mocker):
    """
    Given:
    - Entity name that does not contain excluded words.

    When:
    - Checking whether entity name contains excluded word.

    Then:
    - Ensure true is returned.
    """
    pack = repo.create_pack("TestPack")
    integration = pack.create_integration(name="BitcoinAbuse")
    integration.create_default_integration(name="BitcoinAbuse")
    integration.yml.update({"display": "BitcoinAbuse"})
    integration_structure_validator = StructureValidator(integration.yml.path)
    integration_content_entity_validator = ContentEntityValidator(
        integration_structure_validator
    )
    assert integration_content_entity_validator.name_does_not_contain_excluded_word()


def test_entity_valid_name_invalid(repo, mocker):
    """
    Given:
    - Entity name with excluded word.

    When:
    - Checking whether entity name contains excluded word.

    Then:
    - Ensure false is returned.
    """
    pack = repo.create_pack("TestPack")
    script = pack.create_script(name="QRadar")
    script.create_default_script(name="QRadar")
    excluded_word = EXCLUDED_DISPLAY_NAME_WORDS[0]
    script.yml.update({"name": f"QRadar ({excluded_word})"})
    script_structure_validator = StructureValidator(script.yml.path)
    script_content_entity_validator = ContentEntityValidator(script_structure_validator)
    mocker.patch.object(script_content_entity_validator, "handle_error")
    assert not script_content_entity_validator.name_does_not_contain_excluded_word()


def test_validate_readme_exists_not_checking_on_test_playbook(repo, mocker):
    """
    Given:
    - A test playbook

    When:
    - Validating if a readme file exists

    Then:
    - Ensure that True is being returned since we don't validate a readme for test playbooks.
    """
    pack = repo.create_pack("TEST_PALYBOOK")
    test_playbook = pack.create_test_playbook("test_playbook1")
    structue_validator = StructureValidator(test_playbook.yml.path)
    content_entity_validator = ContentEntityValidator(structue_validator)
    assert content_entity_validator.validate_readme_exists()


def test_validate_readme_exists_not_checking_on_api_modules(repo):
    """
    Given:
    - An APIModules script

    When:
    - Validating if a readme file exists

    Then:
    - Ensure that True is being returned since we don't validate a readme for APIModules files.
    """
    pack = repo.create_pack(API_MODULES_PACK)
    api_modules = pack.create_script("TestApiModule", readme=None)
    Path(api_modules.readme.path).unlink()
    structue_validator = StructureValidator(api_modules.yml.path)
    content_entity_validator = ContentEntityValidator(structue_validator)
    assert content_entity_validator.validate_readme_exists()


@pytest.mark.parametrize(
    "with_test, support_level, expected_result",
    [(True, "xsoar", True), (False, "xsoar", False), (False, "community", True)],
)
def test_validate_unit_test_exists(
    repo, with_test: bool, support_level: str, expected_result: bool
):
    """
    Given:
    - A 'test pack' which contains / does not contain a 'test file'

    When:
    - Validating if an unittest file exists

    Then:
    - Ensure that False is being returned since unittest for the Python file was not found,
        or True is being returned since there's an unittest for the Python file.
         (Validation just for xsoar and partner support.)
    """
    pack = repo.create_pack(name="Test_Pack")
    integration = pack.create_integration("Test_Integration")
    structure_validator = StructureValidator(integration.yml.path)
    pack.pack_metadata.update({"support": support_level})
    path = Path(integration.code.path)
    if not with_test:
        path.with_name(f"{path.stem}_test.py").unlink(missing_ok=True)
    content_entity_validator = ContentEntityValidator(structure_validator)
    assert content_entity_validator.validate_unit_test_exists() == expected_result


FROM_AND_TO_VERSION_FOR_TEST = [
    ({}, "test.json", True),
    ({"fromVersion": "0.0.0"}, "test.json", True),
    ({"fromVersion": "1.32.45"}, "test.json", True),
    ({"toVersion": "21.32.44"}, "test.json", True),
    ({"toversion": "1.5"}, "test.yml", False),
    ({"toversion": "0.0.0", "fromversion": "1.32.45"}, "test.yml", True),
    ({"toversion": "0.0.0", "fromversion": "1.3_45"}, "test.yml", False),
    ({"toversion": "0.0.", "fromversion": "1.32.45"}, "test.yml", False),
    ({"toversion": "0.f.0"}, "test.yml", False),
    ({"toversion": "test"}, "test", "test is not json or yml type"),
    ({"toversion": ""}, "test.yml", True),
]


@pytest.mark.parametrize(
    "current_file, file_path, expected_result", FROM_AND_TO_VERSION_FOR_TEST
)
def test_are_fromversion_and_toversion_in_correct_format(
    mocker, current_file, file_path, expected_result
):

    mocker.patch.object(StructureValidator, "__init__", lambda a, b: None)
    structure = StructureValidator(file_path)
    structure.is_valid = True
    structure.scheme_name = "playbook"
    structure.file_path = file_path
    structure.current_file = current_file
    structure.old_file = None
    structure.prev_ver = "master"
    structure.branch_name = ""
    structure.specific_validations = None

    content_entity_validator = ContentEntityValidator(structure)
    mocker.patch.object(
        ContentEntityValidator, "handle_error", return_value=current_file
    )

    try:
        assert (
            content_entity_validator.are_fromversion_and_toversion_in_correct_format()
            == expected_result
        )
    except Exception as e:
        assert expected_result in str(e)


INPUTS_VALID_FROM_VERSION_MODIFIED = [
    (
        VALID_TEST_PLAYBOOK_PATH,
        INVALID_PLAYBOOK_PATH,
        False,
        "Valid from version marked as invalid",
    ),
    (
        INVALID_PLAYBOOK_PATH,
        VALID_PLAYBOOK_ID_PATH,
        False,
        "Invalid from version marked as valid.",
    ),
    (
        INVALID_PLAYBOOK_PATH,
        INVALID_PLAYBOOK_PATH,
        True,
        "From version did not changed but marked as changed.",
    ),
]


@pytest.mark.parametrize(
    "path, old_file_path, answer, error", INPUTS_VALID_FROM_VERSION_MODIFIED
)
def test_fromversion_update_validation_yml_structure(
    path, old_file_path, answer, error
):
    validator = ContentEntityValidator(StructureValidator(file_path=path))
    with open(old_file_path) as f:
        validator.old_file = yaml.load(f)
        assert validator.is_valid_fromversion_on_modified() is answer, error


@pytest.mark.parametrize(
    "old_pack_marketplaces,old_content_marketplaces,new_content_marketplaces,expected_valid",
    [
        pytest.param(
            ["1"], ["1"], ["1"], True, id="sanity, both match and are unchanged"
        ),
        pytest.param(
            ["1"],
            ["1"],
            ["1", "2"],
            True,
            id="pack&content had 1, added 2 to both",
        ),
        pytest.param(
            ["1"],
            [],
            ["1"],
            True,
            id="pack had 1, content had empty, added 1 to content",
        ),
        pytest.param(
            ["1"],
            [],
            ["2"],
            False,
            id="pack had 1, content had empty, added 2 to content",
        ),
        pytest.param(
            ["1"],
            ["1"],
            [],
            False,
            id="pack&content had 1, now content has empty",
        ),
    ],
)
def test_marketplaces_update_against_pack(
    mocker,
    old_pack_marketplaces: List[str],
    old_content_marketplaces: List[str],
    new_content_marketplaces: List[str],
    expected_valid: bool,
):
    old_pack = {"marketplaces": old_pack_marketplaces}

    old_content = {"marketplaces": old_content_marketplaces}
    new_content = {"marketplaces": new_content_marketplaces}

    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.content_entity_validator.get_remote_file",
        return_value=old_pack,
    )
    from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
        ContentEntityValidator,  # importing again to allow mocking get_remote_file
    )

    with TemporaryDirectory() as dir, open(file := Path(dir, "test.json"), "w") as f:
        json.dump(new_content, f)
        f.flush()
        validator = ContentEntityValidator(StructureValidator(file_path=str(file)))
        validator.old_file = old_content
        assert validator.is_valid_marketplaces_on_modified() is expected_valid


INPUTS_VALID_TOVERSION_MODIFIED = [
    (
        VALID_TEST_PLAYBOOK_PATH,
        VALID_TEST_PLAYBOOK_MARKETPLACES_PATH,
        False,
        "change toversion field is not allowed",
    ),
    (
        VALID_TEST_PLAYBOOK_PATH,
        VALID_TEST_PLAYBOOK_PATH,
        True,
        "toversion was not changed.",
    ),
]


@pytest.mark.parametrize(
    "path, old_file_path, answer, error", INPUTS_VALID_TOVERSION_MODIFIED
)
def test_toversion_update_validation_yml_structure(path, old_file_path, answer, error):
    validator = ContentEntityValidator(StructureValidator(file_path=path))
    with open(old_file_path) as f:
        validator.old_file = yaml.load(f)
        assert validator.is_valid_toversion_on_modified() is answer, error


INPUTS_IS_ID_MODIFIED = [
    (
        INVALID_PLAYBOOK_PATH,
        VALID_PLAYBOOK_ID_PATH,
        False,
        "Didn't find the id as updated in file",
    ),
    (
        VALID_PLAYBOOK_ID_PATH,
        VALID_PLAYBOOK_ID_PATH,
        True,
        "Found the ID as changed although it is not",
    ),
]


@pytest.mark.parametrize("current_file, old_file, answer, error", INPUTS_IS_ID_MODIFIED)
def test_is_id_not_modified(current_file, old_file, answer, error):
    validator = ContentEntityValidator(StructureValidator(file_path=current_file))
    with open(old_file) as f:
        validator.old_file = yaml.load(f)
        assert validator.is_id_not_modified() is answer, error


@pytest.mark.parametrize(
    "current_file, old_file, answer, error",
    INPUTS_VALID_FROM_VERSION_MODIFIED + INPUTS_IS_ID_MODIFIED,
)
def test_is_backward_compatible(current_file, old_file, answer, error):
    validator = ContentEntityValidator(StructureValidator(file_path=current_file))
    with open(old_file) as f:
        validator.old_file = yaml.load(f)
        assert validator.is_backward_compatible() is answer, error


def mock_handle_error(error_message, error_code, file_path):
    return error_message


@pytest.mark.parametrize(
    "rule_file_name, rule_type, rule_dict, expected_error, valid",
    [
        (
            "MyRuleModelingRules",
            MODELING_RULE,
            {"id": "modeling-rule", "name": "Modeling Rule"},
            "\nThe rule id should end with 'ModelingRule'",
            False,
        ),  # Wrong modeling rule id.
        (
            "MyRuleModelingRules",
            MODELING_RULE,
            {"id": "ModelingRule", "name": "Modeling-Rule"},
            "\nThe rule name should end with 'Modeling Rule'",
            False,
        ),  # Wrong modeling rule name.
        (
            "MyRuleModelingRules",
            MODELING_RULE,
            {"id": "ModelingRule", "name": "Modeling Rule"},
            "",
            True,
        ),  # Correct modeling rule id and name.
        (
            "MyRuleParsingRules",
            PARSING_RULE,
            {"id": "parsing-rule", "name": "Parsing Rule"},
            "\nThe rule id should end with 'ParsingRule'",
            False,
        ),  # Wrong parsing rule id.
        (
            "MyRuleParsingRules",
            PARSING_RULE,
            {"id": "ParsingRule", "name": "Parsing-Rule"},
            "\nThe rule name should end with 'Parsing Rule'",
            False,
        ),  # Wrong parsing rule name.
        (
            "MyRuleParsingRules",
            PARSING_RULE,
            {"id": "ParsingRule", "name": "Parsing Rule"},
            "",
            True,
        ),  # Correct parsing rule id and name.
    ],
)
def test_is_valid_rule_suffix(
    mocker, repo, rule_type, rule_file_name, rule_dict, expected_error, valid
):
    """
    Given: A modeling/parsing rule with valid/invalid file_name/id/name
    When: running is_valid_rule_suffix_name.
    Then: Validate that the modeling/parsing rule is valid/invalid and the message (in case of invalid) is as expected.
    """
    pack = repo.create_pack("TestPack")
    create_rule_function = {
        MODELING_RULE: pack.create_modeling_rule,
        PARSING_RULE: pack.create_parsing_rule,
    }[rule_type]
    dummy_rule = create_rule_function(rule_file_name, rule_dict)
    structure_validator = StructureValidator(dummy_rule.yml.path)
    error_message = mocker.patch(
        "demisto_sdk.commands.common.hook_validations.content_entity_validator.ContentEntityValidator.handle_error",
        side_effect=mock_handle_error,
    )

    with ChangeCWD(repo.path):
        rule_validator = ContentEntityValidator(structure_validator)
        assert rule_validator.is_valid_rule_suffix(rule_type) == valid
        if not valid:
            assert (
                error_message.call_args[0][0].split("is invalid:")[1] == expected_error
            )
