import pytest

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.hook_validations.conf_json import ConfJsonValidator

WITH_DESCRIPTION = {"test": "description"}
MISSING_DESCRIPTION = {"test": "", "test2": "description"}
TESTS_SECTION = [{"playbookID": "siri"}, {"playbookID": "alexa"}]


def test_conf_json_description(mocker):
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.conf_json.ConfJsonValidator.load_conf_file",
        return_value=None,
    )
    validator = ConfJsonValidator()

    assert validator.is_valid_description_in_conf_dict(
        checked_dict=WITH_DESCRIPTION
    ), "The conf validator couldn't find the description in the dictionary"


def test_conf_json_description_not_given(mocker):
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.conf_json.ConfJsonValidator.load_conf_file",
        return_value=None,
    )
    validator = ConfJsonValidator()

    assert (
        validator.is_valid_description_in_conf_dict(checked_dict=MISSING_DESCRIPTION)
        is False
    ), "The conf validator couldn't find the missing description in the dictionary"


def test_the_missing_existence_of_added_test_in_conf_json(mocker):
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.conf_json.ConfJsonValidator.load_conf_file",
        return_value={"tests": TESTS_SECTION},
    )
    validator = ConfJsonValidator()

    assert (
        validator.is_test_in_conf_json(file_id="cortana") is False
    ), "The conf validator didn't catch that the test is missing"


def test_the_existence_of_added_test_in_conf_json(mocker):
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.conf_json.ConfJsonValidator.load_conf_file",
        return_value={"tests": TESTS_SECTION},
    )
    validator = ConfJsonValidator()

    assert validator.is_test_in_conf_json(
        file_id="alexa"
    ), "The conf validator didn't catch the test although it exists in the test list"


def test_is_valid_conf_json_sanity_check(mocker):
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.conf_json.ConfJsonValidator.load_conf_file",
        return_value={
            "skipped_tests": WITH_DESCRIPTION,
            "skipped_integrations": WITH_DESCRIPTION,
            "unmockable_integrations": WITH_DESCRIPTION,
        },
    )
    validator = ConfJsonValidator()

    assert (
        validator.is_valid_conf_json()
    ), "The conf validator didn't find the description sections although they exist"


def test_is_valid_conf_json_negative_sanity_check(mocker):
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.conf_json.ConfJsonValidator.load_conf_file",
        return_value={
            "skipped_tests": WITH_DESCRIPTION,
            "skipped_integrations": MISSING_DESCRIPTION,
            "unmockable_integrations": MISSING_DESCRIPTION,
        },
    )
    validator = ConfJsonValidator()

    assert (
        validator.is_valid_conf_json() is False
    ), "The conf validator didn't find the missing description sections although they don't exist"


INTEGRATION_IS_SKIPPED_TEST_INPUTS = [
    (
        {
            "tests": [
                {"integrations": "SomeIntegration", "playbookID": "SomeTestPlaybook"}
            ],
            "skipped_tests": {"SomeTestPlaybook": "Some Issue"},
        },
        False,
    ),
    (
        {
            "tests": [
                {"integrations": "SomeIntegration", "playbookID": "SomeTestPlaybook"}
            ],
            "skipped_tests": {"SomeOtherTestPlaybook": "Some Issue"},
        },
        True,
    ),
    (
        {
            "tests": [
                {"integrations": "SomeIntegration", "playbookID": "SomeTestPlaybook"},
                {
                    "integrations": ["SomeIntegration", "SomeOtherIntegration"],
                    "playbookID": "SomeCombinedTestPlaybook",
                },
            ],
            "skipped_tests": {"SomeTestPlaybook": "Some Issue"},
        },
        True,
    ),
]


@pytest.mark.parametrize("conf_dict, answer", INTEGRATION_IS_SKIPPED_TEST_INPUTS)
def test_integration_has_unskipped_test_playbook(mocker, conf_dict, answer):
    """
    Given:
        - An integration.
        - conf file with configurations for the integration.

    When: running is_valid_file_in_conf_json specifically on integration.

    Then: Validate the integration has at least one unskipped test playbook.
    """
    mocker.patch.object(ConfJsonValidator, "load_conf_file", return_value=conf_dict)

    validator = ConfJsonValidator()
    current = {"commonfields": {"id": "SomeIntegration"}, "tests": ["SomeTestPlaybook"]}

    assert (
        validator.is_valid_file_in_conf_json(
            current_file=current,
            file_type=FileType.INTEGRATION,
            file_path="SomeFilePath",
        )
        is answer
    )


