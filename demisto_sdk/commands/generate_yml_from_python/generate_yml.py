"""This file is a part of the generating yml design. Generating a yml file from a python file."""
import datetime
import importlib.util
import inspect
import os
import traceback
from enum import EnumMeta
from types import FunctionType
from typing import Any, AnyStr, Callable, List, Union

import click
import mock
import yaml
from docstring_parser import parse

from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
    CommandMetadata, ConfKey, InputArgument, YMLMetadataCollector)


class YMLGenerator:
    """The YMLGenerator class preforms the following:
        1. Obtain the relevant YMLMetadataCollector object from the specified python file.
        2. Make a list of the decorated functions from the specified python file.
        3. Use metadata_collector to collect the details from the relevant python file.
        4. Generate YML file based on the details collected.
    """

    def __init__(self, filename: str):
        self.functions = []
        self.filename = os.path.abspath(filename)
        self.metadata_collector = None
        self.file_import = None
        self.is_generatable_file = self.import_the_metadata_collector()
        self.metadata = None

    def import_the_metadata_collector(self):
        """Find the metadata_collector object in the python file and import it."""
        orig_import = __import__
        mock_obj = mock.MagicMock()

        def import_mock(name: str, *args):
            if name not in ['InputArgument', 'ConfTypesEnum', 'ConfKey', 'YMLMetadataCollector',
                            'demisto_sdk.commands.unify.yml_metadata_collector']:
                return mock_obj
            return orig_import(name, *args)

        with mock.patch('builtins.__import__', side_effect=import_mock):
            try:
                spec = importlib.util.spec_from_file_location("metadata_collector", self.filename)
                # The self.file_import object will be used later to identify wrapped functions.
                self.file_import = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(self.file_import)
                # Here we assume the details_collector object will be called 'metadata_collector'.
                self.metadata_collector = self.file_import.metadata_collector
                click.secho(f"Found the metadata collector in file {self.filename}")
                return True
            except Exception as err:
                click.secho(f"No metadata collector found in {self.filename}")
                if not str(err) == "module 'metadata_collector' has no attribute 'metadata_collector'":
                    click.secho(traceback.format_exc())
                    click.secho(str(err))
                return False

    def generate(self):
        """The main method. Collect details and write the yml file."""
        if not self.is_generatable_file:
            click.secho(f'Not running file {self.filename} without metadata collector.')
            return
        # Collect the wrapped functions with the details.
        self.collect_functions()
        # Make sure when they are ran, only collecting data will be preformed.
        self.metadata_collector.set_collect_data(True)
        # Run the functions and by that, collect the data.
        self.run_functions()
        # Write the yml file according to the collected details.
        self.extract_metadata()
        # Make sure the functions are back to normal running state.
        self.metadata_collector.set_collect_data(False)

    def collect_functions(self):
        """Collect the wrapped functions from the python file."""
        if self.is_generatable_file and not self.functions:
            for item in dir(self.file_import):
                new_function = getattr(self.file_import, item)
                # if it is a YMLMetadataCollector wrapper, add it to the list.
                if callable(new_function) and isinstance(new_function, FunctionType) and 'YMLMetadataCollector' in repr(new_function):
                    self.functions.append(new_function)

    def run_functions(self):
        """Run the functions found."""
        if self.is_generatable_file:
            for function in self.functions:
                function()

    def get_yml_filename(self):
        yml_filename_splitted = self.filename.split('.')[:-1] + ['yml']
        yml_filename = ".".join(yml_filename_splitted)
        return yml_filename

    def extract_metadata(self):
        """Collected details to MetadataToDict object."""
        if self.is_generatable_file:
            click.secho('Converting collected details to dict')
            self.metadata = MetadataToDict(self.metadata_collector)
            self.metadata.build_integration_dict()

    def save_to_yml_file(self):
        """Write the yml file based on the collected details."""
        yml_filename = self.get_yml_filename()
        self.metadata.save_dict_as_yaml_integration_file(yml_filename)

    def get_metadata_dict(self):
        return self.metadata.metadata_dict


