import json
import os

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


def test_merge_integration_dicts():
    merge_integration_dict = example_merge_integration_dict()
    new_integration_dict = example_new_integration_dict()
    result = merge_integration_dicts(merge_integration_dict, new_integration_dict, None)

    assert len(result.get("script").get("commands")) == 2
    assert result.get("script").get("commands")[0].get("description") == "updated"
    assert result.get("script").get("commands")[1].get("description") == "new"

def test_full_generator():
    # Try with an absolute path to a file
    path_to_this_test_file = os.path.abspath(__file__)
    path_to_fake_integration = path_to_this_test_file.split(os.path.sep)[:-4] + ["tests", "test_files", "fake_annotated_integration", "fake_annotated_integration.py"]
    path_to_fake_integration = os.path.sep.join(path_to_fake_integration)
    result = PythonIntegrationGenerator.build_dict_from_module(
        integration_path=path_to_fake_integration,
        integration_name="fake_annotated_integration"
    )

    assert result == full_fake_integration_result_dict()

    # Try with a module path as well
    PythonIntegrationGenerator.build_dict_from_module(
        integration_path="demisto_sdk.tests.test_files.fake_annotated_integration.fake_annotated_integration",
        integration_name="fake_annotated_integration"
    )
