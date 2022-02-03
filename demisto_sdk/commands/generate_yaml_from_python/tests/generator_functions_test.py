import json

import pytest

from demisto_sdk.commands.generate_yaml_from_python.generator_functions import *
from demisto_sdk.tests.test_files.fake_annotated_integration.fake_annotated_integration import *
from demisto_sdk.tests.test_files.fake_annotated_integration.output_dicts import *


@pytest.mark.parametrize(
    "fake_command_name,test_result_dict",
    [
        ("fake-command", fake_command_dict()),
        ("fake-command-optional-argument", fake_command_optional_argument_dict()),
    ]
)
def test_command_from_function(fake_command_name, test_result_dict):
    command_register = COMMANDS
    fake_command_func = command_register.commands.get(fake_command_name)

    result = command_from_function(fake_command_name, fake_command_func)
    print(json.dumps(result, indent=4))
    assert result == test_result_dict
