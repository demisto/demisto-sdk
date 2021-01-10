from copy import deepcopy
from pathlib import Path

import pytest
from demisto_sdk.commands.common.constants import FETCH_REQUIRED_PARAMS
from demisto_sdk.commands.common.content.objects.pack_objects import (
    FEED_REQUIRED_PARAMS, Integration)
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object


def mock_integration(repo, create_unified=False):
    pack = repo.create_pack('Temp')
    integration = pack.create_integration(name='MyIntegration', unified=create_unified)
    integration.create_default_integration()
    return integration


class TestNotUnifiedIntegration:
    def test_objects_factory(self, repo):
        integration = mock_integration(repo)
        obj = path_to_pack_object(integration.yml.path)
        assert isinstance(obj, Integration)

    def test_prefix(self, datadir, repo):
        integration = mock_integration(repo)
        obj = Integration(integration.yml.path)
        assert obj.normalize_file_name() == "integration-MyIntegration.yml"

    def test_files_detection(self, datadir, repo):
        integration = mock_integration(repo)
        obj = Integration(integration.yml.path)
        assert obj.readme.path == Path(integration.readme.path)
        assert obj.code_path == Path(integration.code.path)
        assert obj.changelog.path == Path(integration.changelog.path)
        assert obj.description_path == Path(integration.description.path)
        assert obj.png_path == Path(integration.image.path)

    def test_is_unify(self, datadir, repo):
        integration = mock_integration(repo)
        obj = Integration(integration.yml.path)
        assert not obj.is_unify()

    SCRIPT_WITH_DOCKER_IMAGE_1 = {"script": {"dockerimage": "test"}}
    SCRIPT_WITH_DOCKER_IMAGE_2 = {"script": {"dockerimage": "test1"}}
    SCRIPT_WITH_NO_DOCKER_IMAGE = {"script": {"no": "dockerimage"}}
    EMPTY_CASE = {}  # type: dict[any, any]
    IS_DOCKER_IMAGE_CHANGED = [
        (SCRIPT_WITH_DOCKER_IMAGE_1, SCRIPT_WITH_NO_DOCKER_IMAGE, True),
        (SCRIPT_WITH_DOCKER_IMAGE_1, SCRIPT_WITH_DOCKER_IMAGE_2, True),
        (EMPTY_CASE, EMPTY_CASE, False),
        (EMPTY_CASE, SCRIPT_WITH_DOCKER_IMAGE_1, True),
        (SCRIPT_WITH_DOCKER_IMAGE_1, EMPTY_CASE, True)
    ]

    REQUIRED_FIELDS_FALSE = {"configuration": [{"name": "test", "required": False}]}
    REQUIRED_FIELDS_TRUE = {"configuration": [{"name": "test", "required": True}]}
    IS_ADDED_REQUIRED_FIELDS_INPUTS = [
        (REQUIRED_FIELDS_FALSE, REQUIRED_FIELDS_TRUE, False),
        (REQUIRED_FIELDS_TRUE, REQUIRED_FIELDS_FALSE, True),
        (REQUIRED_FIELDS_TRUE, REQUIRED_FIELDS_TRUE, False),
        (REQUIRED_FIELDS_FALSE, REQUIRED_FIELDS_FALSE, False)
    ]

    @pytest.mark.parametrize("current_file, old_file, answer", IS_ADDED_REQUIRED_FIELDS_INPUTS)
    def test_is_added_required_fields(self, current_file, old_file, answer, repo):
        integration = mock_integration(repo)
        integration.yml.update(current_file)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_added_required_fields(old_file) is answer

    IS_REMOVED_INTEGRATION_PARAMETERS_INPUTS = [
        ({"configuration": [{"name": "test"}]}, {"configuration": [{"name": "test"}]}, False),
        ({"configuration": [{"name": "test"}, {"name": "test2"}]}, {"configuration": [{"name": "test"}]}, False),
        ({"configuration": [{"name": "test"}]}, {"configuration": [{"name": "test"}, {"name": "test2"}]}, True),
        ({"configuration": [{"name": "test"}]}, {"configuration": [{"name": "old_param"}, {"name": "test2"}]}, True),
    ]

    @pytest.mark.parametrize("current_file, old_file, answer", IS_REMOVED_INTEGRATION_PARAMETERS_INPUTS)
    def test_is_removed_integration_parameters(self, current_file, old_file, answer, repo):
        """
        Given
        - integration configuration with different parameters

        When
        - running the validation is_removed_integration_parameters()

        Then
        - upon removal of parameters: it should set is_valid to False and return True
        - upon non removal or addition of parameters: it should set is_valid to True and return False
        """
        integration = mock_integration(repo)
        integration.yml.update(current_file)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_removed_integration_parameters(old_file) is answer

    CONFIGURATION_JSON_1 = {"configuration": [{"name": "test", "required": False}, {"name": "test1", "required": True}]}
    EXPECTED_JSON_1 = {"test": False, "test1": True}
    FIELD_TO_REQUIRED_INPUTS = [
        (CONFIGURATION_JSON_1, EXPECTED_JSON_1),
    ]

    @pytest.mark.parametrize("input_json, expected", FIELD_TO_REQUIRED_INPUTS)
    def test_get_field_to_required_dict_given_json(self, input_json, expected, repo):
        integration = mock_integration(repo)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj._get_field_to_required_dict(input_json) == expected

    @pytest.mark.parametrize("input_json, expected", FIELD_TO_REQUIRED_INPUTS)
    def test_get_field_to_required_dict_no_given_json(self, input_json, expected, repo):
        integration = mock_integration(repo)
        integration.yml.update(input_json)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj._get_field_to_required_dict() == expected

    IS_CONTEXT_CHANGED_OLD = [{"name": "test", "outputs": [{"contextPath": "test"}]}]
    IS_CONTEXT_CHANGED_NEW = [{"name": "test", "outputs": [{"contextPath": "test2"}]}]
    IS_CONTEXT_CHANGED_ADDED_PATH = [{"name": "test", "outputs": [{"contextPath": "test"}, {"contextPath": "test2"}]}]
    IS_CONTEXT_CHANGED_ADDED_COMMAND = [{"name": "test", "outputs": [{"contextPath": "test"}]},
                                        {"name": "test2", "outputs": [{"contextPath": "new command"}]}]
    IS_CONTEXT_CHANGED_NO_OUTPUTS = [{"name": "test"}]
    IS_CHANGED_CONTEXT_INPUTS = [
        (IS_CONTEXT_CHANGED_OLD, IS_CONTEXT_CHANGED_OLD, False),
        (IS_CONTEXT_CHANGED_NEW, IS_CONTEXT_CHANGED_OLD, True),
        (IS_CONTEXT_CHANGED_NEW, IS_CONTEXT_CHANGED_ADDED_PATH, True),
        (IS_CONTEXT_CHANGED_ADDED_PATH, IS_CONTEXT_CHANGED_NEW, False),
        (IS_CONTEXT_CHANGED_ADDED_COMMAND, IS_CONTEXT_CHANGED_OLD, False),
        (IS_CONTEXT_CHANGED_ADDED_COMMAND, IS_CONTEXT_CHANGED_NEW, True),
        (IS_CONTEXT_CHANGED_NO_OUTPUTS, IS_CONTEXT_CHANGED_NO_OUTPUTS, False),
        (IS_CONTEXT_CHANGED_NO_OUTPUTS, IS_CONTEXT_CHANGED_OLD, True),
    ]

    @pytest.mark.parametrize("current, old, answer", IS_CHANGED_CONTEXT_INPUTS)
    def test_is_changed_context_path(self, current, old, answer, repo):
        integration = mock_integration(repo)
        current = {'script': {'commands': current}}
        integration.yml.update(current)
        old = {'script': {'commands': old}}
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_changed_context_path(old) is answer

    CHANGED_COMMAND_INPUT_1 = [{"name": "test", "arguments": [{"name": "test"}]}]
    CHANGED_COMMAND_INPUT_2 = [{"name": "test", "arguments": [{"name": "test1"}]}]
    CHANGED_COMMAND_NAME_INPUT = [{"name": "test1", "arguments": [{"name": "test1"}]}]
    CHANGED_COMMAND_INPUT_ADDED_ARG = [{"name": "test", "arguments": [{"name": "test"}, {"name": "test1"}]}]
    CHANGED_COMMAND_INPUT_REQUIRED = [{"name": "test", "arguments": [{"name": "test", "required": True}]}]
    CHANGED_COMMAND_INPUT_ADDED_REQUIRED = [
        {"name": "test", "arguments": [{"name": "test"}, {"name": "test1", "required": True}]}]
    CHANGED_COMMAND_OR_ARG_INPUTS = [
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_REQUIRED, False),
        (CHANGED_COMMAND_INPUT_ADDED_REQUIRED, CHANGED_COMMAND_INPUT_1, True),
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_ADDED_REQUIRED, True),
        (CHANGED_COMMAND_INPUT_ADDED_ARG, CHANGED_COMMAND_INPUT_1, False),
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_ADDED_ARG, True),
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_2, True),
        (CHANGED_COMMAND_NAME_INPUT, CHANGED_COMMAND_INPUT_1, True),
        (CHANGED_COMMAND_NAME_INPUT, CHANGED_COMMAND_NAME_INPUT, False),
    ]

    @pytest.mark.parametrize("current, old, answer", CHANGED_COMMAND_OR_ARG_INPUTS)
    def test_is_changed_command_name_or_arg(self, current, old, answer, repo):
        integration = mock_integration(repo)
        current = {'script': {'commands': current}}
        integration.yml.update(current)
        old = {'script': {'commands': old}}
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_changed_command_name_or_arg(old) is answer

    WITHOUT_DUP = [{"name": "test"}, {"name": "test1"}]
    WITH_DUP = [{"name": "test"}, {"name": "test"}]
    DUPLICATE_PARAMS_INPUTS = [
        (WITHOUT_DUP, True),
        (WITH_DUP, False)
    ]

    @pytest.mark.parametrize("current, answer", DUPLICATE_PARAMS_INPUTS)
    def test_no_duplicate_params(self, current, answer, repo):
        integration = mock_integration(repo)
        current = {'configuration': current}
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_there_duplicate_params() is answer

    WITHOUT_DUP_ARGS = [{"name": "testing", "arguments": [{"name": "test1"}, {"name": "test2"}]}]
    WITH_DUP_ARGS = [{"name": "testing", "arguments": [{"name": "test1"}, {"name": "test1"}]}]
    DUPLICATE_ARGS_INPUTS = [
        (WITHOUT_DUP_ARGS, True),
        (WITH_DUP_ARGS, False)
    ]

    @pytest.mark.parametrize("current, answer", DUPLICATE_ARGS_INPUTS)
    def test_is_there_duplicate_args(self, current, answer, repo):
        current = {'script': {'commands': current}}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_there_duplicate_args() is answer

    PYTHON3_SUBTYPE = {
        "type": "python",
        "subtype": "python3"
    }
    PYTHON2_SUBTYPE = {
        "type": "python",
        "subtype": "python2"
    }

    BLA_BLA_SUBTYPE = {
        "type": "python",
        "subtype": "blabla"
    }
    INPUTS_SUBTYPE_TEST = [
        (PYTHON2_SUBTYPE, PYTHON3_SUBTYPE, True),
        (PYTHON3_SUBTYPE, PYTHON2_SUBTYPE, True),
        (PYTHON3_SUBTYPE, PYTHON3_SUBTYPE, False),
        (PYTHON2_SUBTYPE, PYTHON2_SUBTYPE, False)
    ]

    @pytest.mark.parametrize("current, old, answer", INPUTS_SUBTYPE_TEST)
    def test_is_changed_subtype(self, current, old, answer, repo):
        current, old = {'script': current}, {'script': old}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_changed_subtype(old) is answer

    INPUTS_VALID_SUBTYPE_TEST = [
        (PYTHON2_SUBTYPE, True),
        (PYTHON3_SUBTYPE, True),
        ({"type": "python", "subtype": "lies"}, False)
    ]

    @pytest.mark.parametrize("current, answer", INPUTS_VALID_SUBTYPE_TEST)
    def test_id_valid_subtype(self, current, answer, repo):
        current = {'script': current}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_subtype() is answer

    DEFUALT_ARGS_2 = [
        {"name": "email", "arguments": [{"name": "email", "required": False, "default": True}, {"name": "verbose"}]}]
    DEFUALT_ARGS_INVALID_1 = [{"name": "file", "required": True, "default": True}, {"name": "verbose"}]
    DEFUALT_ARGS_INVALID_2 = [
        {"name": "email", "arguments": [{"name": "email", "required": False, "default": False}, {"name": "verbose"}]}]
    DEFUALT_ARGS_INVALID_3 = [{"name": "file", "required": True, "default": False}, {"name": "verbose"}]
    DEFAULT_ARGS_INPUTS = [
        (DEFUALT_ARGS_2, True),
        (DEFUALT_ARGS_INVALID_1, False),
        (DEFUALT_ARGS_INVALID_2, False),
        (DEFUALT_ARGS_INVALID_3, False),
    ]

    @pytest.mark.parametrize("current, answer", DEFAULT_ARGS_INPUTS)
    def test_is_valid_default_arguments(self, current, answer, repo):
        current = {"script": {"commands": current}}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_default_arguments() is answer

    MOCK_REPUTATIONS_1 = [{"contextPath": "Int.lol", "description": "desc", "type": "number"},
                          {"contextPath": "DBotScore.lives.matter"}]
    MOCK_REPUTATIONS_2 = [{"name": "panorama-commit-status", "outputs": 1}]
    MOCK_REPUTATIONS_INVALID_EMAIL = [
        {"contextPath": "DBotScore.Indicator", "description": "The indicator that was tested.", "type": "string"},
        {"contextPath": "DBotScore.Type", "description": "The indicator type.", "type": "string"},
        {"contextPath": "DBotScore.Vendor", "description": "Vendor used to calculate the score.", "type": "string"},
        {"contextPath": "DBotScore.Sc0re", "description": "The actual score.", "type": "int"},
        {"contextPath": "Email.To", "description": "email to", "type": "string"}]
    MOCK_REPUTATIONS_INVALID_FILE = [
        {"contextPath": "DBotScore.Indicator", "description": "The indicator that was tested.", "type": "string"},
        {"contextPath": "DBotScore.Type", "description": "The indicator type.", "type": "string"},
        {"contextPath": "DBotScore.Vendor", "description": "Vendor used to calculate the score.", "type": "string"},
        {"contextPath": "DBotScore.Score", "description": "The actual score.", "type": "int"},
        {"contextPath": "File.Md5", "description": "The MD5 hash of the file.", "type": "string"}]
    MOCK_REPUTATIONS_VALID_IP = [
        {"contextPath": "DBotScore.Indicator", "description": "The indicator that was tested.", "type": "string"},
        {"contextPath": "DBotScore.Type", "description": "The indicator type.", "type": "string"},
        {"contextPath": "DBotScore.Vendor", "description": "Vendor used to calculate the score.", "type": "string"},
        {"contextPath": "DBotScore.Score", "description": "The actual score.", "type": "int"},
        {"contextPath": "IP.Address", "description": "IP address", "type": "string"}]
    IS_OUTPUT_FOR_REPUTATION_INPUTS = [
        (MOCK_REPUTATIONS_1, "not bang", True),
        (MOCK_REPUTATIONS_2, "not bang", True),
        (MOCK_REPUTATIONS_INVALID_EMAIL, "email", False),
        (MOCK_REPUTATIONS_INVALID_FILE, "file", False),
        (MOCK_REPUTATIONS_VALID_IP, "ip", True)
    ]

    @pytest.mark.parametrize("current, name, answer", IS_OUTPUT_FOR_REPUTATION_INPUTS)
    def test_is_outputs_for_reputations_commands_valid(self, current, name, answer, repo):
        current = {"script": {"commands": [{"name": name, "outputs": current}]}}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_outputs_for_reputations_commands_valid() is answer

    VALID_BETA = {"commonfields": {"id": "newIntegration"}, "name": "newIntegration",
                  "display": "newIntegration (Beta)", "beta": True}
    INVALID_BETA_DISPLAY = {"commonfields": {"id": "newIntegration"}, "name": "newIntegration",
                            "display": "newIntegration", "beta": True}
    INVALID_BETA_ID = {"commonfields": {"id": "newIntegration-beta"}, "name": "newIntegration",
                       "display": "newIntegration", "beta": True}
    INVALID_BETA_NAME = {"commonfields": {"id": "newIntegration"}, "name": "newIntegration (Beta)",
                         "display": "newIntegration", "beta": True}
    INVALID_BETA_ALL_BETA = {"commonfields": {"id": "newIntegration beta"}, "name": "newIntegration beta",
                             "display": "newIntegration (Beta)"}
    INVALID_BETA_CHANGED_NAME_NO_BETA_FIELD = {"commonfields": {"id": "newIntegration beta"},
                                               "name": "newIntegration beta",
                                               "display": "newIntegration changed (Beta)"}
    IS_VALID_BETA_INPUTS = [
        (VALID_BETA, True, True),
        (INVALID_BETA_DISPLAY, True, False),
        (INVALID_BETA_ID, True, False),
        (INVALID_BETA_NAME, True, False),
        (INVALID_BETA_ALL_BETA, INVALID_BETA_CHANGED_NAME_NO_BETA_FIELD, False),
    ]

    @pytest.mark.parametrize("current, old, answer", IS_VALID_BETA_INPUTS)
    def test_is_valid_beta_integration(self, current, old, answer, repo):
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_beta(old) is answer

    PROXY_VALID = [{"name": "proxy", "type": 8, "display": "Use system proxy settings", "required": False}]
    PROXY_WRONG_TYPE = [{"name": "proxy", "type": 9, "display": "Use system proxy settings", "required": False}]
    PROXY_WRONG_DISPLAY = [{"name": "proxy", "type": 8, "display": "bla", "required": False}]
    PROXY_WRONG_REQUIRED = [{"name": "proxy", "type": 8, "display": "Use system proxy settings", "required": True}]
    IS_PROXY_INPUTS = [
        (PROXY_VALID, True),
        (PROXY_WRONG_TYPE, False),
        (PROXY_WRONG_DISPLAY, False),
        (PROXY_WRONG_REQUIRED, False)
    ]

    @pytest.mark.parametrize("current, answer", IS_PROXY_INPUTS)
    def test_is_proxy_configured_correctly(self, current, answer, repo):
        current = {"configuration": current}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_proxy_configured_correctly() is answer

    UNSECURE_VALID = [
        {"name": "unsecure", "type": 8, "display": "Trust any certificate (not secure)", "required": False}]
    INSECURE_WRONG_DISPLAY = [
        {"name": "insecure", "type": 8, "display": "Use system proxy settings", "required": False}]
    UNSECURE_WRONG_DISPLAY = [
        {"name": "unsecure", "type": 8, "display": "Use system proxy settings", "required": False}]
    UNSECURE_WRONG_DISPLAY_AND_TYPE = [
        {"name": "unsecure", "type": 7, "display": "Use system proxy settings", "required": False}]
    IS_INSECURE_INPUTS = [
        (UNSECURE_VALID, True),
        (INSECURE_WRONG_DISPLAY, False),
        (UNSECURE_WRONG_DISPLAY, False),
        (UNSECURE_WRONG_DISPLAY_AND_TYPE, False)
    ]

    @pytest.mark.parametrize("current, answer", IS_INSECURE_INPUTS)
    def test_is_insecure_configured_correctly(self, current, answer, repo):
        current = {"configuration": current}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_insecure_configured_correctly() is answer

    VALID_CHECKBOX_PARAM = [
        {"name": "test1", "type": 8, "display": "test1", "required": False}]
    INVALID_CHECKBOX_PARAM = [
        {"name": "test2", "type": 8, "display": "test2", "required": True}]

    IS_INSECURE_INPUTS = [
        (VALID_CHECKBOX_PARAM, True),
        (INVALID_CHECKBOX_PARAM, False)
    ]

    @pytest.mark.parametrize("current, answer", IS_INSECURE_INPUTS)
    def test_is_checkbox_param_configured_correctly(self, current, answer, repo):
        current = {"configuration": current}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_checkbox_param_configured_correctly() is answer

    INVALID_CATEGORY = {"category": "Analytics & SIEMM"}
    VALID_CATEGORY1 = {"category": "Endpoint"}
    VALID_CATEGORY2 = {"category": "File Integrity Management"}

    IS_VALID_CATEGORY_INPUTS = [
        (VALID_CATEGORY1, True),
        (VALID_CATEGORY2, True),
        (INVALID_CATEGORY, False)
    ]

    @pytest.mark.parametrize("current, answer", IS_VALID_CATEGORY_INPUTS)
    def test_is_valid_category(self, current, answer, repo):
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_category() is answer

    VALID_DISPLAY_NON_HIDDEN = [
        {"name": "unsecure", "type": 8, "display": "Trust any certificate (not secure)", "required": False,
         "hidden": False}]
    VALID_DISPLAY_HIDDEN = [
        {"name": "insecure", "type": 8, "display": "Use system proxy settings", "required": False, "hidden": True}]
    INVALID_DISPLAY_NON_HIDDEN = [
        {"name": "unsecure", "type": 8, "display": "", "required": False, "hidden": False}]
    INVALID_NO_DISPLAY_NON_HIDDEN = [
        {"name": "unsecure", "type": 8, "required": False, "hidden": False}]
    VALID_NO_DISPLAY_TYPE_EXPIRATION = [
        {"name": "unsecure", "type": 17, "required": False, "hidden": False}]
    INVALID_DISPLAY_TYPE_EXPIRATION = [
        {"name": "unsecure", "type": 17, "display": "some display", "required": False, "hidden": False}]
    IS_VALID_DISPLAY_INPUTS = [
        (VALID_DISPLAY_NON_HIDDEN, False),
        (VALID_DISPLAY_HIDDEN, False),
        (INVALID_DISPLAY_NON_HIDDEN, True),
        (INVALID_DISPLAY_NON_HIDDEN, True),
        (VALID_NO_DISPLAY_TYPE_EXPIRATION, False),
        (INVALID_DISPLAY_TYPE_EXPIRATION, True),
        (FEED_REQUIRED_PARAMS, False),
    ]

    @pytest.mark.parametrize("configuration_setting, answer", IS_VALID_DISPLAY_INPUTS)
    def test_is_valid_display_configuration(self, configuration_setting, answer, repo):
        current = {"configuration": configuration_setting}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_not_valid_display_configuration() is not answer

    VALID_FEED = [
        # Valid feed
        (True, "5.5.0"),
        # No feed, including from version
        (False, "4.5.0"),
        # No feed, no from version
        (False, None),
        # No feed, fromversion 5.5
        (False, "5.5.0"),
    ]

    @pytest.mark.parametrize("feed, fromversion", VALID_FEED)
    def test_valid_feed(self, feed, fromversion, repo):
        current = {
            "script": {"feed": feed},
            "fromversion": fromversion,
            'configuration': deepcopy(FEED_REQUIRED_PARAMS)
        }
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_feed()

    INVALID_FEED = [
        # invalid from version
        (True, "5.0.0"),
        # Feed missing fromversion
        (True, None),
    ]

    @pytest.mark.parametrize("feed, fromversion", INVALID_FEED)
    def test_invalid_feed(self, feed, fromversion, repo):
        current = {"script": {"feed": feed}, "fromversion": fromversion}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert not integration_obj.is_valid_feed()

    V2_VALID = {"display": "integrationname v2", "name": "integrationname v2", "id": "integrationname v2"}
    V2_WRONG_DISPLAY_1 = {"display": "integrationname V2", "name": "integrationname V2", "id": "integrationname V2"}
    V2_WRONG_DISPLAY_2 = {"display": "integrationnameV2", "name": "integrationnameV2", "id": "integrationnameV2"}
    V2_WRONG_DISPLAY_3 = {"display": "integrationnamev2", "name": "integrationnamev2", "id": "integrationnamev2"}
    V2_NAME_INPUTS = [
        (V2_VALID, True),
        (V2_WRONG_DISPLAY_1, False),
        (V2_WRONG_DISPLAY_2, False),
        (V2_WRONG_DISPLAY_3, False)
    ]

    @pytest.mark.parametrize("current, answer", V2_NAME_INPUTS)
    def test_is_valid_display_name(self, current, answer, repo):
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_display_name() is answer

    def test_is_duplicate_description(self, repo):
        integration = mock_integration(repo)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_duplicate_description() is True

    def test_is_valid_fetch_valid(self, repo):
        current = {
            'configuration': deepcopy(FETCH_REQUIRED_PARAMS),
            'script': {'isfetch': True}
        }
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_fetch(), 'is_valid_fetch() returns False instead True'

    def test_is_valid_fetch_missing_param(self, repo):
        # missing param in configuration
        conf = deepcopy(FETCH_REQUIRED_PARAMS)
        conf = conf[:-1]
        current = {
            'configuration': conf,
            'script': {'isfetch': True}
        }
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_fetch() is False, 'is_valid_fetch() returns True instead False'

    def test_is_valid_fetch_malformed_field(self, capsys, repo):
        # incorrect param
        config = deepcopy(FETCH_REQUIRED_PARAMS)
        current = {
            'configuration': [],
            'script': {'isfetch': True}
        }
        for t in config:
            if t['name'] == 'incidentType':
                t['type'] = 123
            current['configuration'].append(t)
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_fetch() is False, 'is_valid_fetch() returns True instead False'
        captured = capsys.readouterr()
        out = captured.out
        assert "display: Incident type" in out
        assert "name: incidentType" in out
        assert "required: false" in out
        assert "type: 13" in out

    def test_is_valid_fetch_not_fetch(self, repo):
        current = {
            'configuration': deepcopy(FETCH_REQUIRED_PARAMS),
            'script': {'isfetch': False}
        }
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_fetch(), 'is_valid_fetch() returns False instead True'

    def test_all_feed_params_exist_valid(self, repo):
        current = {
            'configuration': deepcopy(FEED_REQUIRED_PARAMS),
            'script': {'feed': True}
        }
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.all_feed_params_exist(), 'all_feed_params_exist() returns False instead True'

    def test_all_feed_params_exist_missing_param(self, repo):
        # missing param in configuration
        conf = deepcopy(FEED_REQUIRED_PARAMS)
        conf = conf[:-1]
        current = {
            'configuration': conf,
            'script': {'feed': True}
        }
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.all_feed_params_exist() is False, 'is_valid_fetch() returns True instead False'

    def test_all_feed_params_exist_malformed_field(self, repo):
        # incorrect param
        current = {
            'configuration': [],
            'script': {'feed': True}
        }
        config = deepcopy(FEED_REQUIRED_PARAMS)
        for t in config:
            if not t.get('display'):
                t['type'] = 123
            current['configuration'].append(t)

        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)

        assert integration_obj.all_feed_params_exist() is False, 'all_feed_params_exist() returns True instead False'

    def test_all_feed_params_exist_hidden_feed_reputation_field(self, repo):
        # the feed reputation param is hidden
        current = {
            'configuration': [],
            'script': {'feed': True}
        }
        configuration = deepcopy(FEED_REQUIRED_PARAMS)
        for item in configuration:
            if item.get('name') == 'feedReputation':
                item['hidden'] = True
            current['configuration'].append(item)

        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.all_feed_params_exist() is True, \
            'all_feed_params_exist() returns False instead True for feedReputation param'

    NO_HIDDEN = {"configuration": [{"id": "new", "name": "new", "display": "test"}, {"d": "123", "n": "s", "r": True}]}
    HIDDEN_FALSE = {"configuration": [{"id": "n", "hidden": False}, {"display": "123", "name": "serer"}]}
    HIDDEN_TRUE = {"configuration": [{"id": "n", "n": "n"}, {"display": "123", "required": "false", "hidden": True}]}
    HIDDEN_TRUE_AND_FALSE = {"configuration": [{"id": "n", "hidden": False}, {"ty": "0", "r": "true", "hidden": True}]}
    HIDDEN_ALLOWED_TRUE = {"configuration": [{"name": "longRunning", "required": "false", "hidden": True}]}
    HIDDEN_ALLOWED_FEED_REPUTATION = {
        "configuration": [{"name": "feedReputation", "required": "false", "hidden": True}]}

    IS_VALID_HIDDEN_PARAMS = [
        (NO_HIDDEN, True),
        (HIDDEN_FALSE, True),
        (HIDDEN_TRUE, False),
        (HIDDEN_TRUE_AND_FALSE, False),
        (HIDDEN_ALLOWED_TRUE, True),
        (HIDDEN_ALLOWED_FEED_REPUTATION, True),
    ]

    @pytest.mark.parametrize("current, answer", IS_VALID_HIDDEN_PARAMS)
    def test_is_valid_hidden_params(self, current, answer, repo):
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_hidden_params() is answer

    @pytest.mark.parametrize("script_type, fromversion, res", [
        ('powershell', None, False),
        ('powershell', '4.5.0', False),
        ('powershell', '5.5.0', True),
        ('powershell', '5.5.1', True),
        ('powershell', '6.0.0', True),
        ('python', '', True),
        ('python', '4.5.0', True),
    ])
    def test_valid_pwsh(self, script_type, fromversion, res, repo):
        current = {
            "script": {"type": script_type},
            "fromversion": fromversion,
        }
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_pwsh() == res

    def test_empty_commands(self, repo):
        """
        Given: an integration with no commands

        When: running validate on integration with no command.

        Then: Validate it's valid.
        """
        current = {"script": {"commands": None}}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_valid_default_arguments() is True

    @pytest.mark.parametrize('param', [
        {'commands': ['something']},
        {'isFetch': True},
        {'longRunning': True},
        {'feed': True}
    ])
    def test_is_there_a_runnable(self, param, repo):
        """
        Given: one of any runnable integration

        When: running validate on integration with at least one of commands, fetch, feed or long-running

        Then: Validate it's valid.
        """
        current = {"script": param}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_there_a_runnable() is True

    def test_is_there_a_runnable_negative(self, repo):
        """
        Given: an integration with no runnable param

        When: running validate on integration with no one of commands, fetch, feed or long-running

        Then: Validate it's invalid.
        """
        current = {"script": {}}
        integration = mock_integration(repo)
        integration.yml.update(current)
        integration_obj = Integration(integration.yml.path)
        assert integration_obj.is_there_a_runnable() is False


class TestUnifiedIntegration:
    def test_objects_factory(self, datadir):
        obj = path_to_pack_object(datadir["integration-sample.yml"])
        assert isinstance(obj, Integration)

    def test_prefix(self, datadir):
        obj = Integration(datadir["integration-sample.yml"])
        assert obj.normalize_file_name() == "integration-sample.yml"

    def test_files_detection(self, datadir):
        obj = Integration(datadir["integration-sample.yml"])
        assert obj.readme.path == Path(datadir["integration-sample_README.md"])
        assert obj.changelog.path == Path(datadir["integration-sample_CHANGELOG.md"])

    def test_is_unify(self, datadir):
        obj = Integration(datadir["integration-sample.yml"])
        assert obj.is_unify()