SCRIPT_IS_SKIPPED_TEST_INPUTS = [
    (
        ["SomeTestPlaybook"],
        {"skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
        False,
    ),
    (
        ["SomeTestPlaybook"],
        {"skipped_tests": {"SomeOtherTestPlaybook": "Some Issue"}},
        True,
    ),
    (
        ["SomeTestPlaybook", "SomeSecondTestPlaybook"],
        {"skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
        True,
    ),
]


@pytest.mark.parametrize(
    "test_playbooks, conf_dict, answer", SCRIPT_IS_SKIPPED_TEST_INPUTS
)
def test_script_has_unskipped_test_playbook(mocker, test_playbooks, conf_dict, answer):
    """
    Given:
        - A Script.
        - conf file with skipped tests.

    When: running is_valid_file_in_conf_json specifically on the script.

    Then: Validate the script has at least one unskipped test playbook.
    """
    mocker.patch.object(ConfJsonValidator, "load_conf_file", return_value=conf_dict)

    validator = ConfJsonValidator()

    current = {"commonfields": {"id": "SomeScript"}, "tests": test_playbooks}
    assert (
        validator.is_valid_file_in_conf_json(
            current_file=current, file_type=FileType.SCRIPT, file_path="SomeFilePath"
        )
        is answer
    )


def test_non_testable_entity_is_vaild_in_conf(mocker):
    """
    Given:
        - A content entity that cant have test playbooks, specifically a test playbook
        - Some conf file.

    When: running is_valid_file_in_conf_json specifically on the content entity.

    Then: Validate the content entity is valid in conf file.
    """
    mocker.patch.object(
        ConfJsonValidator,
        "load_conf_file",
        return_value={"skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
    )

    validator = ConfJsonValidator()

    current = {"id": "TheTestPlaybook"}
    assert validator.is_valid_file_in_conf_json(
        current_file=current, file_type=FileType.TEST_PLAYBOOK, file_path="SomeFilePath"
    )


NOT_SKIPPED_DYNAMIC_SECTION_INPUTS = [
    (
        {"skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
        {"tests": ["TestPlaybook"], "tags": ["dynamic-section"]},
    ),
    (
        {"skipped_tests": {"TestPlaybook": "Some Issue"}},
        {"tests": ["TestPlaybook"], "tags": ["dynamic-section"]},
    ),
    (
        {"skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
        {"tags": ["dynamic-section"]},
    ),
]


@pytest.mark.parametrize("conf_data, yml_data", NOT_SKIPPED_DYNAMIC_SECTION_INPUTS)
def test_not_skipped_test_playbook_for_dynamic_section(mocker, conf_data, yml_data):
    """
    Given:
    - Script data.
    - Conf JSON file.

    When:
    - running is_valid_file_in_conf_json specifically on the content entity with dynamic section tag.
    Cases:
        Case 1) Has not skipped TPB.
        Case 2) Has skipped TPB.
        Case 3) Does not have TPB.

    Then:
    - Ensure True is returned.
    """
    mocker.patch.object(ConfJsonValidator, "load_conf_file", return_value=conf_data)

    validator = ConfJsonValidator()

    assert validator.is_valid_file_in_conf_json(
        current_file=yml_data, file_type=FileType.SCRIPT, file_path="SomeFilePath"
    )


@pytest.mark.parametrize("has_tests", (True, False))
def test_has_unittests(mocker, integration, has_tests):
    from pathlib import Path

    mocker.patch.object(ConfJsonValidator, "load_conf_file", return_value={})
    validator = ConfJsonValidator()
    test_file = None
    try:
        if has_tests:
            test_file: Path = Path(integration.path) / (integration.name + "_test.py")
            test_file.touch()
        res = validator.has_unittest(integration.yml.path)
        assert res == has_tests
    finally:
        if test_file:
            test_file.unlink()  # Remove the file


def test_get_test_path(mocker, integration):
    mocker.patch.object(ConfJsonValidator, "load_conf_file", return_value={})
    validator = ConfJsonValidator()
    res = validator.get_test_path(integration.yml.path)
    assert res.parts[-1] == integration.name + "_test.py"
