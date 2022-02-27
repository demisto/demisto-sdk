"""This file is a part of the generating yml design. Generating a yml file from a python file."""
import enum
from typing import Any, List


class InputArgument:
    def __init__(self, name, description='', required=False, default=None,
                 is_array=False, secret=False, execution=False, options=[]):
        self.name = name
        self.description = description
        self.required = required
        self.default = default
        self.is_array = is_array
        self.secret = secret
        self.execution = execution
        self.options = options


class ConfTypesEnum(enum.Enum):
    SHORT_TEXT = 0
    ENCRYPTED_TEXT = 4
    BOOLEAN_CHECKBOX = 8
    AUTH_TEXT = 9
    LONG_TEXT = 12
    INCIDENT_SINGLE_SELECT = 13
    SINGLE_SELECT = 15
    MULTIPLE_SELECT = 16


class ConfKey:
    def __init__(self, name: str, display: str = "", default_value: Any = None,
                 key_type: ConfTypesEnum = ConfTypesEnum.SHORT_TEXT, required: bool = False,
                 additional_info: str = ""):
        self.name = name
        self.display = display if display else name
        self.default_value = default_value
        self.key_type = key_type.value
        self.required = required
        self.additional_info = additional_info


class YMLMetadataCollector:
    """The YMLMetadataCollector class provides decorators for integration
    functions which contain details relevant to yml generation.

    If collect_data is set to true, calling the decorated functions will result in
    collecting the relevant details and not running them. If it is set to false,
    the run should remain unchanged.
    """
    # Restored args will not be shown in the YML unless they are added as an InputArgument.
    RESTORED_ARGS = ['command_name', 'outputs_prefix', 'outputs_key_field', 'outputs_dict',
                     'kwargs', 'args', 'inputs_list']

    def __init__(self, integration_name, docker_image="demisto/python3:latest",
                 description="", category="Utilities", conf: List[ConfKey] = [], is_feed=False,
                 is_fetch=False, is_runonce=False, detailed_description="", image=None,
                 display="", tests=["No tests"], fromversion="6.0.0", long_running=False, long_running_port=False,
                 integration_type="python", integration_subtype="python3", deprecated=False, system=False,
                 timeout=""):
        self.docs = {}
        self.command_names = []
        self.functions = {}
        self.outputs = {}
        self.inputs = {}
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

    def set_collect_data(self, value):
        """A setter for collect_data."""
        self.collect_data = value

    def command(self, command_name='', outputs_prefix='', outputs_dict=None, inputs_list=None):
        """Decorator for integration command function.

        Args:
            command_name: The name of the command.
            outputs_prefix: The command results' output prefix.
            outputs_dict: The command results' outputs dict in the format {"some_field": (type, "description")}.
            inputs_list: The command input arguments.

        Return: A wrapper for the command function with the following restored args:
           command_name: The name of the command
           outputs_prefix: The command results' output prefix.
           outputs_dict: The command results' empty outputs dict. {"some_field": None}
        """
        print("adding command")

        def command_wrapper(func):
            """The wrapper of the command function."""
            def get_out_info(*args, **kwargs):
                """The function which will collect data if needed or
                run the original function instead."""
                print(f"collect_data {self.collect_data}")
                if self.collect_data:
                    print("collecting")
                    # Collect details from function declaration and builtins.
                    self.docs[command_name] = func.__doc__
                    self.functions[command_name] = func
                    self.outputs[command_name] = {}
                    if outputs_prefix or outputs_dict:
                        self.outputs[command_name] = {
                            'outputs_prefix': outputs_prefix,
                            'outputs_dict': outputs_dict,
                        }
                    if inputs_list:
                        self.inputs[command_name] = inputs_list
                else:
                    # Send back the details provided to be used in function and reduce code duplication.
                    kwargs['command_name'] = command_name
                    kwargs['outputs_prefix'] = outputs_prefix
                    kwargs['outputs_dict'] = dict.fromkeys(outputs_dict.keys()) if outputs_dict else None
                    func(*args, **kwargs)
            return get_out_info

        self.command_names.append(command_name)
        return command_wrapper
