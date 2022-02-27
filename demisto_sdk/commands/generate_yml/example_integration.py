"""This file is a part of the generating yml design. Generating a yml file from a python file.

This is an example for an integration containing a general configuration, commands and helper functions.
"""
import enum

import hlem
from yml_metadata_collector import (ConfKey, ConfTypesEnum, InputArgument,
                                    YMLMetadataCollector)

hlem.hello()

# The exact keyword metadata_collector should be used to init the YMLMetadataCollector of the integration
metadata_collector = YMLMetadataCollector(integration_name="NewIntegration",
                                          description="A new integration",
                                          conf=[ConfKey(name="api_key"),
                                                ConfKey(name="is_important", key_type=ConfTypesEnum.BOOLEAN_CHECKBOX)])


class CommandResults:
    def __init__(self, outputs_prefix, outputs_key_field, outputs):
        self.outputs_prefix = outputs_prefix
        self.outputs_key_field = outputs_key_field
        self.outputs = outputs


# Adding a decorator from the YMLMetadataCollector object in the following way
COMMAND_ONE_OUTPUTS = {
    "some_field": (str, "some description"),
    "other_field": (int, "some other field")
}


@metadata_collector.command(command_name='first_command', outputs_prefix="NewIntegration.first",
                            outputs_dict=COMMAND_ONE_OUTPUTS)
def this_is_a_command(some_arg1, command_name, outputs_prefix, outputs_key_field, outputs_dict) -> CommandResults:
    """Some Documentation

    :param some_arg1: some arg1 description.
    """
    print(f"my command name is {command_name}")
    outputs_dict["some_field"] = some_arg1
    print(f"empty_outputs is {outputs_dict}")
    return CommandResults(
        outputs_prefix=outputs_prefix,
        outputs_key_field=outputs_key_field,
        outputs=outputs_dict
    )


# Example of helper function not being affected by the YMLMetadataCollector
def this_is_a_helper_func():
    """Some helper docs"""
    print("helper")


class ExampleEnum(enum.Enum):
    EXAMPLE_FIRST_OPTION = "FirstOption"
    EXAMPLE_SECOND_OPTION = "SecondOption"


# Multiple usage of the same decorator are welcome.
# To not use the kwargs sent, we need to use **kwargs in function declaration.
@metadata_collector.command(command_name='other_command')
def this_is_another_command(arg1: ExampleEnum, **kwargs):
    """Some other command

        :param arg1: some arg1 description
    """
    print(f"other command with arg {arg1}")


COMMAND_THREE_INPUTS = [InputArgument(name="the_arg", description="the arg desc", is_array=False),
                        InputArgument(name="pre_arg", options=["Hello", "Hi"])]


# Multiple usage of the same decorator are welcome.
# To not use the kwargs sent, we need to use **kwargs in function declaration.
@metadata_collector.command(command_name='third_command', inputs_list=COMMAND_THREE_INPUTS)
def this_is_a_third_command(arg1: ExampleEnum, **kwargs):
    """Some other command

        :param arg1: some arg1 description
    """
    print(f"other command with arg {arg1}")


# This is called as a sanity check making sure the decorators do not interrupt the run
this_is_a_command("hello")
# this_is_another_command("hello")
