import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import mock_open, patch

import pytest

from demisto_sdk.commands.common.constants import (
    ALERT_FETCH_REQUIRED_PARAMS,
    FEED_REQUIRED_PARAMS,
    FIRST_FETCH_PARAM,
    INCIDENT_FETCH_REQUIRED_PARAMS,
    MAX_FETCH_PARAM,
    PARTNER_SUPPORT,
    SUPPORT_LEVEL_HEADER,
    XSOAR_SUPPORT,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.default_additional_info_loader import (
    load_default_additional_info_dict,
)
from demisto_sdk.commands.common.hook_validations.integration import (
    IntegrationValidator,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from TestSuite.integration import Integration
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list

default_additional_info = load_default_additional_info_dict()


def build_feed_required_params():
    params = []
    for required_param in FEED_REQUIRED_PARAMS:
        must_be_one_of = {
            key: val[-1] if isinstance(val, list) else val
            for key, val in required_param.get("must_be_one_of").items()
        }
        params.append(
            dict(
                required_param.get("must_equal"),
                **required_param.get("must_contain"),
                name=required_param.get("name"),
                **must_be_one_of,
            )
        )
    return params


FEED_REQUIRED_PARAMS_STRUCTURE = build_feed_required_params()


def mock_structure(
    file_path: Optional[str] = None,
    current_file: Optional[dict] = None,
    old_file: Optional[dict] = None,
    quiet_bc: Optional[bool] = False,
) -> StructureValidator:
    with patch.object(StructureValidator, "__init__", lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = "integration"
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = "master"
        structure.branch_name = ""
        structure.quiet_bc = quiet_bc
        structure.specific_validations = None
        return structure


class TestIntegrationValidator:
    SCRIPT_WITH_DOCKER_IMAGE_1 = {"script": {"dockerimage": "test"}}
    SCRIPT_WITH_DOCKER_IMAGE_2 = {"script": {"dockerimage": "test1"}}
    SCRIPT_WITH_NO_DOCKER_IMAGE = {"script": {"no": "dockerimage"}}
    EMPTY_CASE: Dict[Any, Any] = {}
    IS_DOCKER_IMAGE_CHANGED = [
        (SCRIPT_WITH_DOCKER_IMAGE_1, SCRIPT_WITH_NO_DOCKER_IMAGE, True),
        (SCRIPT_WITH_DOCKER_IMAGE_1, SCRIPT_WITH_DOCKER_IMAGE_2, True),
        (EMPTY_CASE, EMPTY_CASE, False),
        (EMPTY_CASE, SCRIPT_WITH_DOCKER_IMAGE_1, True),
        (SCRIPT_WITH_DOCKER_IMAGE_1, EMPTY_CASE, True),
    ]

    REQUIED_FIELDS_FALSE = {"configuration": [{"name": "test", "required": False}]}
    REQUIED_FIELDS_TRUE = {"configuration": [{"name": "test", "required": True}]}
    NO_ADDED_REQUIRED_FIELDS_INPUTS = [
        (REQUIED_FIELDS_FALSE, REQUIED_FIELDS_TRUE, True),
        (REQUIED_FIELDS_TRUE, REQUIED_FIELDS_FALSE, False),
        (REQUIED_FIELDS_TRUE, REQUIED_FIELDS_TRUE, True),
        (REQUIED_FIELDS_FALSE, REQUIED_FIELDS_FALSE, True),
    ]

    @pytest.mark.parametrize(
        "current_file, old_file, answer", NO_ADDED_REQUIRED_FIELDS_INPUTS
    )
    def test_no_added_required_fields(self, current_file, old_file, answer):
        structure = mock_structure("", current_file, old_file)
        validator = IntegrationValidator(structure)
        assert validator.no_added_required_fields() is answer
        structure.quiet_bc = True
        assert (
            validator.no_added_required_fields() is True
        )  # if quiet_bc is true should always succeed

    NO_CHANGED_REMOVED_YML_FIELDS_INPUTS = [
        (
            {"script": {"isfetch": True, "feed": False}},
            {"script": {"isfetch": True, "feed": False}},
            True,
        ),
        (
            {"script": {"isfetch": True}},
            {"script": {"isfetch": True, "feed": False}},
            True,
        ),
        (
            {"script": {"isfetch": False, "feed": False}},
            {"script": {"isfetch": True, "feed": False}},
            False,
        ),
        (
            {"script": {"feed": False}},
            {"script": {"isfetch": True, "feed": False}},
            False,
        ),
    ]

    @pytest.mark.parametrize(
        "current_file, old_file, answer", NO_CHANGED_REMOVED_YML_FIELDS_INPUTS
    )
    def test_no_changed_removed_yml_fields(self, current_file, old_file, answer):
        """
        Given
        - integration script with different fields

        When
        - running the validation no_changed_removed_yml_fields()

        Then
        - upon removal or change of some fields from true to false: it should set is_valid to False and return False
        - upon non removal or change of some fields from true to false: it should set is_valid to True and return True
        """

        structure = mock_structure("", current_file, old_file)
        validator = IntegrationValidator(structure)
        assert validator.no_changed_removed_yml_fields() is answer
        assert validator.is_valid is answer
        structure.quiet_bc = True
        assert (
            validator.no_changed_removed_yml_fields() is True
        )  # if quiet_bc is true should always succeed

    NO_REMOVED_INTEGRATION_PARAMETERS_INPUTS = [
        (
            {"configuration": [{"name": "test"}]},
            {"configuration": [{"name": "test"}]},
            True,
        ),
        (
            {"configuration": [{"name": "test"}, {"name": "test2"}]},
            {"configuration": [{"name": "test"}]},
            True,
        ),
        (
            {"configuration": [{"name": "test"}]},
            {"configuration": [{"name": "test"}, {"name": "test2"}]},
            False,
        ),
        (
            {"configuration": [{"name": "test"}]},
            {"configuration": [{"name": "old_param"}, {"name": "test2"}]},
            False,
        ),
    ]

    @pytest.mark.parametrize(
        "current_file, old_file, answer", NO_REMOVED_INTEGRATION_PARAMETERS_INPUTS
    )
    def test_no_removed_integration_parameters(self, current_file, old_file, answer):
        """
        Given
        - integration configuration with different parameters

        When
        - running the validation no_removed_integration_parameters()

        Then
        - upon removal of parameters: it should set is_valid to False and return False
        - upon non removal or addition of parameters: it should set is_valid to True and return True
        """
        structure = mock_structure("", current_file, old_file)
        validator = IntegrationValidator(structure)
        assert validator.no_removed_integration_parameters() is answer
        assert validator.is_valid is answer
        structure.quiet_bc = True
        assert (
            validator.no_removed_integration_parameters() is True
        )  # if quiet_bc is true should always succeed

    CONFIGURATION_JSON_1 = {
        "configuration": [
            {"name": "test", "required": False},
            {"name": "test1", "required": True},
        ]
    }
    EXPECTED_JSON_1 = {"test": False, "test1": True}
    FIELD_TO_REQUIRED_INPUTS = [
        (CONFIGURATION_JSON_1, EXPECTED_JSON_1),
    ]

    @pytest.mark.parametrize("input_json, expected", FIELD_TO_REQUIRED_INPUTS)
    def test_get_field_to_required_dict(self, input_json, expected):
        assert IntegrationValidator._get_field_to_required_dict(input_json) == expected

    IS_CONTEXT_CHANGED_OLD = [{"name": "test", "outputs": [{"contextPath": "test"}]}]
    IS_CONTEXT_CHANGED_NEW = [{"name": "test", "outputs": [{"contextPath": "test2"}]}]
    IS_CONTEXT_CHANGED_ADDED_PATH = [
        {"name": "test", "outputs": [{"contextPath": "test"}, {"contextPath": "test2"}]}
    ]
    IS_CONTEXT_CHANGED_ADDED_COMMAND = [
        {"name": "test", "outputs": [{"contextPath": "test"}]},
        {"name": "test2", "outputs": [{"contextPath": "new command"}]},
    ]
    IS_CONTEXT_CHANGED_NO_OUTPUTS = [{"name": "test"}]
    MULTIPLE_CHANGES_OLD = [
        {"name": "command1", "outputs": [{"contextPath": "old_command1_path"}]},
        {"name": "command2", "outputs": [{"contextPath": "old_command2_path"}]},
    ]
    MULTIPLE_CHANGES_NEW = [
        {"name": "command1", "outputs": [{"contextPath": "new_command1_path"}]},
        {"name": "command2", "outputs": [{"contextPath": "new_command2_path"}]},
    ]
    MULTIPLE_COMMANDS_NO_OUTPUTS_ONE = [
        {"name": "command1", "outputs": [{"contextPath": "old_command1_path"}]},
        {"name": "command2"},
    ]
    MULTIPLE_COMMANDS_NO_OUTPUTS_ALL = [{"name": "command1"}, {"name": "command2"}]
    IS_CHANGED_CONTEXT_INPUTS = [
        pytest.param(
            IS_CONTEXT_CHANGED_OLD, IS_CONTEXT_CHANGED_OLD, True, [], id="no change"
        ),
        pytest.param(
            IS_CONTEXT_CHANGED_NEW,
            IS_CONTEXT_CHANGED_OLD,
            False,
            ["test"],
            id="context path change",
        ),
        pytest.param(
            IS_CONTEXT_CHANGED_NEW,
            IS_CONTEXT_CHANGED_ADDED_PATH,
            False,
            ["test"],
            id="removed context path",
        ),
        pytest.param(
            IS_CONTEXT_CHANGED_ADDED_PATH,
            IS_CONTEXT_CHANGED_NEW,
            True,
            [],
            id="added context path",
        ),
        pytest.param(
            IS_CONTEXT_CHANGED_ADDED_COMMAND,
            IS_CONTEXT_CHANGED_OLD,
            True,
            [],
            id="added new command",
        ),
        pytest.param(
            IS_CONTEXT_CHANGED_ADDED_COMMAND,
            IS_CONTEXT_CHANGED_NEW,
            False,
            ["test"],
            id="added new command and changed context of old command",
        ),
        pytest.param(
            IS_CONTEXT_CHANGED_NO_OUTPUTS,
            IS_CONTEXT_CHANGED_NO_OUTPUTS,
            True,
            [],
            id="no change with no outputs",
        ),
        pytest.param(
            IS_CONTEXT_CHANGED_NO_OUTPUTS,
            IS_CONTEXT_CHANGED_OLD,
            False,
            ["test"],
            id="deleted command outputs",
        ),
        pytest.param(
            MULTIPLE_CHANGES_NEW,
            MULTIPLE_CHANGES_OLD,
            False,
            ["command1", "command2"],
            id="context changes in multiple commands",
        ),
        pytest.param(
            MULTIPLE_COMMANDS_NO_OUTPUTS_ONE,
            MULTIPLE_CHANGES_OLD,
            False,
            ["command2"],
            id="no changes in one command output and deleted outputs for other command",
        ),
        pytest.param(
            MULTIPLE_COMMANDS_NO_OUTPUTS_ALL,
            MULTIPLE_CHANGES_OLD,
            False,
            ["command1", "command2"],
            id="deleted outputs for two command",
        ),
    ]

    @pytest.mark.parametrize(
        "current, old, answer, changed_command_names", IS_CHANGED_CONTEXT_INPUTS
    )
    def test_no_change_to_context_path(
        self, current, old, answer, changed_command_names, mocker
    ):
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        current = {"script": {"commands": current}}
        old = {"script": {"commands": old}}
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        assert validator.no_change_to_context_path() is answer
        for changed_command_name in changed_command_names:
            assert str_in_call_args_list(
                logger_error.call_args_list, changed_command_name
            )
        structure.quiet_bc = True
        assert (
            validator.no_change_to_context_path() is True
        )  # if quiet_bc is true should always succeed

    CHANGED_COMMAND_INPUT_1 = [{"name": "test", "arguments": [{"name": "test"}]}]
    CHANGED_COMMAND_INPUT_2 = [{"name": "test", "arguments": [{"name": "test1"}]}]
    CHANGED_COMMAND_NAME_INPUT = [{"name": "test1", "arguments": [{"name": "test1"}]}]
    CHANGED_COMMAND_INPUT_ADDED_ARG = [
        {"name": "test", "arguments": [{"name": "test"}, {"name": "test1"}]}
    ]
    CHANGED_COMMAND_INPUT_REQUIRED = [
        {"name": "test", "arguments": [{"name": "test", "required": True}]}
    ]
    CHANGED_COMMAND_INPUT_ADDED_REQUIRED = [
        {
            "name": "test",
            "arguments": [{"name": "test"}, {"name": "test1", "required": True}],
        }
    ]
    CHANGED_COMMAND_OR_ARG_INPUTS = [
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_REQUIRED, True),
        (CHANGED_COMMAND_INPUT_ADDED_REQUIRED, CHANGED_COMMAND_INPUT_1, False),
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_ADDED_REQUIRED, False),
        (CHANGED_COMMAND_INPUT_ADDED_ARG, CHANGED_COMMAND_INPUT_1, True),
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_ADDED_ARG, False),
        (CHANGED_COMMAND_INPUT_1, CHANGED_COMMAND_INPUT_2, False),
        (CHANGED_COMMAND_NAME_INPUT, CHANGED_COMMAND_INPUT_1, False),
        (CHANGED_COMMAND_NAME_INPUT, CHANGED_COMMAND_NAME_INPUT, True),
    ]

    @pytest.mark.parametrize("current, old, answer", CHANGED_COMMAND_OR_ARG_INPUTS)
    def test_no_changed_command_name_or_arg(self, current, old, answer):
        current = {"script": {"commands": current}}
        old = {"script": {"commands": old}}
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        assert validator.no_changed_command_name_or_arg() is answer
        structure.quiet_bc = True
        assert (
            validator.no_changed_command_name_or_arg() is True
        )  # if quiet_bc is true should always succeed

    CHANGED_COMMAND_OR_ARG_MST_TEST_INPUTS = [
        (
            [
                {
                    "name": "command_test_name_1",
                    "arguments": [{"name": "argument_test_name_1", "required": True}],
                },
                {
                    "name": "command_test_name_2",
                    "arguments": [{"name": "argument_test_name_2", "required": True}],
                },
            ],
            [
                {
                    "name": "test1",
                    "arguments": [{"name": "argument_test_name_1", "required": True}],
                },
                {
                    "name": "test2",
                    "arguments": [{"name": "argument_test_name_2", "required": True}],
                },
            ],
            "[BC104] - Possible backwards compatibility break, Your updates to this file contains changes"
            " to a name or an argument of an existing command(s).\nPlease undo you changes to the following command(s):\ntest1\ntest2",
        )
    ]

    @pytest.mark.parametrize(
        "current, old, expected_error_msg", CHANGED_COMMAND_OR_ARG_MST_TEST_INPUTS
    )
    def test_no_changed_command_name_or_arg_msg(
        self, current, old, expected_error_msg, mocker
    ):
        """
        Given
        An integration with BC break in the following way:
        - Case 1: Old and New coppies of a yml file.
        Old copy: Has two commands - command_test_name_1 and command_test_name_2
        where each command has 1 argument - argument_test_name_1, argument_test_name_2 respectively.
        New copy: Has two commands - command_test_name_1 and command_test_name_2
        where each command has 1 argument - argument_test_name_1, argument_test_name_2 respectively.

        When
        - running the validation no_changed_command_name_or_arg()

        Then
        Ensure that the error massage was created correctly.
        - Case 1: Should include both command_test_name_1 and command_test_name_2 in the commands list in the error as they both have BC break changes.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        current = {"script": {"commands": current}}
        old = {"script": {"commands": old}}
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        validator.no_changed_command_name_or_arg()
        assert str_in_call_args_list(logger_error.call_args_list, expected_error_msg)

    WITHOUT_DUP = [{"name": "test"}, {"name": "test1"}]
    DUPLICATE_PARAMS_INPUTS = [(WITHOUT_DUP, True)]

    @pytest.mark.parametrize("current, answer", DUPLICATE_PARAMS_INPUTS)
    def test_no_duplicate_params(self, current, answer):
        current = {"configuration": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.has_no_duplicate_params() is answer

    def test_with_duplicate_params(self):
        """
        Given
        - integration configuration contains duplicate parameter (called test)

        When
        - running the validation has_no_duplicate_params()

        Then
        - it should set is_valid to False
        - it should return True (there are duplicate params)
        - it should print an error message that contains the duplicated param name
        """
        current = {"configuration": [{"name": "test"}, {"name": "test"}]}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)

        assert validator.has_no_duplicate_params() is False
        assert validator.is_valid is False

    WITHOUT_DUP_ARGS = [
        {"name": "testing", "arguments": [{"name": "test1"}, {"name": "test2"}]}
    ]
    WITH_DUP_ARGS = [
        {"name": "testing", "arguments": [{"name": "test1"}, {"name": "test1"}]}
    ]
    WITH_DUP_ARGS_NON_IDENTICAL = [
        {
            "name": "testing",
            "arguments": [
                {"name": "test1", "desc": "hello"},
                {"name": "test1", "desc": "hello1"},
            ],
        },
    ]

    DUPLICATE_ARGS_INPUTS = [
        (WITHOUT_DUP_ARGS, True),
        (WITH_DUP_ARGS, False),
        (WITH_DUP_ARGS_NON_IDENTICAL, False),
    ]

    @pytest.mark.parametrize("current, answer", DUPLICATE_ARGS_INPUTS)
    def test_has_no_duplicate_args(self, current, answer):
        current = {"script": {"commands": current}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.has_no_duplicate_args() is answer

    WITH_DEFAULT_INFO = [
        {"name": "API key", "additionalinfo": default_additional_info["API key"]}
    ]
    MISSING_DEFAULT_INFO = [{"name": "API key", "additionalinfo": ""}]
    NON_DEFAULT_INFO = [{"name": "API key", "additionalinfo": "you know, the API key"}]

    DEFAULT_INFO_INPUTS = [
        (WITH_DEFAULT_INFO, True, False),
        (MISSING_DEFAULT_INFO, False, False),
        (NON_DEFAULT_INFO, True, True),
    ]

    @pytest.mark.parametrize("args, answer, expecting_warning", DEFAULT_INFO_INPUTS)
    def test_default_params_default_info(
        self, mocker, args: List[Dict], answer: str, expecting_warning: bool
    ):
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        validator = IntegrationValidator(mock_structure("", {"configuration": args}))
        assert validator.default_params_have_default_additional_info() is answer

        if expecting_warning:
            from demisto_sdk.commands.common.errors import Errors

            warning_message, warning_code = Errors.non_default_additional_info(
                ["API key"]
            )
            expected_message = f"[{warning_code}] - {warning_message}"
            assert str_in_call_args_list(
                logger_warning.call_args_list, expected_message
            )

    NO_INCIDENT_INPUT = [
        (
            {
                "script": {
                    "commands": [{"name": "command1", "arguments": [{"name": "arg1"}]}]
                }
            },
            True,
        ),
        (
            {
                "script": {
                    "commands": [
                        {"name": "command_incident", "arguments": [{"name": "arg1"}]}
                    ]
                }
            },
            False,
        ),
        (
            {
                "script": {
                    "commands": [
                        {"name": "command1", "arguments": [{"name": "incident_arg"}]}
                    ]
                }
            },
            False,
        ),
    ]

    @pytest.mark.parametrize("content, answer", NO_INCIDENT_INPUT)
    def test_no_incident_in_core_pack(self, content, answer):
        """
        Given
            - An integration with commands' names and arguments.
        When
            - running no_incident_in_core_packs.
        Then
            - validate that commands' names and arguments do not contain the word incident.
        """
        structure = mock_structure("", content)
        validator = IntegrationValidator(structure)
        assert validator.no_incident_in_core_packs() is answer
        assert validator.is_valid is answer

    PYTHON3_SUBTYPE = {"type": "python", "subtype": "python3"}
    PYTHON2_SUBTYPE = {"type": "python", "subtype": "python2"}

    BLA_BLA_SUBTYPE = {"type": "python", "subtype": "blabla"}
    INPUTS_SUBTYPE_TEST = [
        (PYTHON2_SUBTYPE, PYTHON3_SUBTYPE, False),
        (PYTHON3_SUBTYPE, PYTHON2_SUBTYPE, False),
        (PYTHON3_SUBTYPE, PYTHON3_SUBTYPE, True),
        (PYTHON2_SUBTYPE, PYTHON2_SUBTYPE, True),
    ]

    @pytest.mark.parametrize("current, old, answer", INPUTS_SUBTYPE_TEST)
    def test_no_changed_subtype(self, current, old, answer):
        current, old = {"script": current}, {"script": old}
        structure = mock_structure("", current, old)
        validator = IntegrationValidator(structure)
        assert validator.no_changed_subtype() is answer
        structure.quiet_bc = True
        assert (
            validator.no_changed_subtype() is True
        )  # if quiet_bc is true should always succeed

    INPUTS_VALID_SUBTYPE_TEST = [
        (PYTHON2_SUBTYPE, True),
        (PYTHON3_SUBTYPE, True),
        ({"type": "python", "subtype": "lies"}, False),
    ]

    @pytest.mark.parametrize("current, answer", INPUTS_VALID_SUBTYPE_TEST)
    def test_id_valid_subtype(self, current, answer):
        current = {"script": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_subtype() is answer

    DEFAULT_ARGS_DIFFERENT_ARG_NAME = [
        {
            "name": "cve",
            "arguments": [
                {"name": "cve_id", "required": False, "default": True, "isArray": True}
            ],
        }
    ]
    DEFAULT_ARGS_SAME_ARG_NAME = [
        {
            "name": "cve",
            "arguments": [
                {"name": "cve", "required": False, "default": True, "isArray": True}
            ],
        }
    ]
    DEFAULT_ARGS_MISSING_UNREQUIRED_DEFAULT_FIELD = [
        {
            "name": "email",
            "arguments": [
                {"name": "email", "required": False, "default": True, "isArray": True},
                {"name": "verbose"},
            ],
        }
    ]
    DEFAULT_ARGS_MISSING_DEFAULT_PARAM_WHEN_ALLOWED = [
        {
            "name": "endpoint",
            "arguments": [{"name": "id", "required": False, "default": False}],
        }
    ]
    DEFAULT_ARGS_INVALID_PARMA_MISSING_DEFAULT = [
        {"name": "file", "required": True, "default": True, "isArray": True},
        {"name": "verbose"},
    ]
    DEFAULT_ARGS_INVALID_NOT_DEFAULT = [
        {
            "name": "email",
            "arguments": [
                {"name": "email", "required": False, "default": False},
                {"name": "verbose"},
            ],
        }
    ]
    DEFAULT_ARGS_INVALID_COMMAND = [
        {"name": "file", "required": True, "default": False},
        {"name": "verbose"},
    ]
    DEFAULT_ARGS_MISSING_DEFAULT_PARAM_WHEN_NOT_ALLOWED = [
        {
            "name": "email",
            "arguments": [
                {
                    "name": "verbose",
                    "required": False,
                    "default": False,
                    "isArray": True,
                }
            ],
        }
    ]
    DEFAULT_ARGS_NOT_ARRAY = [
        {
            "name": "email",
            "arguments": [
                {"name": "email", "required": False, "default": True, "isArray": False},
                {"name": "verbose"},
            ],
        }
    ]
    DEFAULT_ARGS_INPUTS = [
        (DEFAULT_ARGS_DIFFERENT_ARG_NAME, False),
        (DEFAULT_ARGS_MISSING_UNREQUIRED_DEFAULT_FIELD, True),
        (DEFAULT_ARGS_MISSING_DEFAULT_PARAM_WHEN_ALLOWED, True),
        (DEFAULT_ARGS_INVALID_PARMA_MISSING_DEFAULT, False),
        (DEFAULT_ARGS_INVALID_NOT_DEFAULT, False),
        (DEFAULT_ARGS_INVALID_COMMAND, False),
        (DEFAULT_ARGS_MISSING_DEFAULT_PARAM_WHEN_NOT_ALLOWED, False),
        (DEFAULT_ARGS_NOT_ARRAY, False),
        (DEFAULT_ARGS_SAME_ARG_NAME, True),
    ]

    @pytest.mark.parametrize("current, answer", DEFAULT_ARGS_INPUTS)
    def test_is_valid_default_array_argument_in_reputation_command(
        self, current, answer
    ):
        """
        Given: Integration reputation command with arguments.

        When: running is_valid_default_argument_in_reputation command.

        Then: Validate that matching default arg name yields True, else yields False.
        """
        current = {"script": {"commands": current}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert (
            validator.is_valid_default_array_argument_in_reputation_command() is answer
        )

    MULTIPLE_DEFAULT_ARGS_1 = [
        {
            "name": "msgraph-list-users",
            "arguments": [
                {"name": "users", "required": False, "default": False},
                {"name": "verbose"},
            ],
        }
    ]
    MULTIPLE_DEFAULT_ARGS_2 = [
        {
            "name": "msgraph-list-users",
            "arguments": [
                {"name": "users", "required": False, "default": True},
                {"name": "verbose"},
            ],
        }
    ]
    MULTIPLE_DEFAULT_ARGS_INVALID_1 = [
        {
            "name": "msgraph-list-users",
            "arguments": [
                {"name": "users", "required": False, "default": True},
                {"name": "verbose", "default": True},
            ],
        }
    ]
    NONE_ARGS_INVALID = [{"name": "msgraph-list-users", "arguments": None}]

    DEFAULT_ARGS_INPUTS = [
        (MULTIPLE_DEFAULT_ARGS_1, True),
        (MULTIPLE_DEFAULT_ARGS_2, True),
        (MULTIPLE_DEFAULT_ARGS_INVALID_1, False),
        (NONE_ARGS_INVALID, False),
    ]

    @pytest.mark.parametrize("current, answer", DEFAULT_ARGS_INPUTS)
    def test_is_valid_default_argument(self, current, answer):
        """
        Given: Integration command with arguments.

        When: running is_valid_default_argument command.

        Then: Validate that up to 1 default arg name yields True and that the arguments are not None, else yields False.
        """
        current = {"script": {"commands": current}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_default_argument() is answer

    MOCK_REPUTATIONS_1 = [
        {"contextPath": "Int.lol", "description": "desc", "type": "number"},
        {"contextPath": "DBotScore.lives.matter"},
    ]
    MOCK_REPUTATIONS_2 = [{"name": "panorama-commit-status", "outputs": 1}]
    MOCK_REPUTATIONS_INVALID_EMAIL = [
        {
            "contextPath": "DBotScore.Indicator",
            "description": "The indicator that was tested.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Type",
            "description": "The indicator type.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Vendor",
            "description": "Vendor used to calculate the score.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Sc0re",
            "description": "The actual score.",
            "type": "int",
        },
        {"contextPath": "Email.To", "description": "email to", "type": "string"},
    ]
    MOCK_REPUTATIONS_INVALID_FILE = [
        {
            "contextPath": "DBotScore.Indicator",
            "description": "The indicator that was tested.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Type",
            "description": "The indicator type.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Vendor",
            "description": "Vendor used to calculate the score.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Score",
            "description": "The actual score.",
            "type": "int",
        },
        {
            "contextPath": "File.Md5",
            "description": "The MD5 hash of the file.",
            "type": "string",
        },
    ]
    MOCK_REPUTATIONS_VALID_IP = [
        {
            "contextPath": "DBotScore.Indicator",
            "description": "The indicator that was tested.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Type",
            "description": "The indicator type.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Vendor",
            "description": "Vendor used to calculate the score.",
            "type": "string",
        },
        {
            "contextPath": "DBotScore.Score",
            "description": "The actual score.",
            "type": "int",
        },
        {"contextPath": "IP.Address", "description": "IP address", "type": "string"},
    ]
    MOCK_REPUTATIONS_VALID_ENDPOINT = [
        {
            "contextPath": "Endpoint.Hostname",
            "description": "The endpoint's hostname.",
            "type": "string",
        },
        {
            "contextPath": "Endpoint.IPAddress",
            "description": "The endpoint's IP address.",
            "type": "string",
        },
        {
            "contextPath": "Endpoint.ID",
            "description": "The endpoint's ID.",
            "type": "string",
        },
    ]

    IS_OUTPUT_FOR_REPUTATION_INPUTS = [
        (MOCK_REPUTATIONS_1, "not bang", True),
        (MOCK_REPUTATIONS_2, "not bang", True),
        (MOCK_REPUTATIONS_INVALID_EMAIL, "email", False),
        (MOCK_REPUTATIONS_INVALID_FILE, "file", False),
        (MOCK_REPUTATIONS_VALID_IP, "ip", True),
        (MOCK_REPUTATIONS_VALID_ENDPOINT, "endpoint", True),
    ]

    @pytest.mark.parametrize("current, name, answer", IS_OUTPUT_FOR_REPUTATION_INPUTS)
    def test_is_outputs_for_reputations_commands_valid(self, current, name, answer):
        current = {"script": {"commands": [{"name": name, "outputs": current}]}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_outputs_for_reputations_commands_valid() is answer
        structure.quiet_bc = True
        assert (
            validator.is_outputs_for_reputations_commands_valid() is True
        )  # if quiet_bc is true should succeed

    CASE_EXISTS_WITH_DEFAULT_TRUE = [
        {
            "name": "endpoint",
            "arguments": [{"name": "ip", "required": False, "default": True}],
            "outputs": [
                {"contextPath": "Endpoint.ID"},
                {"contextPath": "Endpoint.IPAddress"},
                {"contextPath": "Endpoint.Hostname"},
            ],
        }
    ]
    CASE_REQUIRED_ARG_WITH_DEFAULT_FALSE = [
        {
            "name": "endpoint",
            "arguments": [{"name": "id", "required": False, "default": False}],
            "outputs": [
                {"contextPath": "Endpoint.ID"},
                {"contextPath": "Endpoint.IPAddress"},
                {"contextPath": "Endpoint.Hostname"},
            ],
        }
    ]
    CASE_INVALID_MISSING_REQUIRED_ARGS = [
        {
            "name": "endpoint",
            "arguments": [{"name": "url", "required": False, "default": True}],
        }
    ]
    CASE_INVALID_NON_DEFAULT_ARG_WITH_DEFAULT_TRUE = [
        {
            "name": "endpoint",
            "arguments": [{"name": "id", "required": False, "default": True}],
        }
    ]
    CASE_INVALID_MISSING_OUTPUT = [
        {
            "name": "endpoint",
            "arguments": [{"name": "ip", "required": False, "default": True}],
            "outputs": [
                {"contextPath": "Endpoint.IPAddress"},
                {"contextPath": "Endpoint.Hostname"},
                {"contextPath": "Endpoint.Test"},
            ],
        }
    ]
    ENDPOINT_CASES = [
        (CASE_EXISTS_WITH_DEFAULT_TRUE, True),
        (CASE_REQUIRED_ARG_WITH_DEFAULT_FALSE, True),
        (CASE_INVALID_MISSING_REQUIRED_ARGS, False),
        (CASE_INVALID_NON_DEFAULT_ARG_WITH_DEFAULT_TRUE, False),
    ]

    @pytest.mark.parametrize("current, answer", ENDPOINT_CASES)
    def test_is_valid_endpoint_command(self, current, answer):
        """
        Given: Endpoint command with arguments and outputs in yml.

        When: running is_valid_endpoint_command.

        Then: Validate that at least one of the required input exists (with correct deafult field)
         and the relevant outputs are correct.
        """
        current = {"script": {"commands": current}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_endpoint_command() is answer

    VALID_BETA = {
        "commonfields": {"id": "newIntegration"},
        "name": "newIntegration",
        "display": "newIntegration (Beta)",
        "beta": True,
    }
    VALID_BETA_DEPRECATED = {
        "commonfields": {"id": "Proofpoint Server Protection"},
        "name": "Proofpoint Server Protection",
        "display": "Proofpoint Protection Server (Deprecated)",
        "beta": True,
        "deprecated": True,
        "description": "Deprecated. The integration uses an unsupported scraping API. "
        "Use Proofpoint Protection Server v2 instead.",
    }
    INVALID_BETA_DISPLAY = {
        "commonfields": {"id": "newIntegration"},
        "name": "newIntegration",
        "display": "newIntegration",
        "beta": True,
    }
    INVALID_BETA_ID = {
        "commonfields": {"id": "newIntegration-beta"},
        "name": "newIntegration",
        "display": "newIntegration",
        "beta": True,
    }
    INVALID_BETA_NAME = {
        "commonfields": {"id": "newIntegration"},
        "name": "newIntegration (Beta)",
        "display": "newIntegration",
        "beta": True,
    }
    INVALID_BETA_ALL_BETA = {
        "commonfields": {"id": "newIntegration beta"},
        "name": "newIntegration beta",
        "display": "newIntegration (Beta)",
    }
    INVALID_BETA_CHANGED_NAME_NO_BETA_FIELD = {
        "commonfields": {"id": "newIntegration beta"},
        "name": "newIntegration beta",
        "display": "newIntegration changed (Beta)",
    }
    IS_VALID_BETA_INPUTS = [
        (VALID_BETA, True, True),
        (VALID_BETA_DEPRECATED, False, True),
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

    PROXY_VALID = [
        {
            "name": "proxy",
            "type": 8,
            "display": "Use system proxy settings",
            "required": False,
        }
    ]
    PROXY_WRONG_TYPE = [
        {
            "name": "proxy",
            "type": 9,
            "display": "Use system proxy settings",
            "required": False,
        }
    ]
    PROXY_WRONG_DISPLAY = [
        {"name": "proxy", "type": 8, "display": "bla", "required": False}
    ]
    PROXY_WRONG_REQUIRED = [
        {
            "name": "proxy",
            "type": 8,
            "display": "Use system proxy settings",
            "required": True,
        }
    ]
    IS_PROXY_INPUTS = [
        (PROXY_VALID, True),
        (PROXY_WRONG_TYPE, False),
        (PROXY_WRONG_DISPLAY, False),
        (PROXY_WRONG_REQUIRED, False),
    ]

    @pytest.mark.parametrize("current, answer", IS_PROXY_INPUTS)
    def test_is_proxy_configured_correctly(self, current, answer):
        current = {"configuration": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_proxy_configured_correctly() is answer

    UNSECURE_VALID = [
        {
            "name": "unsecure",
            "type": 8,
            "display": "Trust any certificate (not secure)",
            "required": False,
        }
    ]
    INSECURE_WRONG_DISPLAY = [
        {
            "name": "insecure",
            "type": 8,
            "display": "Use system proxy settings",
            "required": False,
        }
    ]
    UNSECURE_WRONG_DISPLAY = [
        {
            "name": "unsecure",
            "type": 8,
            "display": "Use system proxy settings",
            "required": False,
        }
    ]
    UNSECURE_WRONG_DISPLAY_AND_TYPE = [
        {
            "name": "unsecure",
            "type": 7,
            "display": "Use system proxy settings",
            "required": False,
        }
    ]
    IS_INSECURE_INPUTS = [
        (UNSECURE_VALID, True),
        (INSECURE_WRONG_DISPLAY, False),
        (UNSECURE_WRONG_DISPLAY, False),
        (UNSECURE_WRONG_DISPLAY_AND_TYPE, False),
    ]

    @pytest.mark.parametrize("current, answer", IS_INSECURE_INPUTS)
    def test_is_insecure_configured_correctly(self, current, answer):
        current = {"configuration": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_insecure_configured_correctly() is answer

    VALID_CHECKBOX_PARAM = [
        {"name": "test1", "type": 8, "display": "test1", "required": False}
    ]
    INVALID_CHECKBOX_PARAM = [
        {"name": "test2", "type": 8, "display": "test2", "required": True}
    ]

    IS_INSECURE_INPUTS = [(VALID_CHECKBOX_PARAM, True), (INVALID_CHECKBOX_PARAM, False)]

    @pytest.mark.parametrize("current, answer", IS_INSECURE_INPUTS)
    def test_is_checkbox_param_configured_correctly(self, current, answer):
        current = {"configuration": current}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_checkbox_param_configured_correctly() is answer

    INVALID_CATEGORY = {"category": "Analytics & SIEMM"}
    VALID_CATEGORY1 = {"category": "Endpoint"}
    VALID_CATEGORY2 = {"category": "File Integrity Management"}

    IS_VALID_CATEGORY_INPUTS = [
        (VALID_CATEGORY1, True, ["Endpoint"]),
        (VALID_CATEGORY2, True, ["File Integrity Management"]),
        (INVALID_CATEGORY, False, []),
    ]

    @pytest.mark.parametrize(
        "current, answer, valid_list_mock", IS_VALID_CATEGORY_INPUTS
    )
    def test_is_valid_category(self, mocker, current, answer, valid_list_mock):
        mocker.patch(
            "demisto_sdk.commands.common.hook_validations.integration.tools.get_current_categories",
            return_value=valid_list_mock,
        )
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_category() is answer

    VALID_DISPLAY_NON_HIDDEN = [
        {
            "name": "unsecure",
            "type": 8,
            "display": "Trust any certificate (not secure)",
            "required": False,
            "hidden": False,
        }
    ]
    VALID_DISPLAY_HIDDEN = [
        {
            "name": "insecure",
            "type": 8,
            "display": "Use system proxy settings",
            "required": False,
            "hidden": True,
        }
    ]
    INVALID_DISPLAY_NON_HIDDEN = [
        {
            "name": "unsecure",
            "type": 8,
            "display": "",
            "required": False,
            "hidden": False,
        }
    ]
    INVALID_NO_DISPLAY_NON_HIDDEN = [
        {"name": "unsecure", "type": 8, "required": False, "hidden": False}
    ]
    VALID_NO_DISPLAY_TYPE_EXPIRATION = [
        {"name": "unsecure", "type": 17, "required": False, "hidden": False}
    ]
    INVALID_DISPLAY_TYPE_EXPIRATION = [
        {
            "name": "unsecure",
            "type": 17,
            "display": "some display",
            "required": False,
            "hidden": False,
        }
    ]
    INVALID_DISPLAY_BUT_VALID_DISPLAYPASSWORD = [
        {
            "name": "credentials",
            "type": 9,
            "display": "",
            "displaypassword": "some display password",
            "required": True,
            "hiddenusername": True,
        }
    ]
    IS_VALID_DISPLAY_INPUTS = [
        (VALID_DISPLAY_NON_HIDDEN, False),
        (VALID_DISPLAY_HIDDEN, False),
        (INVALID_DISPLAY_NON_HIDDEN, True),
        (INVALID_NO_DISPLAY_NON_HIDDEN, True),
        (VALID_NO_DISPLAY_TYPE_EXPIRATION, False),
        (INVALID_DISPLAY_TYPE_EXPIRATION, True),
        (FEED_REQUIRED_PARAMS_STRUCTURE, False),
        (INVALID_DISPLAY_BUT_VALID_DISPLAYPASSWORD, False),
    ]

    @pytest.mark.parametrize("configuration_setting, answer", IS_VALID_DISPLAY_INPUTS)
    def test_is_valid_display_configuration(self, configuration_setting, answer):
        current = {"configuration": configuration_setting}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_display_configuration() is not answer
        structure.quiet_bc = True
        assert (
            validator.is_valid_display_configuration() is True
        )  # if quiet_bc is true should always succeed

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
            "configuration": deepcopy(FEED_REQUIRED_PARAMS_STRUCTURE),
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

    V2_VALID = {
        "display": "integrationname v2",
        "name": "integrationname v2",
        "id": "integrationname v2",
    }
    V2_WRONG_DISPLAY_1 = {
        "display": "integrationname V2",
        "name": "integrationname V2",
        "id": "integrationname V2",
    }
    V2_WRONG_DISPLAY_2 = {
        "display": "integrationnameV2",
        "name": "integrationnameV2",
        "id": "integrationnameV2",
    }
    V2_WRONG_DISPLAY_3 = {
        "display": "integrationnamev2",
        "name": "integrationnamev2",
        "id": "integrationnamev2",
    }
    V2_NAME_INPUTS = [
        (V2_VALID, True),
        (V2_WRONG_DISPLAY_1, False),
        (V2_WRONG_DISPLAY_2, False),
        (V2_WRONG_DISPLAY_3, False),
    ]

    @pytest.mark.parametrize("current, answer", V2_NAME_INPUTS)
    def test_is_valid_display_name(self, current, answer):
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_display_name() is answer

    V2_VALID_SIEM_1 = {"display": "PhishTank v2", "script": {"isfetchevents": False}}
    V2_VALID_SIEM_2 = {
        "display": "PhishTank v2 Event Collector",
        "script": {"isfetchevents": True},
    }
    V2_VALID_SIEM_3 = {"display": "PhishTank v2 Event Collector", "script": {}}
    V2_VALID_SIEM_4 = {"display": "PhishTank v2 Event Collector"}
    V2_INVALID_SIEM = {"display": "PhishTank v2", "script": {"isfetchevents": True}}

    V2_SIEM_NAME_INPUTS = [
        (V2_VALID_SIEM_1, True),
        (V2_VALID_SIEM_2, True),
        (V2_VALID_SIEM_3, True),
        (V2_VALID_SIEM_4, True),
        (V2_INVALID_SIEM, False),
    ]

    @pytest.mark.parametrize("current, answer", V2_SIEM_NAME_INPUTS)
    def test_is_valid_display_name_siem(self, current, answer):
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current

        assert validator.is_valid_display_name_for_siem() is answer

    V2_VALID_SIEM_1 = {
        "display": "Test Event Collector",
        "script": {"isfetchevents": True},
        "marketplaces": ["marketplacev2"],
    }
    V2_INVALID_SIEM = {
        "display": "Test Event Collector",
        "script": {"isfetchevents": True},
        "marketplaces": ["marketplacev2", "xsoar"],
    }
    V2_INVALID_SIEM_2 = {
        "display": "Test Event Collector",
        "script": {"isfetchevents": True},
        "marketplaces": ["xsoar"],
    }

    V2_SIEM_MARKETPLACE_INPUTS = [
        (V2_VALID_SIEM_1, True),
        (V2_INVALID_SIEM, False),
        (V2_INVALID_SIEM_2, False),
    ]

    @pytest.mark.parametrize("current, answer", V2_SIEM_MARKETPLACE_INPUTS)
    def test_is_valid_xsiam_marketplace(self, current, answer):
        """
        Given
            - Valid marketplaces field (only with marketplacev2)
            - Invalid marketplaces field (with 2 entries - suppose to be only 1)
            - Invalid marketplaces field (with xsaor value instead of marketplacev2)

        When
            - running is_valid_xsiam_marketplace.

        Then
            - Check that the function returns True if valid, else False.
        """
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current

        assert validator.is_valid_xsiam_marketplace() is answer

    VALID_DEFAULTVALUE_CHECKBOX_1 = {
        "configuration": [{"defaultvalue": "true", "type": 8}]
    }
    VALID_DEFAULTVALUE_CHECKBOX_2 = {
        "configuration": [{"type": 8, "defaultvalue": "false"}]
    }
    VALID_DEFAULTVALUE_CHECKBOX_3 = {
        "configuration": [{"type": 0, "defaultvalue": True}]
    }
    VALID_DEFAULTVALUE_CHECKBOX_4 = {"configuration": [{"type": 8}]}

    INVALID_DEFAULTVALUE_CHECKBOX_1 = {
        "configuration": [{"type": 8, "defaultvalue": True}]
    }
    INVALID_DEFAULTVALUE_CHECKBOX_2 = {
        "configuration": [{"type": 8, "defaultvalue": False}]
    }
    INVALID_DEFAULTVALUE_CHECKBOX_3 = {
        "configuration": [{"type": 8, "defaultvalue": "True"}]
    }

    DEFAULTVALUE_CHECKBOX_INPUTS = [
        (VALID_DEFAULTVALUE_CHECKBOX_1, True),
        (VALID_DEFAULTVALUE_CHECKBOX_2, True),
        (VALID_DEFAULTVALUE_CHECKBOX_3, True),
        (VALID_DEFAULTVALUE_CHECKBOX_4, True),
        (INVALID_DEFAULTVALUE_CHECKBOX_1, False),
        (INVALID_DEFAULTVALUE_CHECKBOX_2, False),
        (INVALID_DEFAULTVALUE_CHECKBOX_3, False),
    ]

    @pytest.mark.parametrize("current, answer", DEFAULTVALUE_CHECKBOX_INPUTS)
    def test_is_valid_defaultvalue_for_checkbox(self, current, answer):
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current

        assert validator.is_valid_default_value_for_checkbox() is answer

    def test_is_valid_description_positive(self):
        integration_path = os.path.normpath(
            os.path.join(
                f"{git_path()}/demisto_sdk/tests", "test_files", "integration-Zoom.yml"
            )
        )
        structure = mock_structure(file_path=integration_path)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_description() is True

    DEPRECATED_VALID = {
        "deprecated": True,
        "display": "ServiceNow (Deprecated)",
        "description": "Deprecated. Use the XXXX integration instead.",
    }
    DEPRECATED_VALID2 = {
        "deprecated": True,
        "display": "Feodo Tracker Hashes Feed (Deprecated)",
        "description": "Deprecated. Feodo Tracker no longer supports this feed. "
        "No available replacement.",
    }
    DEPRECATED_VALID3 = {
        "deprecated": True,
        "display": "Proofpoint Protection Server (Deprecated)",
        "description": "Deprecated. The integration uses an unsupported scraping API. "
        "Use Proofpoint Protection Server v2 instead.",
    }
    DEPRECATED_INVALID_DISPLAY = {
        "deprecated": True,
        "display": "ServiceNow (Old)",
        "description": "Deprecated. Use the XXXX integration instead.",
    }
    DEPRECATED_INVALID_DESC = {
        "deprecated": True,
        "display": "ServiceNow (Deprecated)",
        "description": "Deprecated.",
    }
    DEPRECATED_INVALID_DESC2 = {
        "deprecated": True,
        "display": "ServiceNow (Deprecated)",
        "description": "Use the ServiceNow integration to manage...",
    }
    DEPRECATED_INVALID_DESC3 = {
        "deprecated": True,
        "display": "Proofpoint Protection Server (Deprecated)",
        "description": "Deprecated. The integration uses an unsupported scraping API.",
    }
    DEPRECATED_INPUTS = [
        (DEPRECATED_VALID, True),
        (DEPRECATED_VALID2, True),
        (DEPRECATED_VALID3, True),
        (DEPRECATED_INVALID_DISPLAY, False),
        (DEPRECATED_INVALID_DESC, False),
        (DEPRECATED_INVALID_DESC2, False),
        (DEPRECATED_INVALID_DESC3, False),
    ]

    @pytest.mark.parametrize("current, answer", DEPRECATED_INPUTS)
    def test_is_valid_deprecated_integration(self, current, answer):
        """
        Given
            - A deprecated integration with a display and description.

        When
            - running is_valid_as_deprecated.

        Then
            - an integration with an invalid display name or invalid description will be errored.
        """
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_as_deprecated() is answer

    def test_valid_integration_parameters_display_name(self, integration):
        """
        Given
            - An integration with valid parameters display names.
        When
            - running is_valid_parameters_display_name.
        Then
            - an integration with a valid parameters display name is valid.
        """

        integration.yml.write_dict(
            {"configuration": [{"display": "Token"}, {"display": "Username"}]}
        )
        structure_validator = StructureValidator(
            integration.yml.path, predefined_scheme="integration"
        )
        validator = IntegrationValidator(structure_validator)

        assert validator.is_valid_parameters_display_name()

    def test_invalid_integration_parameters_display_name(self, integration):
        """
        Given
            - An integration with invalid parameters display names.
        When
            - running is_valid_parameters_display_name.
        Then
            - an integration with an invalid parameters display name is invalid.
        """

        integration.yml.write_dict(
            {"configuration": [{"display": "token"}, {"display": "User_name"}]}
        )

        with ChangeCWD(integration.repo_path):
            structure_validator = StructureValidator(
                integration.yml.path, predefined_scheme="integration"
            )
            validator = IntegrationValidator(structure_validator)

            assert not validator.is_valid_parameters_display_name()

    @pytest.mark.parametrize(
        "yml_data, excepted_result",
        [
            ({"configuration": [{"defaultvalue": "https://test.com"}]}, True),
            ({"configuration": [{"defaultvalue": "http://test.com"}]}, False),
        ],
    )
    def test_valid_integration_parameters_default_value(
        self, yml_data, excepted_result, integration: Integration
    ):
        """
        Given
            - Case 1: An integration with valid parameter default value.
            - Case 2: An integration with invalid parameter default value.
        When
            - running is_valid_parameter_url_default_value.
        Then
            - validate the output of the validation is as expected.
        """

        integration.yml.write_dict(yml_data)
        structure_validator = StructureValidator(
            integration.yml.path, predefined_scheme="integration"
        )
        validator = IntegrationValidator(structure_validator)

        assert validator.is_valid_parameter_url_default_value() is excepted_result

    @pytest.mark.parametrize(
        "support_level, expected_result", [("XSOAR", True), ("community", False)]
    )
    def test_fromlicense_in_integration_parameters_fields(
        self, pack, support_level, expected_result
    ):
        """
        Given
            - An integration from a contributor with not allowed key ('fromlicense') in parameters.
        When
            - Running is_valid_param.
        Then
            - an integration with an invalid parameters display name is invalid.
        """
        pack.pack_metadata.write_json({"support": support_level})
        integration = pack.create_integration("contributor")

        integration.yml.write_dict(
            {
                "configuration": [
                    {"name": "token", "display": "token", "fromlicense": "encrypted"}
                ]
            }
        )

        with ChangeCWD(pack.repo_path):
            structure_validator = StructureValidator(
                integration.yml.path, predefined_scheme="integration"
            )
            validator = IntegrationValidator(structure_validator)

            result = validator.has_no_fromlicense_key_in_contributions_integration()

        assert result == expected_result

    def test_valid_integration_path(self, integration):
        """
        Given
            - An integration with valid file path.
        When
            - running is_valid_integration_file_path.
        Then
            - an integration with a valid file path is valid.
        """

        structure_validator = StructureValidator(
            integration.yml.path, predefined_scheme="integration"
        )
        validator = IntegrationValidator(structure_validator)
        validator.file_path = (
            "Packs/VirusTotal/Integrations/integration-VirusTotal_5.5.yml"
        )

        assert validator.is_valid_integration_file_path()

        structure_validator = StructureValidator(
            integration.path, predefined_scheme="integration"
        )
        validator = IntegrationValidator(structure_validator)
        validator.file_path = "Packs/VirusTotal/Integrations/VirusTotal/Virus_Total.yml"

        assert validator.is_valid_integration_file_path()

    def test_invalid_integration_path(self, integration, mocker):
        """
        Given
            - An integration with invalid file path.
        When
            - running is_valid_integration_file_path.
        Then
            - an integration with an invalid file path is invalid.
        """
        structure_validator = StructureValidator(
            integration.yml.path, predefined_scheme="integration"
        )
        validator = IntegrationValidator(structure_validator)
        validator.file_path = (
            "Packs/VirusTotal/Integrations/VirusTotal/integration-VirusTotal_5.5.yml"
        )

        mocker.patch.object(validator, "handle_error", return_value=True)

        assert not validator.is_valid_integration_file_path()

        structure_validator = StructureValidator(
            integration.path, predefined_scheme="integration"
        )
        validator = IntegrationValidator(structure_validator)
        validator.file_path = "Packs/VirusTotal/Integrations/Virus_Total_5.yml"

        mocker.patch.object(validator, "handle_error", return_value=True)

        assert not validator.is_valid_integration_file_path()

    @pytest.mark.parametrize("file_name", ["IntNameTest.py", "IntNameTest_test.py"])
    def test_invalid_py_file_names(self, repo, file_name):
        """
        Given
            - An integration with invalid python file path.
            - A Unittest with invalid python file path.
        When
            - running is_valid_py_file_names.
        Then
            - The files are invalid (the integration name is incorrect).
        """

        pack = repo.create_pack("PackName")

        integration = pack.create_integration("IntName")
        integration.create_default_integration()
        structure_validator = StructureValidator(
            integration.path, predefined_scheme="integration"
        )

        python_path = integration.code.path
        new_name = f'{python_path.rsplit("/", 1)[0]}/{file_name}'
        os.rename(python_path, new_name)
        with ChangeCWD(repo.path):
            validator = IntegrationValidator(structure_validator)
            validator.file_path = new_name
            assert not validator.is_valid_py_file_names()

    def test_folder_name_without_separators(self, pack):
        """
        Given
            - An integration without separators in folder name.
        When
            - running check_separators_in_folder.
        Then
            - Ensure the validate passes.
        """

        integration = pack.create_integration("myInt")

        structure_validator = StructureValidator(integration.yml.path)
        validator = IntegrationValidator(structure_validator)

        assert validator.check_separators_in_folder()

    def test_files_names_without_separators(self, pack):
        """
        Given
            - An integration without separators in files names.
        When
            - running check_separators_in_files.
        Then
            - Ensure the validate passes.
        """

        integration = pack.create_integration("myInt")

        structure_validator = StructureValidator(integration.yml.path)
        validator = IntegrationValidator(structure_validator)

        assert validator.check_separators_in_files()

    def test_folder_name_with_separators(self, pack):
        """
        Given
            - An integration with separators in folder name.
        When
            - running check_separators_in_folder.
        Then
            - Ensure the validate failed.
        """

        integration = pack.create_integration("my_Int")

        with ChangeCWD(integration.repo_path):
            structure_validator = StructureValidator(integration.yml.path)
            validator = IntegrationValidator(structure_validator)

            assert not validator.check_separators_in_folder()

    def test_files_names_with_separators(self, pack):
        """
        Given
            - An integration with separators in files names.
        When
            - running check_separators_in_files.
        Then
            - Ensure the validate failed.
        """

        integration = pack.create_integration("my_Int")

        with ChangeCWD(integration.repo_path):
            structure_validator = StructureValidator(integration.yml.path)
            validator = IntegrationValidator(structure_validator)

            assert not validator.check_separators_in_files()

    def test_name_contains_the_type(self, pack):
        """
        Given
            - An integration with a name that contains the word "integration".
        When
            - running name_not_contain_the_type.
        Then
            - Ensure the validate failed.
        """
        integration = pack.create_integration(yml={"name": "test_integration"})

        with ChangeCWD(pack.repo_path):
            structure_validator = StructureValidator(integration.yml.path)
            validator = IntegrationValidator(structure_validator)

            assert not validator.name_not_contain_the_type()

    def test_display_name_contains_the_type(self, pack):
        """
        Given
            - An integration with a display name that contains the word "integration".
        When
            - running name_not_contain_the_type.
        Then
            - Ensure the validate failed.
        """

        integration = pack.create_integration(yml={"display": "test_integration"})

        with ChangeCWD(pack.repo_path):
            structure_validator = StructureValidator(integration.yml.path)
            validator = IntegrationValidator(structure_validator)

            assert not validator.name_not_contain_the_type()

    def test_name_does_not_contains_the_type(self, pack):
        """
        Given
            - An integration with a name that does not contains "integration" string.
        When
            - running name_not_contain_the_type.
        Then
            - Ensure the validate passes.
        """

        integration = pack.create_integration(yml={"name": "test", "display": "test"})

        structure_validator = StructureValidator(integration.yml.path)
        validator = IntegrationValidator(structure_validator)

        assert validator.name_not_contain_the_type()

    @pytest.mark.parametrize(
        "support, parameter_type, hidden, expected_result",
        [
            ("xsoar", 4, False, False),
            ("xsoar", 9, False, True),
            ("xsoar", 4, True, True),
            ("community", 4, False, True),
            ("partner", 4, False, True),
        ],
    )
    def test_is_api_token_in_credential_type(
        self, pack, support, parameter_type, hidden, expected_result
    ):
        """
        Given
            - An integration with API token parameter in non credential type.
        When
            - Running is_api_token_in_credential_type on `xsoar` support integration and non `xsoar` integration.
        Then
            - Ensure the validate on `xsoar` integration support failed on invalid type,
            the type of the parameter should be 9 (credentials).
        """

        pack.pack_metadata.write_json({"support": support})

        integration = pack.create_integration(
            yml={
                "configuration": [
                    {
                        "display": "API token",
                        "name": "token",
                        "type": parameter_type,  # Encrypted text failed
                        "hidden": hidden,
                    }
                ]
            }
        )

        with ChangeCWD(pack.repo_path):
            structure_validator = StructureValidator(
                integration.yml.path, predefined_scheme="integration"
            )
            validator = IntegrationValidator(structure_validator)

            assert validator.is_api_token_in_credential_type() == expected_result

    IS_SKIPPED_INPUTS = [
        ({"skipped_integrations": {"SomeIntegration": "No instance"}}, False, False),
        ({"skipped_integrations": {"SomeOtherIntegration": "No instance"}}, True, True),
        (
            {"skipped_integrations": {"SomeOtherIntegration": "Other reason"}},
            False,
            True,
        ),
        ({"skipped_integrations": {"SomeIntegration": "Other reason"}}, False, True),
    ]

    @pytest.mark.parametrize("conf_dict, has_unittests, answer", IS_SKIPPED_INPUTS)
    def test_is_unskipped_integration(self, mocker, conf_dict, has_unittests, answer):
        """
        Given:
            - An integration.
            - conf file with configurations for the integration.

        When: running validate specifically on integration.

        Then: Validate the integration is not skipped.
        """
        current = {"commonfields": {"id": "SomeIntegration"}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        validator.file_path = "Packs/VirusTotal/Integrations/VirusTotal/Virus_Total.yml"
        mocker.patch.object(
            IntegrationValidator, "has_unittest", return_value=has_unittests
        )
        assert validator.is_unskipped_integration(conf_dict) is answer

    VERIFY_REPUTATION_COMMANDS = [
        # Test feed integration validation
        (["test1", "test2"], True, False, False),
        (["test3", "test4"], True, True, True),
        # Test reputation commands validation
        (["test5", "test6"], False, False, True),
        (["test7", "url"], False, False, False),
        (["test8", "url"], False, True, True),
        (["domain", "url"], False, True, True),
    ]

    @pytest.mark.parametrize(
        "commands, is_feed, has_reliability, result", VERIFY_REPUTATION_COMMANDS
    )
    def test_verify_reputation_commands_has_reliability(
        self, commands, is_feed, has_reliability, result
    ):
        """
        Given
            - Modified integration with reputation command.
        When
            - Call "verify_reputation_commands_has_reliability" method.
        Then
            - Ensure the command fails when there is a reputation command without reliability parameter.
        """
        current = {"script": {"commands": [{"name": command} for command in commands]}}

        if is_feed:
            current["script"]["feed"] = True

        if has_reliability:
            current["configuration"] = [{"name": "integrationReliability"}]

        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.verify_reputation_commands_has_reliability() is result

    @pytest.mark.parametrize(
        "hidden_value,is_valid",
        (
            (None, True),
            (True, True),
            (False, True),
            ([], True),
            ([MarketplaceVersions.XSOAR], True),
            ([MarketplaceVersions.MarketplaceV2], True),
            ("true", True),
            ("false", True),
            ("True", True),
            ("False", True),
            (
                [MarketplaceVersions.XSOAR, MarketplaceVersions.XSOAR],
                True,
            ),  # may be useless, but not invalid
            # invalid cases
            ("", False),
            (42, False),
            ("None", False),
            ([""], False),
            ([True], False),
            (["true"], False),
            (["True"], False),
            (MarketplaceVersions.XSOAR, False),
            (
                [
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                    MarketplaceVersions.XPANSE,
                    MarketplaceVersions.XSOAR_SAAS,
                    MarketplaceVersions.XSOAR_ON_PREM,
                ],
                False,
            ),
            ("🥲", False),
            ("Trüe", False),
            ([MarketplaceVersions.XSOAR, None], False),
            ([MarketplaceVersions.MarketplaceV2, None], False),
            ([MarketplaceVersions.XSOAR, True], False),
            ([MarketplaceVersions.XSOAR, 1], False),
            ([MarketplaceVersions.XSOAR, "🥲"], False),
            ([MarketplaceVersions.XSOAR, "true"], False),
            ([MarketplaceVersions.XSOAR, "True"], False),
        ),
    )
    def test_invalid_hidden_attributes_for_param(
        self, hidden_value: Any, is_valid: bool
    ):
        assert (
            IntegrationValidator(
                mock_structure(
                    None,
                    # using `longRunning` here, as the name condition is tested in test_is_valid_hidden_params()
                    {
                        "configuration": [
                            {"name": "longRunning", "hidden": hidden_value}
                        ]
                    },
                )
            ).is_valid_hidden_params()
            == is_valid
        )

    @pytest.mark.parametrize(
        "support_level_header, is_valid",
        [
            (XSOAR_SUPPORT, True),
            (PARTNER_SUPPORT, False),
        ],
    )
    def test_is_partner_collector_has_xsoar_support_level_header(
        self, mocker, pack, support_level_header: str, is_valid: bool
    ):
        """
        Given
        - Case A: support_level_header = xsoar
        - Case B: support_level_header = partner

        When
        - run is_partner_collector_has_xsoar_support_level_header

        Then
        - Case A: make sure the validation succeed
        - Case B: make sure the validation fails
        """
        name = "test"
        yml = {
            "commonfields": {"id": name, "version": -1},
            "name": name,
            "display": name,
            "description": name,
            "category": "category",
            "script": {
                "type": "python",
                "subtype": "python3",
                "script": "",
                "isfetchevents": True,
                "commands": [],
            },
            "configuration": [],
            SUPPORT_LEVEL_HEADER: support_level_header,
        }

        integration = pack.create_integration(name, yml=yml)
        validator = IntegrationValidator(
            mock_structure(integration.path, current_file=integration.yml.read_dict())
        )
        mocker.patch.object(
            IntegrationValidator,
            "get_metadata_file_content",
            return_value={"support": PARTNER_SUPPORT},
        )
        assert (
            validator.is_partner_collector_has_xsoar_support_level_header() == is_valid
        )


class TestIsFetchParamsExist:
    def setup_method(self):
        config = {
            "configuration": deepcopy(INCIDENT_FETCH_REQUIRED_PARAMS),
            "script": {"isfetch": True},
        }
        self.validator = IntegrationValidator(mock_structure("", config))

    def test_valid(self):
        assert (
            self.validator.is_valid_fetch()
        ), "is_valid_fetch() returns False instead True"

    def test_sanity(self):
        # missing param in configuration
        self.validator.current_file["configuration"] = [
            t
            for t in self.validator.current_file["configuration"]
            if t["name"] != "incidentType"
        ]
        assert (
            self.validator.is_valid_fetch() is False
        ), "is_valid_fetch() returns True instead False"

    def test_missing_max_fetch_text(self, mocker, caplog, capsys):
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        # missing param in configuration
        self.validator.current_file["configuration"] = [
            t
            for t in self.validator.current_file["configuration"]
            if t["name"] != "incidentType"
        ]
        assert self.validator.is_valid_fetch() is False
        assert not str_in_call_args_list(
            logger_info.call_args_list, "display: Incident type"
        )
        assert str_in_call_args_list(
            logger_error.call_args_list,
            """A required parameter "incidentType" is missing from the YAML file.""",
        )

    def test_missing_field(self):
        # missing param
        for i, t in enumerate(self.validator.current_file["configuration"]):
            if t["name"] == "incidentType":
                del self.validator.current_file["configuration"][i]["name"]
        print(self.validator.current_file["configuration"])  # noqa: T201
        assert (
            self.validator.is_valid_fetch() is False
        ), "is_valid_fetch() returns True instead False"

    def test_malformed_field(self, mocker):
        # incorrect param
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        config = self.validator.current_file["configuration"]
        self.validator.current_file["configuration"] = []
        for t in config:
            if t["name"] == "incidentType":
                t["type"] = 123
            self.validator.current_file["configuration"].append(t)

        assert (
            self.validator.is_valid_fetch() is False
        ), "is_valid_fetch() returns True instead False"
        assert all(
            [
                str_in_call_args_list(
                    logger_error.call_args_list, "display: Incident type"
                ),
                str_in_call_args_list(
                    logger_error.call_args_list, "name: incidentType"
                ),
            ]
        )

    def test_specific_for_marketplace(self):
        """
        Given:
            a schema whit a custom value for specific marketplace on fetch

        When:
            running is_valid_fetch

        Then:
            validate that the validation pass
        """
        self.validator.current_file["configuration"][-1]["defaultValue:xsoar"] = "test"
        assert self.validator.is_valid_fetch()

    def test_not_fetch(self, mocker):
        self.test_malformed_field(mocker)
        self.validator.is_valid = True
        self.validator.current_file["script"]["isfetch"] = False
        assert (
            self.validator.is_valid_fetch()
        ), "is_valid_fetch() returns False instead True"

    @pytest.mark.parametrize(
        argnames="marketpalces, configs, expected_is_valid",
        argvalues=[
            (
                [MarketplaceVersions.MarketplaceV2.value],
                INCIDENT_FETCH_REQUIRED_PARAMS,
                False,
            ),
            (
                [MarketplaceVersions.MarketplaceV2.value],
                ALERT_FETCH_REQUIRED_PARAMS,
                True,
            ),
            ([MarketplaceVersions.XSOAR.value], INCIDENT_FETCH_REQUIRED_PARAMS, True),
            ([MarketplaceVersions.XSOAR.value], ALERT_FETCH_REQUIRED_PARAMS, False),
            (
                [
                    MarketplaceVersions.XSOAR.value,
                    MarketplaceVersions.MarketplaceV2.value,
                ],
                ALERT_FETCH_REQUIRED_PARAMS,
                False,
            ),
            (
                [
                    MarketplaceVersions.XSOAR.value,
                    MarketplaceVersions.MarketplaceV2.value,
                ],
                INCIDENT_FETCH_REQUIRED_PARAMS,
                True,
            ),
        ],
    )
    def test_fetch_field_per_marketplaces_value(
        self, marketpalces, configs, expected_is_valid
    ):
        self.validator.current_file["marketplaces"] = marketpalces
        self.validator.current_file["configuration"] = configs
        self.validator.current_file["script"]["isfetch"] = True
        assert (
            self.validator.is_valid_fetch() == expected_is_valid
        ), f"is_valid_fetch() should returns {expected_is_valid}"


class TestIsValidMaxFetchAndFirstFetch:
    """
    Given
    - yml file of integration as config
    When
    - run validate checks
    Then
    - if the isfetch identifier is true make sure the first_fetch and max_fetch params exists
    - make sure max_fetch param has a default value
    """

    def setup_method(self):
        config = {
            "configuration": deepcopy([FIRST_FETCH_PARAM, MAX_FETCH_PARAM]),
            "script": {"isfetch": True},
        }
        self.validator = IntegrationValidator(mock_structure("", config))

    def test_valid(self):
        assert (
            self.validator.is_valid_max_fetch_and_first_fetch()
        ), "is_valid_fetch() returns False instead True"

    def test_missing_max_fetch(self):
        # missing param in configuration
        self.validator.current_file["configuration"] = [
            t
            for t in self.validator.current_file["configuration"]
            if t["name"] != "max_fetch"
        ]
        assert (
            self.validator.is_valid_max_fetch_and_first_fetch() is False
        ), "is_valid_fetch() returns True instead False"

    def test_missing_default_value_in_max_fetch(self):
        # missing param in configuration
        for param in self.validator.current_file["configuration"]:
            if param.get("name") == "max_fetch":
                param.pop("defaultvalue")
        assert (
            self.validator.is_valid_max_fetch_and_first_fetch() is False
        ), "is_valid_fetch() returns True instead False"

    def test_missing_fetch_time(self):
        # missing param in configuration
        self.validator.current_file["configuration"] = [
            t
            for t in self.validator.current_file["configuration"]
            if t["name"] != "first_fetch"
        ]
        assert (
            self.validator.is_valid_max_fetch_and_first_fetch() is False
        ), "is_valid_fetch() returns True instead False"

    def test_not_fetch(self):
        self.validator.is_valid = True
        self.validator.current_file["script"]["isfetch"] = False
        assert (
            self.validator.is_valid_max_fetch_and_first_fetch()
        ), "is_valid_fetch() returns False instead True"


class TestIsFeedParamsExist:
    def setup_method(self):
        config = {
            "configuration": deepcopy(FEED_REQUIRED_PARAMS_STRUCTURE),
            "script": {"feed": True},
        }
        self.validator = IntegrationValidator(mock_structure("", config))

    def test_valid(self):
        assert (
            self.validator.all_feed_params_exist()
        ), "all_feed_params_exist() returns False instead True"

    def test_sanity(self):
        # missing param in configuration
        self.validator.current_file["configuration"] = [
            t
            for t in self.validator.current_file["configuration"]
            if not t.get("display")
        ]
        assert (
            self.validator.all_feed_params_exist() is False
        ), "all_feed_params_exist() returns True instead False"

    def test_missing_field(self):
        # missing param
        configuration = self.validator.current_file["configuration"]
        for i in range(len(configuration)):
            if not configuration[i].get("display"):
                del configuration[i]["name"]
        self.validator.current_file["configuration"] = configuration
        assert (
            self.validator.all_feed_params_exist() is False
        ), "all_feed_params_exist() returns True instead False"

    def test_malformed_field(self):
        # incorrect param
        self.validator.current_file["configuration"] = []
        for t in self.validator.current_file["configuration"]:
            if not t.get("display"):
                t["type"] = 123
            self.validator.current_file["configuration"].append(t)

        assert (
            self.validator.all_feed_params_exist() is False
        ), "all_feed_params_exist() returns True instead False"

    def test_hidden_feed_reputation_field(self):
        # the feed reputation param is hidden
        configuration = self.validator.current_file["configuration"]
        for item in configuration:
            if item.get("name") == "feedReputation":
                item["hidden"] = True
        assert (
            self.validator.all_feed_params_exist() is True
        ), "all_feed_params_exist() returns False instead True for feedReputation param"

    def test_section_field_feed(self):
        """
        Given:
        - Parameters of feed integration, where one parameter as a 'section: collect' property.

        When:
        - Integration has all feed required params and running all_feed_params_exist on it.

        Then:
        - Ensure that all_feed_params_exists() returns true,
            which means validation did not fail on the additional section field.
        """
        configuration = self.validator.current_file["configuration"]
        for item in configuration:
            if item.get("name") == "feedReputation":
                item["section"] = "Collect"
        assert (
            self.validator.all_feed_params_exist() is True
        ), "all_feed_params_exist() returns False instead True for feedReputation param"

    def test_additional_info_contained(self):
        """
        Given:
        - Parameters of feed integration.

        When:
        - Integration has all feed required params, and additionalinfo containing the expected additionalinfo parameter.

        Then:
        - Ensure that all_feed_params_exists() returns true.
        """
        configuration = self.validator.current_file["configuration"]
        for item in configuration:
            if item.get("additionalinfo"):
                item["additionalinfo"] = f"""{item['additionalinfo']}."""
        assert (
            self.validator.all_feed_params_exist() is True
        ), "all_feed_params_exist() returns False instead True"

    def test_value_for_marketplace_feed(self):
        configuration = self.validator.current_file["configuration"]
        for item in configuration:
            if item.get("name") == "feed":
                item["name:xsoar"] = "test-name"
                item["something:xsoar"] = "test"
        assert (
            self.validator.all_feed_params_exist() is True
        ), "all_feed_params_exist() returns False instead True"

    NO_HIDDEN = {
        "configuration": [
            {"id": "new", "name": "new", "display": "test"},
            {"d": "123", "n": "s", "r": True},
        ]
    }
    HIDDEN_FALSE = {
        "configuration": [
            {"id": "n", "hidden": False},
            {"display": "123", "name": "serer"},
        ]
    }
    HIDDEN_TRUE = {
        "configuration": [
            {"id": "n", "n": "n"},
            {"display": "123", "required": "false", "hidden": True},
        ]
    }
    HIDDEN_TRUE_AND_FALSE = {
        "configuration": [
            {"id": "n", "hidden": False},
            {"ty": "0", "r": "true", "hidden": True},
        ]
    }
    HIDDEN_ALLOWED_TRUE = {
        "configuration": [{"name": "longRunning", "required": "false", "hidden": True}]
    }
    HIDDEN_ALLOWED_FEED_REPUTATION = {
        "configuration": [
            {"name": "feedReputation", "required": "false", "hidden": True}
        ]
    }
    HIDDEN_TRUE_BUT_REPLACED_TYPE_0 = {
        "configuration": [
            {"type": 0, "display": "Username", "hidden": True},
            {"type": 9, "display": "Username"},
        ]
    }
    HIDDEN_TRUE_BUT_REPLACED_TYPE_12 = {
        "configuration": [
            {"type": 12, "display": "Username", "hidden": True},
            {"type": 9, "display": "Username"},
        ]
    }
    HIDDEN_TRUE_BUT_REPLACED_TYPE_14 = {
        "configuration": [
            {"type": 14, "display": "Username", "hidden": True},
            {"type": 9, "display": "Username"},
        ]
    }
    HIDDEN_TRUE_BUT_REPLACED_BY_NOT_ALLOWED = {
        "configuration": [
            {"type": 5, "display": "Username", "hidden": True},
            {"type": 9, "display": "Username"},
        ]
    }
    HIDDEN_TRUE_BUT_REPLACED_4 = {
        "configuration": [
            {"type": 4, "display": "Api key", "hidden": True},
            {"type": 9, "displaypassword": "API key"},
        ]
    }
    HIDDEN_ONE_REPLACED_TO_9_OTHER_NOT = {
        "configuration": [
            {"type": 4, "display": "API key", "hidden": True},
            {"type": 9, "displaypassword": "API key"},
            {"type": 4, "display": "Username", "hidden": True},
        ]
    }

    IS_VALID_HIDDEN_PARAMS = [
        (NO_HIDDEN, True),
        (HIDDEN_FALSE, True),
        (HIDDEN_TRUE, False),
        (HIDDEN_TRUE_AND_FALSE, False),
        (HIDDEN_ALLOWED_TRUE, True),
        (HIDDEN_ALLOWED_FEED_REPUTATION, True),
        (HIDDEN_TRUE_BUT_REPLACED_TYPE_0, True),
        (HIDDEN_TRUE_BUT_REPLACED_TYPE_12, True),
        (HIDDEN_TRUE_BUT_REPLACED_TYPE_14, True),
        (HIDDEN_TRUE_BUT_REPLACED_BY_NOT_ALLOWED, False),
        (HIDDEN_TRUE_BUT_REPLACED_4, True),
        (HIDDEN_ONE_REPLACED_TO_9_OTHER_NOT, False),
    ]

    @pytest.mark.parametrize("current, answer", IS_VALID_HIDDEN_PARAMS)
    def test_is_valid_hidden_params(self, current, answer):
        structure = mock_structure(current_file=current)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_hidden_params() is answer

    @pytest.mark.parametrize(
        "script_type, fromversion, res",
        [
            ("powershell", None, False),
            ("powershell", "4.5.0", False),
            ("powershell", "5.5.0", True),
            ("powershell", "5.5.1", True),
            ("powershell", "6.0.0", True),
            ("python", "", True),
            ("python", "4.5.0", True),
        ],
    )
    def test_valid_pwsh(self, script_type, fromversion, res):
        current = {
            "script": {"type": script_type},
            "fromversion": fromversion,
        }
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_pwsh() == res

    def test_empty_commands(self):
        """
        Given: an integration with no commands

        When: running validate on integration with no command.

        Then: Validate it's valid.
        """
        current = {"script": {"commands": None}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_valid_default_array_argument_in_reputation_command() is True

    @pytest.mark.parametrize(
        "param",
        [
            {"commands": ["something"]},
            {"isFetch": True},
            {"longRunning": True},
            {"feed": True},
        ],
    )
    def test_is_there_a_runnable(self, param):
        """
        Given: one of any runnable integration

        When: running validate on integration with at least one of commands, fetch, feed or long-running

        Then: Validate it's valid.
        """
        current = {"script": param}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_there_a_runnable() is True

    def test_is_there_a_runnable_negative(self):
        """
        Given: an integration with no runnable param

        When: running validate on integration with no one of commands, fetch, feed or long-running

        Then: Validate it's invalid.
        """
        current = {"script": {}}
        structure = mock_structure("", current)
        validator = IntegrationValidator(structure)
        validator.current_file = current
        assert validator.is_there_a_runnable() is False

    VERIFY_YML_COMMANDS_MATCH_README_DATA = [
        (
            True,
            {"script": {"commands": [{"name": "command_name"}]}},
            "## Commands\n### command_name\n somename",
            True,
        ),
        (
            True,
            {
                "script": {
                    "commands": [
                        {"name": "get-mapping-fields"},
                        {"name": "test-get-indicators"},
                    ]
                }
            },
            "",
            True,
        ),
        (True, {"script": {"commands": [{"name": "command_name"}]}}, "", False),
        (False, {"script": {"commands": [{"name": "command_name"}]}}, "", True),
    ]

    @pytest.mark.parametrize(
        "is_modified, yml_data, readme_text, excepted_results",
        VERIFY_YML_COMMANDS_MATCH_README_DATA,
    )
    def test_verify_yml_commands_match_readme(
        self,
        is_modified,
        yml_data,
        readme_text,
        excepted_results,
        integration: Integration,
    ):
        """
        Given
        - Case 1: integration with one command mentioned in both the yml and the readme files that were modified.
        - Case 2: integration with two commands that should be excluded from the readme file and mentioned in the yml
         file that were modified.
        - Case 3: integration with one command mentioned only in the yml file that were modified.
        - Case 4: integration with one command mentioned only in the yml file that aren't modified.
        When
        - Running verify_yml_commands_match_readme on the integration.
        Then
        - Ensure validation correctly identifies missed commands from yml or readme files.
        - Case 1: Should return True.
        - Case 2: Should return True.
        - Case 3: Should return False.
        - Case 4: Should return True.
        """
        integration.yml.write_dict(yml_data)
        integration.readme.write(readme_text)
        struct = mock_structure(current_file=yml_data, file_path=integration.yml.path)
        integration_validator = IntegrationValidator(struct)
        assert (
            integration_validator.verify_yml_commands_match_readme(is_modified)
            == excepted_results
        )

    def test_verify_yml_commands_match_readme_no_readme_file(
        self, integration: Integration
    ):
        """
        Given
        - integration with no readme file.
        When
        - Running verify_yml_commands_match_readme on the integration.
        Then
        - Ensure validation stops before checking if there is a match between the yml and readme.
        """
        yml_data = {"script": {"commands": [{"name": "command_name"}]}}
        integration.yml.write_dict(yml_data)
        struct = mock_structure(current_file=yml_data, file_path=integration.yml.path)
        integration_validator = IntegrationValidator(struct)
        assert (
            integration_validator.verify_yml_commands_match_readme(is_modified=True)
            is False
        )


class TestisContextChanged:
    invalid_readme = """
