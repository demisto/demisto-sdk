"""This file is a part of the generating yml design. Generating a yml file from a python file."""
import enum
import re
from typing import Any, Callable, List, Union

import click


class InputArgument:
    """YML input argument for a command."""

    def __init__(self, name: str = '', description: str = '', required: bool = False, default: Any = None,
                 is_array: bool = False, secret: bool = False, execution: bool = False, options: list = [],
                 input_type: Union[enum.EnumMeta, None] = None):
        # if name is not provided convert class name to camel case
        self.name = name if name else re.sub(r'(?<!^)(?=[A-Z])', '_', self.__class__.__name__).lower()
        self.description = description
        self.required = required
        self.default = default
        self.is_array = is_array
        self.secret = secret
        self.execution = execution
        self.options = options
        self.input_type = input_type


class ConfTypesEnum(enum.Enum):
    """YML configuration key types."""
    SHORT_TEXT = 0
    ENCRYPTED_TEXT = 4
    BOOLEAN_CHECKBOX = 8
    AUTH_TEXT = 9
    LONG_TEXT = 12
    INCIDENT_SINGLE_SELECT = 13
    SINGLE_SELECT = 15
    MULTIPLE_SELECT = 16


class OutputArgument:
    """YML output argument."""

    def __init__(self, name: str, output_type: Any, description: str, prefix: str = ''):
        self.name = name
        self.output_type = output_type
        self.description = description
        self.prefix = prefix


class ConfKey:
    """YML configuration key fields."""

    def __init__(self, name: str, display: str = "", default_value: Any = None,
                 key_type: ConfTypesEnum = ConfTypesEnum.SHORT_TEXT, required: bool = False,
                 additional_info: str = "", options: list = []):
        self.name = name
        self.display = display if display else name
        self.default_value = default_value
        self.key_type = key_type.value
        self.required = required
        self.additional_info = additional_info
        self.options = options


class CommandMetadata:
    def __init__(self, name: str, doc: str, function: Callable, outputs: list,
                 inputs: list, file_output: bool, multiple_output_prefixes: bool, outputs_prefix: str,
                 execution: bool):
        self.name = name
        self.doc = doc
        self.function = function
        self.outputs = outputs
        self.inputs = inputs
        self.file_output = file_output
        self.multiple_output_prefixes = multiple_output_prefixes
        self.outputs_prefix = outputs_prefix
        self.execution = execution


class YMLMetadataCollector:
    """The YMLMetadataCollector class provides decorators for integration
    functions which contain details relevant to yml generation.

    If collect_data is set to true, calling the decorated functions will result in
    collecting the relevant details and not running them. If it is set to false,
    the run should remain unchanged.
    """
    # Restored args will not be shown in the YML unless they are added as an InputArgument.
    RESTORED_ARGS = ['command_name', 'outputs_prefix', 'outputs_key_field', 'outputs_dict',
                     'kwargs', 'args', 'inputs_list', 'client']

    def __init__(self, integration_name: str, docker_image: str = "demisto/python3:latest",
                 description: str = "", category: str = "Utilities", conf: List[ConfKey] = [], is_feed: bool = False,
                 is_fetch: bool = False, is_runonce: bool = False, detailed_description: str = "",
                 image: str = "", display: str = "", tests: list = ["No tests"], fromversion: str = "6.0.0",
                 long_running: bool = False, long_running_port: bool = False, integration_type: str = "python",
                 integration_subtype: str = "python3", deprecated: bool = False, system: bool = False,
                 timeout: str = "", default_classifier: str = "", default_mapper_in: str = ""):
        self.commands = []
        self.collect_data = False

        # Integration configurations
        self.integration_name = integration_name
        self.display = display if display else integration_name
        self.image = image
        self.detailed_description = detailed_description
        self.docker_image = docker_image
        self.description = description
        self.category = category
        self.conf = conf
        self.is_feed = is_feed
        self.is_fetch = is_fetch
        self.is_runonce = is_runonce
        self.tests = tests
        self.fromversion = fromversion
        self.long_running = long_running
        self.long_running_port = long_running_port
        self.integration_type = integration_type
        self.integration_subtype = integration_subtype
        self.deprecated = deprecated
        self.system = system
        self.timeout = timeout
        self.default_classifier = default_classifier
        self.default_mapper_in = default_mapper_in

    def set_collect_data(self, value: bool):
        """A setter for collect_data."""
        self.collect_data = value

    def command(self, command_name: str = '', outputs_prefix: str = '', outputs_list: list = [],
                inputs_list: list = [], execution: bool = False, file_output: bool = False,
                multiple_output_prefixes: bool = False) -> Callable:
        """Decorator for integration command function.

        Args:
            command_name: The name of the command.
            outputs_prefix: The command results' output prefix.
            outputs_list: The command results' outputs list of OutputArgument.
            inputs_list: The command input arguments.
            file_output: True if the command outputs file.

        Return: A wrapper for the command function with the following restored args:
           command_name: The name of the command
           outputs_prefix: The command results' output prefix.
           outputs_dict: The command results' empty outputs dict. {"some_field": None}
        """

        def command_wrapper(func: Callable):
            """The wrapper of the command function."""
            def get_out_info(*args, **kwargs):
                """The function which will collect data if needed or
                run the original function instead."""
                if self.collect_data:
                    click.secho(f"Collecting metadata from command {command_name}")
                    # Collect details from function declaration and builtins.
                    command_metadata = CommandMetadata(
                        name=command_name,
                        doc=func.__doc__,
                        function=func,
                        inputs=inputs_list if inputs_list else None,
                        outputs=outputs_list if outputs_list else [],
                        file_output=file_output,
                        outputs_prefix=outputs_prefix if outputs_prefix else '',
                        multiple_output_prefixes=multiple_output_prefixes,
                        execution=execution
                    )
                    self.commands.append(command_metadata)
                else:
                    # Send back the details provided to be used in function and reduce code duplication.
                    kwargs['command_name'] = command_name
                    kwargs['outputs_prefix'] = outputs_prefix
                    # TODO: maybe make empty dict here.
                    # kwargs['outputs_dict'] = dict.fromkeys(outputs_dict.keys()) if outputs_dict else None
                    kwargs['execution'] = execution
                    func(*args, **kwargs)
            return get_out_info

        # self.command_names.append(command_name)
        return command_wrapper
