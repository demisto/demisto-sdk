import os
from copy import deepcopy
from typing import Optional

import pytest
from demisto_sdk.commands.common.constants import (FEED_REQUIRED_PARAMS,
                                                   FETCH_REQUIRED_PARAMS)
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from mock import patch


def mock_structure(file_path=None, current_file=None, old_file=None):
    # type: (Optional[str], Optional[dict], Optional[dict]) -> StructureValidator
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'integration'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        return structure


class TestIntegrationValidator:
    SCRIPT_WITH_DOCKER_IMAGE_1 = {"script": {"dockerimage": "test"}}
    SCRIPT_WITH_DOCKER_IMAGE_2 = {"script": {"dockerimage": "test1"}}
    SCRIPT_WITH_NO_DOCKER_IMAGE = {"script": {"no": "dockerimage"}}
    EMPTY_CASE = {}
    IS_DOCKER_IMAGE_CHANGED = [
        (SCRIPT_WITH_DOCKER_IMAGE_1, SCRIPT_WITH_NO_DOCKER_IMAGE, True),
        (SCRIPT_WITH_DOCKER_IMAGE_1, SCRIPT_WITH_DOCKER_IMAGE_2, True),
        (EMPTY_CASE, EMPTY_CASE, False),
        (EMPTY_CASE, SCRIPT_WITH_DOCKER_IMAGE_1, True),
        (SCRIPT_WITH_DOCKER_IMAGE_1, EMPTY_CASE, True)
    ]

    REQUIED_FIELDS_FALSE = {"configuration": [{"name": "test", "required": False}]}
    REQUIED_FIELDS_TRUE = {"configuration": [{"name": "test", "required": True}]}
    IS_ADDED_REQUIRED_FIELDS_INPUTS = [
        (REQUIED_FIELDS_FALSE, REQUIED_FIELDS_TRUE, False),
        (REQUIED_FIELDS_TRUE, REQUIED_FIELDS_FALSE, True),
        (REQUIED_FIELDS_TRUE, REQUIED_FIELDS_TRUE, False),
        (REQUIED_FIELDS_FALSE, REQUIED_FIELDS_FALSE, False)
    ]

    @pytest.mark.parametrize("current_file, old_file, answer", IS_ADDED_REQUIRED_FIELDS_INPUTS)
    def test_is_added_required_fields(self, current_file, old_file, answer):
        structure = mock_structure("", current_file, old_file)
        validator = IntegrationValidator(structure)
        assert validator.is_added_required_fields() is answer

    CONFIGURATION_JSON_1 = {"configuration": [{"name": "test", "required": False}, {"name": "test1", "required": True}]}
    EXPECTED_JSON_1 = {"test": False, "test1": True}
    FIELD_TO_REQUIRED_INPUTS = [
        (CONFIGURATION_JSON_1, EXPECTED_JSON_1),
    ]

    @pytest.mark.parametrize("input_json, expected", FIELD_TO_REQUIRED_INPUTS)
    def test_get_field_to_required_dict(self, input_json, expected):
        assert IntegrationValidator._get_field_to_required_dict(input_json) == expected

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
    def test_is_changed_context_path(self, current, old, answer):
        current = {'script': {'commands': current}}
        old = {'script': {'commands': old}}
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        assert validator.is_changed_context_path() is answer

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
    def test_is_changed_command_name_or_arg(self, current, old, answer):
        current = {'script': {'commands': current}}
        old = {'script': {'commands': old}}
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        assert validator.is_changed_command_name_or_arg() is answer

    WITHOUT_DUP = [{"name": "test"}, {"name": "test1"}]
    DUPLICATE_PARAMS_INPUTS = [
        (WITHOUT_DUP, False)
    ]

    @pytest.mark.parametrize("current, answer", DUPLICATE_PARAMS_INPUTS)
    def test_no_duplicate_params(self, current, answer):
        current = {'configuration': current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.is_there_duplicate_params() is answer

    @patch('demisto_sdk.commands.common.hook_validations.integration.print_error')
    def test_with_duplicate_params(self, print_error):
        """
        Given
        - integration configuratiton contains duplicate parameter (called test)

        When
        - running the validation is_there_duplicate_params()

        Then
        - it should set is_valid to False
        - it should return True (there are duplicate params)
        - it should print an error message that contains the duplicated param name
        """
        # from demisto_sdk.commands.common.tools import print_error
        # mocker.patch(tools, 'print_error')

        current = {
            'configuration': [
                {'name': 'test'},
                {'name': 'test'}
            ]
        }
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)

        assert validator.is_there_duplicate_params() is True
        assert validator.is_valid is False

    WITHOUT_DUP_ARGS = [{"name": "testing", "arguments": [{"name": "test1"}, {"name": "test2"}]}]
    WITH_DUP_ARGS = [{"name": "testing", "arguments": [{"name": "test1"}, {"name": "test1"}]}]
    DUPLICATE_ARGS_INPUTS = [
        (WITHOUT_DUP_ARGS, False),
        (WITH_DUP_ARGS, True)
    ]

    @pytest.mark.parametrize("current, answer", DUPLICATE_ARGS_INPUTS)
    def test_is_there_duplicate_args(self, current, answer):
        current = {'script': {'commands': current}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.is_there_duplicate_args() is answer

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
    def test_is_changed_subtype(self, current, old, answer):
        current, old = {'script': current}, {'script': old}
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        assert validator.is_changed_subtype() is answer

    INPUTS_VALID_SUBTYPE_TEST = [
        (PYTHON2_SUBTYPE, True),
        (PYTHON3_SUBTYPE, True),
        ({"type": "python", "subtype": "lies"}, False)
    ]

    @pytest.mark.parametrize("current, answer", INPUTS_VALID_SUBTYPE_TEST)
    def test_id_valid_subtype(self, current, answer):
        current = {'script': current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_subtype() is answer

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
    def test_is_valid_default_arguments(self, current, answer):
        current = {"script": {"commands": current}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_default_arguments() is answer

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
    def test_is_outputs_for_reputations_commands_valid(self, current, name, answer):
        current = {"script": {"commands": [{"name": name, "outputs": current}]}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_outputs_for_reputations_commands_valid() is answer

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
    def test_is_valid_beta_integration(self, current, old, answer):
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        validator.old_file = old
        assert validator.is_valid_beta() is answer

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
    def test_is_proxy_configured_correctly(self, current, answer):
        current = {"configuration": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_proxy_configured_correctly() is answer

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
    def test_is_insecure_configured_correctly(self, current, answer):
        current = {"configuration": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_insecure_configured_correctly() is answer

    VALID_CHECKBOX_PARAM = [
        {"name": "test1", "type": 8, "display": "test1", "required": False}]
    INVALID_CHECKBOX_PARAM = [
        {"name": "test2", "type": 8, "display": "test2", "required": True}]

    IS_INSECURE_INPUTS = [
        (VALID_CHECKBOX_PARAM, True),
        (INVALID_CHECKBOX_PARAM, False)
    ]

    @pytest.mark.parametrize("current, answer", IS_INSECURE_INPUTS)
    def test_is_checkbox_param_configured_correctly(self, current, answer):
        current = {"configuration": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_checkbox_param_configured_correctly() is answer

    INVALID_CATEGORY = {"category": "Analytics & SIEMM"}
    VALID_CATEGORY = {"category": "Endpoint"}
    IS_VALID_CATEGORY_INPUTS = [
        (VALID_CATEGORY, True),
        (INVALID_CATEGORY, False)
    ]

    @pytest.mark.parametrize("current, answer", IS_VALID_CATEGORY_INPUTS)
    def test_is_valid_category(self, current, answer):
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_category() is answer

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
        (VALID_DISPLAY_NON_HIDDEN, True),
        (VALID_DISPLAY_HIDDEN, True),
        (INVALID_DISPLAY_NON_HIDDEN, False),
        (INVALID_DISPLAY_NON_HIDDEN, False),
        (VALID_NO_DISPLAY_TYPE_EXPIRATION, True),
        (INVALID_DISPLAY_TYPE_EXPIRATION, False),
        (FEED_REQUIRED_PARAMS, True),
    ]

    @pytest.mark.parametrize("configuration_setting, answer", IS_VALID_DISPLAY_INPUTS)
    def test_is_valid_display_configuration(self, configuration_setting, answer):
        current = {"configuration": configuration_setting}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_not_valid_display_configuration() is not answer

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
    def test_valid_feed(self, feed, fromversion):
        current = {
            "script": {"feed": feed},
            "fromversion": fromversion,
            'configuration': deepcopy(FEED_REQUIRED_PARAMS)
        }
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_feed()

    INVALID_FEED = [
        # invalid from version
        (True, "5.0.0"),
        # Feed missing fromversion
        (True, None),
    ]

    @pytest.mark.parametrize("feed, fromversion", INVALID_FEED)
    def test_invalid_feed(self, feed, fromversion):
        current = {"script": {"feed": feed}, "fromversion": fromversion}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert not validator.is_valid_feed()

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
    def test_is_valid_display_name(self, current, answer):
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_display_name() is answer

    def test_is_valid_description_positive(self):
        integration_path = os.path.normpath(
            os.path.join(f'{git_path()}/demisto_sdk/tests', 'test_files', 'integration-Zoom.yml')
        )
        structure = mock_structure(file_path=integration_path)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_description() is True


class TestIsFetchParamsExist:
    def setup(self):
        config = {
            'configuration': deepcopy(FETCH_REQUIRED_PARAMS),
            'script': {'isfetch': True}
        }
        self.validator = IntegrationValidator(mock_structure("", config))

    def test_valid(self):
        assert self.validator.is_valid_fetch(), 'is_valid_fetch() returns False instead True'

    def test_sanity(self):
        # missing param in configuration
        self.validator.current_file['configuration'] = [t for t in self.validator.current_file['configuration']
                                                        if t['name'] != 'incidentType']
        assert self.validator.is_valid_fetch() is False, 'is_valid_fetch() returns True instead False'

    def test_missing_field(self):
        # missing param
        for i, t in enumerate(self.validator.current_file['configuration']):
            if t['name'] == 'incidentType':
                del self.validator.current_file['configuration'][i]['name']
        print(self.validator.current_file['configuration'])
        assert self.validator.is_valid_fetch() is False, 'is_valid_fetch() returns True instead False'

    def test_malformed_field(self, capsys):
        # incorrect param
        config = self.validator.current_file['configuration']
        self.validator.current_file['configuration'] = []
        for t in config:
            if t['name'] == 'incidentType':
                t['type'] = 123
            self.validator.current_file['configuration'].append(t)

        assert self.validator.is_valid_fetch() is False, 'is_valid_fetch() returns True instead False'
        captured = capsys.readouterr()
        out = captured.out
        print(out)
        assert "display: Incident type" in out
        assert "name: incidentType" in out
        assert "required: false" in out
        assert "type: 13" in out

    def test_not_fetch(self, capsys):
        self.test_malformed_field(capsys)
        self.validator.is_valid = True
        self.validator.current_file['script']['isfetch'] = False
        assert self.validator.is_valid_fetch(), 'is_valid_fetch() returns False instead True'


class TestIsFeedParamsExist:

    def setup(self):
        config = {
            'configuration': deepcopy(FEED_REQUIRED_PARAMS),
            'script': {'feed': True}
        }
        self.validator = IntegrationValidator(mock_structure("", config))

    def test_valid(self):
        assert self.validator.all_feed_params_exist(), 'all_feed_params_exist() returns False instead True'

    def test_sanity(self):
        # missing param in configuration
        self.validator.current_file['configuration'] = [t for t in self.validator.current_file['configuration']
                                                        if not t.get('display')]
        assert self.validator.all_feed_params_exist() is False, 'all_feed_params_exist() returns True instead False'

    def test_missing_field(self):
        # missing param
        configuration = self.validator.current_file['configuration']
        for i in range(len(configuration)):
            if not configuration[i].get('display'):
                del configuration[i]['name']
        self.validator.current_file['configuration'] = configuration
        assert self.validator.all_feed_params_exist() is False, 'all_feed_params_exist() returns True instead False'

    def test_malformed_field(self):
        # incorrect param
        self.validator.current_file['configuration'] = []
        for t in self.validator.current_file['configuration']:
            if not t.get('display'):
                t['type'] = 123
            self.validator.current_file['configuration'].append(t)

        assert self.validator.all_feed_params_exist() is False, 'all_feed_params_exist() returns True instead False'

    NO_HIDDEN = {"configuration": [{"id": "new", "name": "new", "display": "test"}, {"d": "123", "n": "s", "r": True}]}
    HIDDEN_FALSE = {"configuration": [{"id": "n", "hidden": False}, {"display": "123", "name": "serer"}]}
    HIDDEN_TRUE = {"configuration": [{"id": "n", "n": "n"}, {"display": "123", "required": "false", "hidden": True}]}
    HIDDEN_TRUE_AND_FALSE = {"configuration": [{"id": "n", "hidden": False}, {"ty": "0", "r": "true", "hidden": True}]}
    HIDDEN_ALLOWED_TRUE = {"configuration": [{"name": "longRunning", "required": "false", "hidden": True}]}
    IS_VALID_HIDDEN_PARAMS = [
        (NO_HIDDEN, True),
        (HIDDEN_FALSE, True),
        (HIDDEN_TRUE, False),
        (HIDDEN_TRUE_AND_FALSE, False),
        (HIDDEN_ALLOWED_TRUE, True)
    ]

    @pytest.mark.parametrize("current, answer", IS_VALID_HIDDEN_PARAMS)
    def test_is_valid_hidden_params(self, current, answer):
        structure = mock_structure(current_file=current)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_hidden_params() is answer

    @pytest.mark.parametrize("script_type, fromversion, res", [
        ('powershell', None, False),
        ('powershell', '4.5.0', False),
        ('powershell', '5.5.0', True),
        ('powershell', '5.5.1', True),
        ('powershell', '6.0.0', True),
        ('python', '', True),
        ('python', '4.5.0', True),
    ])
    def test_valid_pwsh(self, script_type, fromversion, res):
        current = {
            "script": {"type": script_type},
            "fromversion": fromversion,
        }
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_pwsh() == res