#### Base Command

`test-command`
#### Input
| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| arg | arg | Required |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| Test | - | - |

#### Command Example

```
!test-command
```

#### Human Readable Output
"""
    valid_readme = """
#### Base Command

`test-command`
#### Input
| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| arg | arg | Required |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| Test.test | - | - |

#### Command Example

```
!test-command
```

#### Human Readable Output
"""
    TEST_CASE = [
        (
            valid_readme,
            {
                "script": {
                    "commands": [
                        {
                            "name": "test-command",
                            "outputs": [
                                {
                                    "contextPath": "Test.test",
                                    "description": "-",
                                    "type": "-",
                                }
                            ],
                        }
                    ]
                }
            },  # case README and YML are synced
            True,  # expected results
        ),
        (
            invalid_readme,
            {
                "script": {
                    "commands": [
                        {
                            "name": "test-command",
                            "outputs": [
                                {
                                    "contextPath": "Test.test",
                                    "description": "-",
                                    "type": "-",
                                }
                            ],
                        }
                    ]
                }
            },  # case context missing from README
            False,  # expected results
        ),
        (
            valid_readme,
            {
                "script": {
                    "commands": [
                        {
                            "name": "test-command",
                            "outputs": [
                                {"contextPath": "Test", "description": "-", "type": "-"}
                            ],
                        }
                    ]
                }
            },  # case context missing from YML
            False,  # expected results
        ),
    ]

    @pytest.mark.parametrize("readme, current_yml, expected", TEST_CASE)
    def test_is_context_correct_in_readme(self, readme, current_yml, expected):
        """
        Given: a changed YML file
        When: running validate on integration with at least one command
        Then: Validate it's synced with the README.
        """
        patcher = patch("pathlib.Path.exists")
        mock_thing = patcher.start()
        mock_thing.side_effect = lambda: True
        with patch("builtins.open", mock_open(read_data=readme)) as _:
            current = {"script": {}}
            structure = mock_structure("Pack/Test", current)
            validator = IntegrationValidator(structure)
            validator.current_file = current_yml
            res = validator.is_context_correct_in_readme()
            assert res == expected
        patcher.stop()

    README_TEST_DATA = [
        (False, False, True),
        (False, True, True),
        (True, False, False),
        (True, True, True),
    ]

    @pytest.mark.parametrize(
        "remove_readme, validate_all, expected_result", README_TEST_DATA
    )
    @pytest.mark.parametrize("unified", [True, False])
    def test_validate_readme_exists(
        self, repo, unified, remove_readme, validate_all, expected_result
    ):
        """
        Given:
            - An integration yml that was added or modified to validate

        When:
              All the tests occur twice for unified integrations = [True - False]
            - The integration is missing a readme.md file in the same folder
            - The integration has a readme.md file in the same folder
            - The integration is missing a readme.md file in the same folder but has not been changed or added
                (This check is for backward compatibility)

        Then:
            - Ensure readme exists and validation fails
            - Ensure readme exists and validation passes
            - Ensure readme exists and validation passes
        """
        read_me_pack = repo.create_pack("README_test")
        integration = read_me_pack.create_integration(
            "integration1", create_unified=unified
        )

        structure_validator = StructureValidator(integration.yml.path)
        integration_validator = IntegrationValidator(
            structure_validator, validate_all=validate_all
        )
        if remove_readme:
            Path(integration.readme.path).unlink()
        assert (
            integration_validator.validate_readme_exists(
                integration_validator.validate_all
            )
            is expected_result
        )

    @pytest.mark.parametrize(
        "integration_yml, is_validation_ok",
        [
            (
                {"script": {"nativeimage": "test"}, "commonfields": {"id": "test"}},
                False,
            ),
            ({"commonfields": {"id": "test"}}, True),
        ],
    )
    def test_is_native_image_does_not_exist_in_yml_fail(
        self, repo, integration_yml, is_validation_ok
    ):
        """
        Given:
            - Case A: integration yml that has the nativeimage key
            - Case B: integration yml that does not have the nativeimage key
        When:
            - when executing the is_native_image_does_not_exist_in_yml method
        Then:
            - Case A: make sure the validation fails.
            - Case B: make sure the validation pass.
        """
        pack = repo.create_pack("test")
        integration = pack.create_integration(yml=integration_yml)
        structure_validator = StructureValidator(integration.yml.path)
        integration_validator = IntegrationValidator(structure_validator)

        assert (
            integration_validator.is_native_image_does_not_exist_in_yml()
            == is_validation_ok
        )

    @pytest.mark.parametrize(
        "yml_content, use_git, expected_results",
        [
            ({"description": "description without dot"}, False, True),
            (
                {
                    "description": "a yml description with a dot at the end.",
                    "script": {
                        "commands": [
                            {
                                "arguments": [
                                    {
                                        "name": "test_arg",
                                        "description": "description without dot",
                                    }
                                ]
                            }
                        ],
                        "name": "test_command",
                    },
                },
                True,
                False,
            ),
            (
                {
                    "description": "a yml description with a dot at the end.",
                    "script": {
                        "commands": [
                            {
                                "outputs": [
                                    {
                                        "contextPath": "test.path",
                                        "description": "description without dot",
                                    }
                                ]
                            }
                        ],
                        "name": "test_command",
                    },
                },
                True,
                False,
            ),
            (
                {
                    "description": "a yml description with a dot at the end.",
                    "script": {
                        "commands": [
                            {
                                "arguments": [
                                    {
                                        "name": "test_arg",
                                        "description": "description with dot.",
                                    }
                                ]
                            }
                        ],
                        "name": "test_command",
                    },
                },
                True,
                True,
            ),
            (
                {
                    "description": "a yml description with a dot at the end.",
                    "script": {
                        "commands": [
                            {
                                "outputs": [
                                    {
                                        "contextPath": "test.path",
                                        "description": "description with dot.",
                                    }
                                ]
                            }
                        ],
                        "name": "test_command",
                    },
                },
                True,
                True,
            ),
            (
                {
                    "description": "a yml description that ends with a url www.test.com",
                },
                True,
                True,
            ),
            (
                {
                    "description": "a yml with a description that has www.test.com in the middle of the sentence",
                },
                True,
                False,
            ),
            (
                {
                    "description": "a yml with a description that has an 'example without dot at the end of the string.'",
                },
                True,
                True,
            ),
            (
                {
                    "description": "a yml with a description that has a trailing new line.\n",
                },
                True,
                True,
            ),
            (
                {
                    "description": "a yml with a description that has a trailing new line.\n",
                },
                True,
                True,
            ),
            (
                {
                    "description": "a yml description with a dot at the end.",
                    "script": {
                        "commands": [
                            {
                                "outputs": [
                                    {
                                        "contextPath": "test.path",
                                        "description": "",
                                    }
                                ]
                            }
                        ],
                        "name": "test_command",
                    },
                },
                True,
                True,
            ),
            (
                {
                    "description": "a yml description with a dot in the bracket (like this.)",
                    "script": {
                        "commands": [
                            {
                                "outputs": [
                                    {
                                        "contextPath": "test.path",
                                        "description": "a contextPath description with a dot in the bracket (like this.)",
                                    }
                                ]
                            }
                        ],
                        "name": "test_command",
                    },
                },
                True,
                True,
            ),
            (
                {"description": "This description is okay!"},
                True,
                True,
            ),
            (
                {
                    "description": 'This description ends with a json list [\n{\n"name": "example json ending on another line"\n}\n]'
                },
                True,
                True,
            ),
        ],
    )
    def test_is_line_ends_with_dot(
        self, repo, yml_content: dict, use_git: bool, expected_results: bool
    ):
        """
        Given:
            A yml content, use_git flag, and expected_results.
            - Case 1: A yml content with a description without a dot at the end of the sentence, and use_git flag set to False.
            - Case 2: A yml content with a command that an argument with a description without a dot at the end of the sentence, and use_git flag set to True.
            - Case 3: A yml content with a command that a context path with a description without a dot at the end of the sentence, and use_git flag set to True.
            - Case 4: A yml content with a command that an argument with a description with a dot at the end of the sentence, and use_git flag set to True.
            - Case 5: A yml content with a command that a context path with a description with a dot at the end of the sentence, and use_git flag set to True.
            - Case 6: A yml content with a description that ends with a url address and not dot, and use_git flag set to True.
            - Case 7: A yml content with a description that has a url in the middle of the sentence and no comment in the end, and use_git flag set to True.
            - Case 8: A yml content with a description that ends with example quotes with a dot only inside the example quotes, and use_git flag set to True.
            - Case 9: A yml content with a description that ends with a dot followed by new line, and use_git flag set to True.
            - Case 10: A yml content with an empty description, and use_git flag set to True.
            - Case 11: A yml content with a command with an empty description for the output contextPath, and use_git flag set to True.
            - Case 12: A yml content with a description and contextPath with a description that ends with a dot inside a bracket, and use_git flag set to True.
            - Case 13: A yml content with a description that ends with exclamation mark, and use_git flag set to True.
            - Case 14: a yml content with a description that ends with new line followed by square bracket, and use_git flag set to True.
        When:
            - when executing the is_line_ends_with_dot method
        Then:
            - Case 1: make sure the validation pass.
            - Case 2: make sure the validation fails.
            - Case 3: make sure the validation fails.
            - Case 4: make sure the validation pass.
            - Case 5: make sure the validation pass.
            - Case 6: make sure the validation pass.
            - Case 7: make sure the validation fails.
            - Case 8: make sure the validation pass.
            - Case 9: make sure the validation pass.
            - Case 10: make sure the validation pass.
            - Case 11: make sure the validation pass.
            - Case 12: make sure the validation pass.
            - Case 13: make sure the validation pass.
            - Case 14: make sure the validation pass.
        """
        pack = repo.create_pack("test")
        integration = pack.create_integration(yml=yml_content)
        structure_validator = StructureValidator(integration.yml.path)
        integration_validator = IntegrationValidator(
            structure_validator, json_file_path=integration.yml.path, using_git=use_git
        )
        assert integration_validator.is_line_ends_with_dot() is expected_results

    VALID_COMMAND_OUTPUTS = {
        "name": "url",
        "outputs": [
            {
                "contextPath": "URL.Data",
                "description": "test description.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Indicator",
                "description": "The indicator that was tested.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Type",
                "description": "The indicator type.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Vendor",
                "description": "The vendor used to calculate the score.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Score",
                "description": "The actual score.",
                "type": "string",
            },
        ],
    }
    INVALID_COMMAND_OUTPUTS = {
        "name": "url",
        "outputs": [
            {
                "contextPath": "Url.Data",
                "description": "data.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Indicator",
                "description": "The indicator that was tested.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Type",
                "description": "The indicator type.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Vendor",
                "description": "The vendor used to calculate the score.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Score",
                "description": "The actual score.",
                "type": "string",
            },
        ],
    }
    MISSING_COMMAND_OUTPUTS = {
        "name": "endpoint",
        "outputs": [
            {
                "contextPath": "Endpoint.Critical",
                "description": "The percentage of critical findings on the host.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Indicator",
                "description": "The indicator that was tested.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Type",
                "description": "The indicator type.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Vendor",
                "description": "The vendor used to calculate the score.",
                "type": "string",
            },
            {
                "contextPath": "DBotScore.Score",
                "description": "The actual score.",
                "type": "string",
            },
        ],
    }
    IS_OUTPUT_FOR_REPUTATION_INPUTS = [
        (VALID_COMMAND_OUTPUTS, True),
        (INVALID_COMMAND_OUTPUTS, False),
        (MISSING_COMMAND_OUTPUTS, False),
    ]

    @pytest.mark.parametrize("outputs, result", IS_OUTPUT_FOR_REPUTATION_INPUTS)
    def test_is_valid_spelling_command_custom_outputs(
        self, outputs: List[Dict[str, Any]], result: bool
    ):
        """
        Cover IN159 validation which validates the spelling of command output paths for reputation commands.
        Given
        The outputs and command_name of a command context.
            - Case 1: A valid command output, URL is spelled correctly, all DBotScore outputs are present.
            - Case 2: An invalid command output, URL is not spelled correctly (Url), all DBotScore outputs are present.
            - Case 3: An invalid command output, Endpoint is missing one of the mandatory output paths (ID, IPAddress, Hostname), all DBotScore outputs are present.
        When
        - Calling the is_outputs_for_reputations_commands_valid validation.
        Then
            - Case 1: Make sure validation pass.
            - Case 2: Make sure validation fails.
            - Case 3: Make sure validation fails.
        """
        content = {"script": {"commands": [outputs]}}
        structure = mock_structure("", content)
        validator = IntegrationValidator(structure)
        validator.current_file = content
        assert validator.is_outputs_for_reputations_commands_valid() == result
