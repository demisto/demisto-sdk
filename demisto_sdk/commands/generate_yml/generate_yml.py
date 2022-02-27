"""This file is a part of the generating yml design. Generating a yml file from a python file."""
import datetime
import importlib.util
import inspect
from enum import EnumMeta
from types import FunctionType
from typing import AnyStr, Union

import mock
import yaml
from docstring_parser import parse
from yml_metadata_collector import ConfKey, YMLMetadataCollector


class YMLGenerator:
    """The YMLGenerator class preforms the following:
        1. Obtain the relevant YMLMetadataCollector object from the specified python file.
        2. Make a list of the decorated functions from the specified python file.
        3. Use metadata_collector to collect the details from the relevant python file.
        4. Generate YML file based on the details collected.
    """

    def __init__(self, filename):
        self.functions = []
        self.filename = filename
        self.metadata_collector = None
        self.file_import = None
        self.import_the_metadata_collector()
        print(f"{self.metadata_collector}")

    def import_the_metadata_collector(self):
        """Find the metadata_collector object in the python file and import it."""
        orig_import = __import__
        mock_obj = mock.Mock()

        def import_mock(name, *args):
            if name not in ['InputArgument', 'ConfTypesEnum', 'ConfKey', 'YMLMetadataCollector',
                            'yml_metadata_collector']:
                return mock_obj
            return orig_import(name, *args)

        with mock.patch('builtins.__import__', side_effect=import_mock):
            spec = importlib.util.spec_from_file_location("metadata_collector", self.filename)
            # The self.file_import object will be used later to identify wrapped functions.
            self.file_import = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.file_import)
            # Here we assume the details_collector object will be called 'metadata_collector'.
            self.metadata_collector = self.file_import.metadata_collector

    def generate(self):
        """The main method. Collect details and write the yml file."""
        # Collect the wrapped functions with the details.
        self.collect_functions()
        # Make sure when they are ran, only collecting data will be preformed.
        self.metadata_collector.set_collect_data(True)
        # Run the functions and by that, collect the data.
        self.run_functions()
        # Write the yml file according to the collected details.
        self.write_yaml()
        # Make sure the functions are back to normal running state.
        self.metadata_collector.set_collect_data(False)

    def collect_functions(self):
        """Collect the wrapped functions from the python file."""
        for item in dir(self.file_import):
            new_function = getattr(self.file_import, item)
            # if it is a YMLMetadataCollector wrapper, add it to the list.
            if callable(new_function) and isinstance(new_function, FunctionType) and 'YMLMetadataCollector' in repr(new_function):
                print(f"item {item}")
                self.functions.append(new_function)

        print(f"functions found: {self.functions}")

    def run_functions(self):
        """Run the functions found."""
        print("running functions")
        for function in self.functions:
            print(f"function run: {function}")
            function()

    def write_yaml(self):
        """Write the yml file based on the collected details."""
        print("writing...")
        metadata = MetadataToDict(self.metadata_collector)
        metadata.build_integration_dict()
        print(f"metadata_dict: {metadata.metadata_dict}")

        yml_filename_splitted = self.filename.split('.')[:-1] + ['yml']
        yml_filename = ".".join(yml_filename_splitted)
        metadata.save_dict_as_yaml_integration_file(yml_filename)


