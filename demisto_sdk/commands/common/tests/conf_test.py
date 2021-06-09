import pytest
from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.hook_validations.conf_json import \
    ConfJsonValidator

WITH_DESCRIPTION = {
    "test": "description"
}
MISSING_DESCRIPTION = {
    "test": "",
    "test2": "description"
}
TESTS_SECTION = [
    {
        "playbookID": "siri"
    },
    {
        "playbookID": "alexa"
    }
]

# TODO: Unskip


@pytest.mark.skip(reason="pending conf json fix")
def test_conf_json_description():
    validator = ConfJsonValidator()

    assert validator.is_valid_description_in_conf_dict(checked_dict=WITH_DESCRIPTION), \
        "The conf validator couldn't find the description in the dictionary"


@pytest.mark.skip(reason="pending conf json fix")
def test_conf_json_description_not_given():
    validator = ConfJsonValidator()

    assert validator.is_valid_description_in_conf_dict(checked_dict=MISSING_DESCRIPTION) is False, \
        "The conf validator couldn't find the missing description in the dictionary"


@pytest.mark.skip(reason="pending conf json fix")
def test_the_missing_existence_of_added_test_in_conf_json():
    validator = ConfJsonValidator()

    validator.conf_data = {
        "tests": TESTS_SECTION
    }

    assert validator.is_test_in_conf_json(file_id="cortana") is False, \
        "The conf validator didn't catch that the test is missing"


@pytest.mark.skip(reason="pending conf json fix")
def test_the_existence_of_added_test_in_conf_json():
    validator = ConfJsonValidator()

    validator.conf_data = {
        "tests": TESTS_SECTION
    }

    assert validator.is_test_in_conf_json(file_id="alexa"), \
        "The conf validator didn't catch the test although it exists in the test list"


@pytest.mark.skip(reason="pending conf json fix")
def test_is_valid_conf_json_sanity_check():
    validator = ConfJsonValidator()

    validator.conf_data = {
        "skipped_tests": WITH_DESCRIPTION,
        "skipped_integrations": WITH_DESCRIPTION,
        "unmockable_integrations": WITH_DESCRIPTION,
    }

    assert validator.is_valid_conf_json(), \
        "The conf validator didn't find the description sections although they exist"


@pytest.mark.skip(reason="pending conf json fix")
def test_is_valid_conf_json_negative_sanity_check():
    validator = ConfJsonValidator()

    validator.conf_data = {
        "skipped_tests": WITH_DESCRIPTION,
        "skipped_integrations": MISSING_DESCRIPTION,
        "unmockable_integrations": MISSING_DESCRIPTION
    }

    assert validator.is_valid_conf_json() is False, \
        "The conf validator didn't find the missing description sections although they don't exist"


INTEGRATION_IS_SKIPPED_TEST_INPUTS = [
    ({"tests": [{"integrations": "SomeIntegration", "playbookID": "SomeTestPlaybook"}],
      "skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
     False),
    ({"tests": [{"integrations": "SomeIntegration", "playbookID": "SomeTestPlaybook"}],
      "skipped_tests": {"SomeOtherTestPlaybook": "Some Issue"}},
     True),
    ({"tests": [{"integrations": "SomeIntegration", "playbookID": "SomeTestPlaybook"},
                {"integrations": ["SomeIntegration", "SomeOtherIntegration"],
                 "playbookID": "SomeCombinedTestPlaybook"}],
      "skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
     True)
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
    mocker.patch.object(ConfJsonValidator, 'load_conf_file', return_value=conf_dict)

    validator = ConfJsonValidator()
    current = {"commonfields": {"id": "SomeIntegration"}, "tests": ["SomeTestPlaybook"]}

    assert validator.is_valid_file_in_conf_json(current_file=current,
                                                file_type=FileType.INTEGRATION,
                                                file_path="SomeFilePath") is answer


SCRIPT_IS_SKIPPED_TEST_INPUTS = [
    (["SomeTestPlaybook"],
     {"skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
     False),
    (["SomeTestPlaybook"],
     {"skipped_tests": {"SomeOtherTestPlaybook": "Some Issue"}},
     True),
    (["SomeTestPlaybook", "SomeSecondTestPlaybook"],
     {"skipped_tests": {"SomeTestPlaybook": "Some Issue"}},
     True)
]


@pytest.mark.parametrize("test_playbooks, conf_dict, answer", SCRIPT_IS_SKIPPED_TEST_INPUTS)
def test_script_has_unskipped_test_playbook(mocker, test_playbooks, conf_dict, answer):
    """
    Given:
        - A Script.
        - conf file with skipped tests.

    When: running is_valid_file_in_conf_json specifically on the script.

    Then: Validate the script has at least one unskipped test playbook.
    """
    mocker.patch.object(ConfJsonValidator, 'load_conf_file', return_value=conf_dict)

    validator = ConfJsonValidator()

    current = {"commonfields": {"id": "SomeScript"}, "tests": test_playbooks}
    assert validator.is_valid_file_in_conf_json(current_file=current,
                                                file_type=FileType.SCRIPT,
                                                file_path="SomeFilePath") is answer