class MetadataToDict:
    """Transform the YMLMetadataCollector into a dict and then a yml."""

    def __init__(self, metadata_collector: YMLMetadataCollector):
        self.mc = metadata_collector
        self.metadata_dict = {}

    def build_integration_dict(self):
        """Build the integration dictionary from the metadata_collector provided."""
        config_keys = [self.config_metadata_from_key(config_key) for config_key in self.mc.conf]
        commands = [self.command_metadata_from_function(command) for command in self.mc.commands]
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
        if self.mc.default_classifier:
            integration_dict["defaultclassifier"] = self.mc.default_classifier
        if self.mc.default_mapper_in:
            integration_dict["defaultmapperin"] = self.mc.default_mapper_in

        self.metadata_dict = integration_dict

    @staticmethod
    def config_metadata_from_key(config_key: ConfKey) -> dict:
        """Build YML configuration key metadata dictionary from a ConfKey object."""
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

        if config_key.options:
            config_key_metadata["options"] = config_key.options

        return config_key_metadata

    def command_metadata_from_function(self, command: CommandMetadata) -> dict:
        """Build YML command metadata dictionary for the command."""

        docstring = parse(command.function.__doc__)  # type:ignore

        command_dict = {
            "deprecated": False,
            "description": docstring.short_description,  # TODO: check this
            "name": command.name,
            "arguments": [],
            "outputs": []
        }
        if command.inputs:
            # Inputs dict overrides declarations
            command_dict["arguments"] = self.organize_inputs(command.inputs)
        else:
            command_dict["arguments"] = self.organize_inputs_from_declaration(command.function, self.mc.RESTORED_ARGS)

        if command.outputs:
            # Outputs dict overrides declarations
            command_dict["outputs"] = self.organize_outputs(command_outputs=command.outputs,
                                                            prefix=command.outputs_prefix,
                                                            multiple_prefixes=command.multiple_output_prefixes)
        else:
            prefix = command.outputs_prefix if command.outputs_prefix else self.mc.integration_name
            command_dict["outputs"] = self.organize_outputs_from_declaration(command.doc, prefix)

        if command.execution:
            command_dict["execution"] = command.execution

        return command_dict

    @staticmethod
    def organize_inputs(command_inputs: List[InputArgument]) -> List[dict]:
        """Convert a command's InputArgument objects to dicts."""
        command_args = []
        for argument in command_inputs:
            options = []
            if argument.options:
                options = argument.options
            elif argument.input_type:
                options = MetadataToDict.handle_enum(argument.options)

            command_args.append(MetadataToDict.add_arg_metadata(
                arg_name=argument.name,
                description=argument.description,
                default_value=argument.default if not inspect.Parameter.empty else None,
                is_array=argument.is_array,
                secret=argument.secret,
                options=options,
                execution=argument.execution
            ))

        return command_args

    @staticmethod
    def organize_inputs_from_declaration(func: Callable, restored_args: List[str]) -> List[dict]:
        """Take input arguments from commands' docstring and declaration and convert them to YML dicts. """
        args = inspect.signature(func).parameters
        docstring = parse(func.__doc__)

        command_args = []
        for param in docstring.params:
            if param.arg_name.lower() not in restored_args:
                description = param.description.strip()
                declared_arg = args.get(param.arg_name)
                arg_type = declared_arg.annotation if declared_arg else None  # TODO: else get it from () if docstring.
                default = declared_arg.default if not inspect.Parameter.empty else None
                options = []
                secret = False
                execution = False
                if arg_type is EnumMeta:
                    options = MetadataToDict.handle_enum(arg_type)
                elif 'options=[' in description.lower():
                    left_of_line_options = description.lower().split('options=[')[1]
                    options_str = left_of_line_options.split(']')[0]
                    options = options_str.split(',')  # TODO: remove options from description
                    options = [option.strip() for option in options]

                if declared_arg and not inspect.Parameter.empty:
                    default = declared_arg.default
                elif 'default=' in description:
                    left_of_line_default = description.lower().split('default=')[1]
                    default = left_of_line_default.split('.')[0]  # TODO: remove default from description
                if 'secret.' in description.lower():
                    secret = True
                    description = description.replace('secret.', '')
                if 'potentially harmful.' in description.lower():
                    execution = True
                    description = description.replace('potentially harmful.', '')

                command_args.append(MetadataToDict.add_arg_metadata(
                    arg_name=param.arg_name,
                    description=description,
                    default_value=default,
                    is_array=type(arg_type) is list or arg_type in [list, Union[list, dict]],
                    secret=secret,
                    options=options,
                    execution=execution
                ))

        return command_args

    @staticmethod
    def add_arg_metadata(arg_name: str, description: str, default_value: Any, is_array: bool = False,
                         secret: bool = False, options: list = [], execution: bool = False) -> dict:
        """Return a YML metadata dict of a command argument."""
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
    def handle_enum(enum_annotations: Any) -> list:
        """Convert enum arguments with predefined options to list for YML metadata."""
        result = []
        for attribute in list(enum_annotations):
            result.append(attribute.value)
        return result

    @staticmethod
    def organize_outputs(command_outputs: list, prefix: str, multiple_prefixes: bool = False,
                         file_output: bool = False) -> List[dict]:
        """Convert command outputs dict to YML metadata dict."""
        # prefix = command_outputs.get("outputs_prefix") if command_outputs else ''
        # outputs_dict = command_outputs.get("outputs_dict") if command_outputs else {}
        # outputs_dict = outputs_dict if outputs_dict else {}
        organized_outputs = []

        # TODO: make context path great. add multiple prefixes and no prefix options.
        if multiple_prefixes:
            # TODO: thread lightly
            pass

        for output_key in command_outputs:
            if output_key:
                organized_outputs.append({
                    "contextPath": f"{prefix}.{output_key.name}",
                    "description": output_key.description,
                    "type": MetadataToDict.get_metadata_type(output_key.output_type)
                })

        if file_output:
            # TODO: append all context outputs of file
            pass

        return organized_outputs

    @staticmethod
    def organize_outputs_from_declaration(doc_str: str, prefix: str) -> List[dict]:
        """Convert docstring outputs to YML command outputs metadata dict. Assume Google Docs style."""
        organized_outputs = []
        doc_dict = MetadataToDict.docstring_ident_to_dict(doc_str)
        output_type = 'dict'

        for output_line in doc_dict.get('Context Outputs:', []):
            outputs_key_details, description = output_line.split(':', 1)
            output_key = outputs_key_details.split('(')[0]
            if len(outputs_key_details.split('(')) == 2:
                type_str = outputs_key_details.split('(')[1]
                output_type = type_str.split(')')[0]
            if output_key:
                organized_outputs.append({
                    "contextPath": f"{prefix}.{output_key.strip()}",
                    "description": description.strip(),
                    "type": MetadataToDict.get_metadata_type(eval(output_type.lower()))
                })

        return organized_outputs

    @staticmethod
    def docstring_ident_to_dict(docstring: str) -> dict:
        """Parse docstring's main parts by indentation."""
        docstring_list = docstring.split('\n')
        header_leading_spaces = 0
        docstring_dict = {}
        headers = []

        for line in docstring_list:
            leading_spaces = len(line) - len(line.lstrip())
            if header_leading_spaces == 0:
                header_leading_spaces = leading_spaces
            if header_leading_spaces > 0 and leading_spaces == header_leading_spaces:
                headers.append(line.lstrip())

        last_header = ''
        for line in docstring_list:
            if line.lstrip() in headers and line.lstrip() != last_header:
                last_header = line.lstrip()
                docstring_dict[last_header] = []
            elif last_header != '':
                docstring_dict[last_header].append(line.lstrip())

        docstring_dict.pop('')
        return docstring_dict

    @staticmethod
    def get_metadata_type(output_type: Any) -> str:
        """Get metadata output type from python type."""
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
    def docstring_to_descriptions(obj_with_docs: Any) -> dict:
        """Parse docstring of provided obj_with_docs and return parameters' descriptions."""
        docstring = parse(obj_with_docs.__doc__)
        docstring_params = {}
        for param in docstring.params:
            docstring_params[param.arg_name] = param.description

        return docstring_params

    def save_dict_as_yaml_integration_file(self, output_file: str):
        """Save the dict to an output file."""
        click.secho(f"Writing collected metadata to {output_file}.")
        yaml.dump(self.metadata_dict, open(output_file, "w"))
