import json

import pytest

from demisto_sdk.commands.generate_yaml_from_python.generator_functions import *
from demisto_sdk.tests.test_files.fake_annotated_integration.fake_annotated_integration import (
    COMMANDS, ExampleReturnClass, DemistoParameters)
from demisto_sdk.tests.test_files.fake_annotated_integration.output_dicts import *


def test_build_script_commands_from_register():
    result = build_script_commands_from_register(COMMANDS)
    assert len(result) == 4


@pytest.mark.parametrize(
    "fake_command_name,test_result_dict",
    [
        ("fake-command", fake_command_dict()),
        ("fake-command-optional-argument", fake_command_optional_argument_dict()),
        ("fake-command-enum-argument", fake_command_enum_argument_dict()),
        ("fake-command-list-argument", fake_command_list_argument_dict())
    ]
)
def test_command_from_function(fake_command_name, test_result_dict):
    command_register = COMMANDS
    fake_command_func = command_register.commands.get(fake_command_name)

    result = command_from_function(fake_command_name, fake_command_func)
    assert result == test_result_dict


def test_grid_field_from_class():
    result = grid_fields_from_class(ExampleReturnClass)
    assert result == grid_field_result()


def test_build_configuration_from_param_class():
    result = build_configuration_from_param_class(DemistoParameters)
    assert result == integration_params_result()