class MetadataToDict:
    """Transform the YMLMetadataCollector into a dict and then a yml."""

    def __init__(self, metadata_collector: YMLMetadataCollector):
        self.mc = metadata_collector
        self.metadata_dict = {}

    def build_integration_dict(self):
        """
        Build the complete integration dictionary, suitable to be serialized into YAML.
        Does not include the script itself.
        """
        config_keys = [self.config_metadata_from_key(config_key) for config_key in self.mc.conf]
        commands = [self.command_metadata_from_function(command_name) for command_name in self.mc.command_names]
        integration_dict = {
            "category": self.mc.category,
            "description": self.mc.description,
            "commonfields": {
                "id": self.mc.integration_name,
                "version": -1
            },
            "name": self.mc.integration_name,
            "display": self.mc.integration_name.replace("_", " "),
            "configuration": config_keys,
            "script": {
                "commands": commands,
                "script": "-",
                "type": self.mc.integration_type,
                "subtype": self.mc.integration_subtype,
                "dockerimage": self.mc.docker_image,
                "feed": self.mc.is_feed,
                "isfetch": self.mc.is_fetch,
                "runonce": self.mc.is_runonce,
                "longRunning": self.mc.long_running,
                "longRunningPort": self.mc.long_running_port
            },
            "fromversion": self.mc.fromversion,
            "tests": self.mc.tests
        }

        if self.mc.detailed_description:
            integration_dict["detaileddescription"] = self.mc.detailed_description
        if self.mc.deprecated:
            integration_dict["deprecated"] = self.mc.deprecated
        if self.mc.system:
            integration_dict["system"] = self.mc.system
        if self.mc.timeout:
            integration_dict["timeout"] = self.mc.timeout

        self.metadata_dict = integration_dict

    @staticmethod
    def config_metadata_from_key(config_key: ConfKey):
        config_key_metadata = {
            "display": config_key.display,
            "name": config_key.name,
            "type": config_key.key_type,
            "required": config_key.required
        }
        if config_key.default_value:
            config_key_metadata["defaultvalue"] = config_key.default_value

        if config_key.additional_info:
            config_key_metadata["additionalinfo"] = config_key.additional_info

        return config_key_metadata

    def command_metadata_from_function(self, command_name: str) -> dict:
        func = self.mc.functions.get(command_name)
        command_outputs = self.mc.outputs.get(command_name)
        command_inputs = self.mc.inputs.get(command_name)

        """
        Converts a python function into an integration command dictionary.
        :param command_name: Name of the command in the integration
        :param func: Callable python function
        """
        docstring = parse(func.__doc__)  # type:ignore

        command = {
            "deprecated": False,
            "description": docstring.short_description,
            "name": command_name,
            "arguments": [],
            "outputs": []
        }
        if command_inputs:
            # Inputs dict overrides declarations
            command["arguments"] = self.organize_inputs(command_inputs)
        else:
            command["arguments"] = self.organize_inputs_from_declaration(func, self.mc.RESTORED_ARGS)

        command["outputs"] = self.organize_outputs(command_outputs)
        return command

    @staticmethod
    def organize_inputs(command_inputs):
        command_args = []
        for argument in command_inputs:
            command_args.append(MetadataToDict.add_arg_metadata(
                arg_name=argument.name,
                description=argument.description,
                default_value=argument.default if not inspect.Parameter.empty else None,
                is_array=argument.is_array,
                secret=argument.secret,
                options=argument.options,
                execution=argument.execution
            ))

        return command_args

    @staticmethod
    def organize_inputs_from_declaration(func, restored_args):
        annotations = func.__annotations__  # type:ignore
        print(f"anno {annotations}")
        args = inspect.signature(func).parameters
        docstring = parse(func.__doc__)

        docstring_params = {}
        for param in docstring.params:
            docstring_params[param.arg_name] = param.description
        print(f"docstring_params {docstring_params}")

        command_args = []
        for arg_name, param in args.items():
            if arg_name not in restored_args:
                description = docstring_params.get(arg_name, '')
                arg_type = param.annotation
                command_args.append(MetadataToDict.add_arg_metadata(
                    arg_name=arg_name,
                    description=description,
                    default_value=param.default if not inspect.Parameter.empty else None,
                    is_array=type(arg_type) is list or arg_type in [list, Union[list, dict]],
                    secret=True if 'secret' in description.lower() else False,
                    options=MetadataToDict.handle_enum(param.annotation) if param.annotation is EnumMeta else [],
                    execution=True if 'potentially harmful' in description.lower() else False
                ))

        return command_args

    @staticmethod
    def add_arg_metadata(arg_name, description, default_value, is_array=False, secret=False, options=[],
                         execution=False):
        arg_metadata = {
            "name": arg_name,
            "isArray": False,
            "description": arg_name,
            "required": False,
            "secret": False,
            "default": False
        }
        if description:
            arg_metadata["description"] = description
        if default_value:
            arg_metadata["required"] = False
            arg_metadata["defaultValue"] = default_value
        else:
            arg_metadata["required"] = True
        if is_array:
            arg_metadata["isArray"] = True
        if options:
            arg_metadata["predefined"] = options
            arg_metadata["auto"] = "PREDEFINED"
        if secret:
            arg_metadata["secret"] = True
        if execution:
            arg_metadata["execution"] = True

        return arg_metadata

    @staticmethod
    def handle_enum(enum_annotations):
        result = []
        for attribute in list(enum_annotations):
            result.append(attribute.value)
        return result

    @staticmethod
    def organize_outputs(command_outputs):
        prefix = command_outputs.get("outputs_prefix") if command_outputs else ''
        outputs_dict = command_outputs.get("outputs_dict") if command_outputs else {}
        outputs_dict = outputs_dict if outputs_dict else {}
        organized_outputs = []

        for output_key in outputs_dict.keys():
            if output_key:
                organized_outputs.append({
                    "contextPath": f"{prefix}.{output_key}",
                    "description": outputs_dict.get(output_key, (None, ''))[1],
                    "type": MetadataToDict.get_metadata_type(outputs_dict[output_key][0])
                })

        return organized_outputs

    @staticmethod
    def get_metadata_type(output_type):
        if output_type is str or output_type is AnyStr:
            return "String"
        if output_type is datetime.datetime or output_type is datetime.date:
            return "Date"
        if output_type is int or output_type is float:
            return "Number"
        if output_type is bool:
            return "Boolean"
        return "Unknown"

    @staticmethod
    def docstring_to_descriptions(obj_with_docs):
        docstring = parse(obj_with_docs.__doc__)
        docstring_params = {}
        for param in docstring.params:
            docstring_params[param.arg_name] = param.description

        return docstring_params

    def save_dict_as_yaml_integration_file(self, output_file: str):
        print(f"Saving generated integration to {output_file}")
        yaml.dump(self.metadata_dict, open(output_file, "w"))


# Example Usage of generating yml file. Will be positioned where unify is called.
yml_generator = YMLGenerator(filename='./example_integration.py')
yml_generator.generate()
