from demisto_sdk.commands.common.constants import DEMISTO_SDK_CONFIG_FILE
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


def test_conf_file_override_default_command_arguments(repo: Repo):
    """
    Given:
        argument1: has default value of True, but in the config value of false
        argument2: has a default value of False, but in the config value of true
        argument3: has a default value = "default_value", but in the config value = "config_value"

    When:
        Calling update_command_args_from_config_file function

    Then:
        Validate that the arguments are being updated with the arguments from the config.

    """
    from demisto_sdk.utils.utils import update_command_args_from_config_file

    command_args = {"argument1": True, "argument2": False, "argument3": "default_value"}
    command_name = "validate"
    repo.make_file(
        DEMISTO_SDK_CONFIG_FILE,
        file_content=f"[{command_name}]\nargument1=false\nargument2=true\nargument3=config_value",
    )
    with ChangeCWD(repo.path):
        update_command_args_from_config_file(command_name, command_args)

    assert command_args["argument1"] is False
    assert command_args["argument2"] is True
    assert command_args["argument3"] == "config_value"


def test_conf_file_add_command_arguments(repo: Repo):
    """
    Given:
        argument1: does not have any default value, but in the config value of false
        argument2: does not have any default value, but in the config value of true
        argument3: does not have any default value, but in the config value = "config_value"

    When:
        Calling update_command_args_from_config_file function

    Then:
        Validate that the arguments are being updated with the arguments from the config.

    """
    from demisto_sdk.utils.utils import update_command_args_from_config_file

    command_args = {}
    command_name = "format"
    repo.make_file(
        DEMISTO_SDK_CONFIG_FILE,
        file_content=f"[{command_name}]\nargument1=false\nargument2=true\nargument3=config_value",
    )
    with ChangeCWD(repo.path):
        update_command_args_from_config_file(command_name, command_args)

    assert command_args["argument1"] is False
    assert command_args["argument2"] is True
    assert command_args["argument3"] == "config_value"
