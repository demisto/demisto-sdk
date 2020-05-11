import json
import os

from demisto_sdk.commands.common.git_tools import git_path
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
CONF_PATH = os.path.normpath(
    os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files', 'conf.json'))


def load_conf_file():
    with open(CONF_PATH) as data_file:
        return json.load(data_file)


# @pytest.mark.skip(reason="pending conf json fix")
def test_conf_json_description(mocker):
    mocker.patch.object(ConfJsonValidator, 'load_conf_file',
                        return_value=load_conf_file())
    validator = ConfJsonValidator()

    assert validator.is_valid_description_in_conf_dict(checked_dict=WITH_DESCRIPTION), \
        "The conf validator couldn't find the description in the dictionary"


# @pytest.mark.skip(reason="pending conf json fix")
def test_conf_json_description_not_given(mocker):
    mocker.patch.object(ConfJsonValidator, 'load_conf_file',
                        return_value=load_conf_file())
    validator = ConfJsonValidator()

    assert validator.is_valid_description_in_conf_dict(checked_dict=MISSING_DESCRIPTION) is False, \
        "The conf validator couldn't find the missing description in the dictionary"


# @pytest.mark.skip(reason="pending conf json fix")
def test_the_missing_existence_of_added_test_in_conf_json(mocker):
    mocker.patch.object(ConfJsonValidator, 'load_conf_file',
                        return_value=load_conf_file())
    validator = ConfJsonValidator()

    validator.conf_data = {
        "tests": TESTS_SECTION
    }

    assert validator.is_test_in_conf_json(file_id="cortana") is False, \
        "The conf validator didn't catch that the test is missing"


# @pytest.mark.skip(reason="pending conf json fix")
def test_the_existence_of_added_test_in_conf_json(mocker):
    mocker.patch.object(ConfJsonValidator, 'load_conf_file',
                        return_value=load_conf_file())
    validator = ConfJsonValidator()

    validator.conf_data = {
        "tests": TESTS_SECTION
    }

    assert validator.is_test_in_conf_json(file_id="alexa"), \
        "The conf validator didn't catch the test although it exists in the test list"


# @pytest.mark.skip(reason="pending conf json fix")
def test_is_valid_conf_json_sanity_check(mocker):
    mocker.patch.object(ConfJsonValidator, 'load_conf_file',
                        return_value=load_conf_file())
    validator = ConfJsonValidator()

    validator.conf_data = {
        "skipped_tests": WITH_DESCRIPTION,
        "skipped_integrations": WITH_DESCRIPTION,
        "unmockable_integrations": WITH_DESCRIPTION,
    }

    assert validator.is_valid_conf_json(), \
        "The conf validator didn't find the description sections although they exist"


# @pytest.mark.skip(reason="pending conf json fix")
def test_is_valid_conf_json_negative_sanity_check(mocker):
    mocker.patch.object(ConfJsonValidator, 'load_conf_file',
                        return_value=load_conf_file())
    validator = ConfJsonValidator()

    validator.conf_data = {
        "skipped_tests": WITH_DESCRIPTION,
        "skipped_integrations": MISSING_DESCRIPTION,
        "unmockable_integrations": MISSING_DESCRIPTION
    }

    assert validator.is_valid_conf_json() is False, \
        "The conf validator didn't find the missing description sections although they don't exist"
