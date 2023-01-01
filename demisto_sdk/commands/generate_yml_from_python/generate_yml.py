"""This file is a part of the generating yml design. Generating a yml file from a python file."""
import datetime
import importlib.util
import inspect
import os
import re
import traceback
from enum import Enum, EnumMeta
from types import FunctionType
from typing import Any, AnyStr, Callable, List, Optional, Tuple, Union
from unittest import mock

import click

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.tools import write_yml
from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
    CommandMetadata,
    ConfKey,
    InputArgument,
    OutputArgument,
    YMLMetadataCollector,
)

yaml = YAML_Handler()


class YMLGenerator:
    """The YMLGenerator class performs the following:
    1. Obtain the relevant YMLMetadataCollector object from the specified python file.
    2. Make a list of the decorated functions from the specified python file.
    3. Use metadata_collector to collect the details from the relevant python file.
    4. Generate YML file based on the details collected.
    """

    IMPORT_COLLECTOR_LINE = (
        "from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import ("
        "CommandMetadata, ConfKey, InputArgument, YMLMetadataCollector, "
        "OutputArgument, ParameterTypes)"
    )
    EXPLICIT_DECLARATION_IMPORTS_LINE = (
        "from CommonServerPython import BaseClient, CommandResults, datetime"
    )

    def __init__(self, filename: str, verbose: bool = False, force: bool = False):
        self.functions: list = []
        self.filename = os.path.abspath(filename)
        self.metadata_collector: Optional[YMLMetadataCollector] = None
        self.file_import: Optional[Any] = None
        self.metadata: Optional[MetadataToDict] = None
        self.verbose = verbose
        self.force = force
        self.is_generatable_file: bool = self.import_the_metadata_collector()

    def import_the_metadata_collector(self):
        """Find the metadata_collector object in the python file and import it."""
        orig_import = __import__
        mock_obj = mock.MagicMock()

        def import_mock(name: str, *args, **kwargs):
            if name not in {
                "InputArgument",
                "ConfKey",
                "ParameterType",
                "YMLMetadataCollector",
                "demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector",
                "datetime",
                "enum",
                "ParameterTypes",
            }:
                return mock_obj
            return orig_import(name, *args, **kwargs)

        self.add_collector_imports()

        with mock.patch("builtins.__import__", side_effect=import_mock):
            try:
                spec = importlib.util.spec_from_file_location(
                    "metadata_collector", self.filename
                )
                # The self.file_import object will be used later to identify wrapped functions.
                if spec:
                    self.file_import = importlib.util.module_from_spec(spec)
                    if self.file_import:
                        spec.loader.exec_module(self.file_import)  # type: ignore[union-attr]
                        # Here we assume the details_collector object will be called 'metadata_collector'.
                        self.metadata_collector = self.file_import.metadata_collector
                        if self.verbose:
                            click.secho(
                                f"Found the metadata collector in file {self.filename}"
                            )
                        return True
                else:
                    click.secho(f"Problem importing {self.filename}", fg="red")
                    return False
            except Exception as err:
                click.secho(f"No metadata collector found in {self.filename}", fg="red")
                if (
                    not str(err)
                    == "module 'metadata_collector' has no attribute 'metadata_collector'"
                ):
                    click.secho(traceback.format_exc())
                    click.secho(str(err), fg="red")
                return False

    def generate(self):
        """The main method. Collect details and write the yml file."""
        click.secho("Starting yml generation..")
        if not self.is_generatable_file:
            click.secho(
                f"Not running file {self.filename} without metadata collector.",
                fg="red",
            )
            return
        # Collect the wrapped functions with the details.
        self.collect_functions()
        previous_verbose_setting = False
        # Make sure when they are ran, only collecting data will be performed.
        if self.metadata_collector:
            self.metadata_collector.set_collect_data(True)
            previous_verbose_setting = self.metadata_collector.verbose
            self.metadata_collector.set_verbose(self.verbose)
        # Run the functions and by that, collect the data.
        self.run_functions()
        # Write the yml file according to the collected details.
        self.extract_metadata()
        # Make sure the functions are back to normal running state.
        if self.metadata_collector:
            self.metadata_collector.set_collect_data(False)
            self.metadata_collector.set_verbose(previous_verbose_setting)
        # Remove imports from file
        self.remove_collector_imports()

    def add_collector_imports(self):
        """Add collector imports to provided file."""
        with open(self.filename, "r+") as code_file:
            content = code_file.read()
            if not content.startswith(self.IMPORT_COLLECTOR_LINE):
                if self.verbose:
                    click.secho(
                        "Adding import lines, please do not remove while generating yml."
                    )
                code_file.seek(0, 0)
                code_file.write(
                    f"{self.IMPORT_COLLECTOR_LINE}\n{self.EXPLICIT_DECLARATION_IMPORTS_LINE}\n\n{content}"
                )

    def remove_collector_imports(self):
        """Remove collector imports from provided file."""
        with open(self.filename, "r+") as code_file:
            content = code_file.read()
            # Delete file content so the file won't be a mess
            code_file.seek(0)
            code_file.truncate()
            # clean_content will store the content without the import lines.
            clean_content = content
            collector_import_lines = f"{self.IMPORT_COLLECTOR_LINE}\n{self.EXPLICIT_DECLARATION_IMPORTS_LINE}\n\n"
            if content.startswith(collector_import_lines):
                if self.verbose:
                    click.secho("Removing added import lines.")
                # Split the content to the parts before and after the collector_import_lines
                content_parts = content.split(collector_import_lines)
                # Restore content to previous form and ignore the first found import lines.
                clean_content = f"{collector_import_lines}".join(content_parts[1:])

            code_file.write(clean_content)

    def collect_functions(self):
        """Collect the wrapped functions from the python file."""
        if not self.functions:
            for item in dir(self.file_import):
                new_function = getattr(self.file_import, item)
                # if it is a YMLMetadataCollector wrapper, add it to the list.
                if (
                    callable(new_function)
                    and isinstance(new_function, FunctionType)
                    and "YMLMetadataCollector" in repr(new_function)
                ):
                    self.functions.append(new_function)

    def run_functions(self):
        """Run the functions found."""
        for function in self.functions:
            try:
                function()
            except Exception as err:
                click.secho(
                    f"Failed running and collecting data for function: {function.__name__}",
                    fg="red",
                )
                click.secho(traceback.format_exc())
                click.secho(str(err), fg="red")
                click.secho("Continuing..")

    def get_yml_filename(self) -> str:
        yml_filename_splitted = self.filename.split(".")[:-1] + ["yml"]
        yml_filename = ".".join(yml_filename_splitted)
        return yml_filename

    def extract_metadata(self):
        """Collected details to MetadataToDict object."""
        if self.is_generatable_file:
            if self.verbose:
                click.secho("Converting collected details to dict..")
            if self.metadata_collector:
                self.metadata = MetadataToDict(
                    metadata_collector=self.metadata_collector,
                    verbose=self.verbose,
                    file_import=self.file_import,
                )
                self.metadata.build_integration_dict()

    def save_to_yml_file(self):
        """Write the yml file based on the collected details."""
        yml_filename = self.get_yml_filename()

        if os.path.exists(yml_filename) and not self.force:
            click.secho(
                f"File {yml_filename} already exists, not writing. To override add --force.",
                fg="red",
            )
        else:
            if self.force:
                click.secho(
                    f"Force flag is used. Overriding {yml_filename} if it exists.",
                    fg="yellow",
                )
            if self.metadata:
                self.metadata.save_dict_as_yaml_integration_file(yml_filename)

    def get_metadata_dict(self) -> Optional[dict]:
        if self.metadata:
            return self.metadata.metadata_dict
        return None


class MetadataToDict:
    """Transform the YMLMetadataCollector into a dict and then a yml."""

    def __init__(
        self,
        metadata_collector: YMLMetadataCollector,
        verbose: bool = False,
        file_import: Optional[Any] = None,
    ):
        self.mc = metadata_collector
        self.metadata_dict: dict = {}
        self.verbose = verbose
        self.file_import = file_import

    def build_integration_dict(self):
        """Build the integration dictionary from the metadata_collector provided."""
        config_keys = [
            self.config_metadata_from_key(config_key) for config_key in self.mc.conf
        ]
        commands = [
            self.command_metadata_from_function(command) for command in self.mc.commands
        ]
        integration_dict: dict = {
            "category": self.mc.category,
            "description": self.mc.description,
            "commonfields": {"id": self.mc.integration_name, "version": -1},
            "name": self.mc.integration_name,
            "display": self.mc.display
            if self.mc.display
            else self.mc.integration_name.replace("_", " "),
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
                "longRunningPort": self.mc.long_running_port,
            },
            "fromversion": self.mc.fromversion,
            "tests": self.mc.tests,
        }

        if self.mc.detailed_description:
            integration_dict.update(
                {"detaileddescription": self.mc.detailed_description}
            )
        if self.mc.deprecated is not None:
            integration_dict["deprecated"] = self.mc.deprecated
        if self.mc.system is not None:
            integration_dict["system"] = self.mc.system
        if self.mc.timeout:
            integration_dict["timeout"] = self.mc.timeout
        if self.mc.default_classifier:
            integration_dict["defaultclassifier"] = self.mc.default_classifier
        if self.mc.default_mapper_in:
            integration_dict["defaultmapperin"] = self.mc.default_mapper_in
        if self.mc.integration_name_x2:
            integration_dict["commonfields"]["name_x2"] = self.mc.integration_name_x2
        if self.mc.default_enabled is not None:
            integration_dict["defaultEnabled"] = self.mc.default_enabled
        if self.mc.default_enabled_x2 is not None:
            integration_dict["defaultEnabled_x2"] = self.mc.default_enabled_x2
        if self.mc.image:
            integration_dict["image"] = self.mc.image

        self.metadata_dict = integration_dict

    @staticmethod
    def config_metadata_from_key(config_key: ConfKey) -> dict:
        """Build YML configuration key metadata dictionary from a ConfKey object."""
        config_key_metadata = {
            "display": config_key.display,
            "name": config_key.name,
            "type": config_key.key_type,
            "required": config_key.required,
        }
        if config_key.default_value:
            config_key_metadata["defaultvalue"] = config_key.default_value

        if config_key.additional_info:
            config_key_metadata["additionalinfo"] = config_key.additional_info

        if config_key.options:
            config_key_metadata["options"] = config_key.options

        if config_key.input_type:
            config_key_metadata["options"] = MetadataToDict.handle_enum(
                config_key.input_type
            )

        return config_key_metadata

    def command_metadata_from_function(self, command: CommandMetadata) -> dict:
        """Build YML command metadata dictionary for the command."""
        if self.verbose:
            click.secho(f"Parsing metadata for command {command.name}...")

        description, in_args, out_args = self.google_docstring_to_dict(
            command.function.__doc__, self.verbose, self.file_import
        )

        command_dict: dict = {
            "deprecated": command.deprecated,
            "description": command.description if command.description else description,
            "name": command.name,
            "arguments": [],
            "outputs": [],
        }

        if command.inputs:
            # Inputs dict overrides declarations
            command_dict["arguments"] = self.organize_inputs(command.inputs)
        else:
            command_dict["arguments"] = self.organize_inputs_from_declaration(
                command.function, in_args, self.mc.RESTORED_ARGS
            )

        prefix = (
            command.outputs_prefix
            if command.outputs_prefix
            else self.mc.integration_name
        )
        if command.outputs:
            # Outputs dict overrides declarations
            command_dict["outputs"] = self.organize_outputs(
                command_outputs=command.outputs,
                prefix=prefix,
                multiple_prefixes=command.multiple_output_prefixes,
                file_output=command.file_output,
            )
        else:
            command_dict["outputs"] = self.organize_outputs(
                command_outputs=out_args,
                prefix=prefix,
                multiple_prefixes=command.multiple_output_prefixes,
                file_output=command.file_output,
            )

        if command.execution is not None:
            command_dict["execution"] = command.execution

        if self.verbose:
            click.secho(f"Completed parsing metadata for command {command.name}.")

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
                options = MetadataToDict.handle_enum(argument.input_type)

            command_args.append(
                MetadataToDict.add_arg_metadata(
                    arg_name=argument.name,
                    description=argument.description if argument.description else "",
                    default_value=argument.default if argument.default else None,
                    is_array=argument.is_array,
                    secret=argument.secret,
                    options=options,
                    execution=argument.execution,
                    required=argument.required,
                )
            )

        return command_args

    @staticmethod
    def organize_inputs_from_declaration(
        func: Callable,
        in_args: List[Tuple[InputArgument, Any]],
        restored_args: List[str],
    ) -> List[dict]:
        """Take input arguments from commands' docstring and declaration and convert them to YML dicts."""
        args = inspect.signature(func).parameters
        command_args = []
        for in_arg in in_args:
            input_arg = in_arg[0]
            arg_type_from_doc = in_arg[1]
            if input_arg.name.lower() not in restored_args:
                description = input_arg.description
                declared_arg = args.get(input_arg.name)
                arg_type = (
                    declared_arg.annotation if declared_arg else arg_type_from_doc
                )
                default = (
                    declared_arg.default
                    if declared_arg and declared_arg.default != inspect.Parameter.empty
                    else None
                )
                options = []
                secret = False
                execution = False
                required = False
                if (
                    arg_type
                    and inspect.isclass(arg_type)
                    and issubclass(arg_type, Enum)
                    or arg_type is EnumMeta
                ):
                    options = MetadataToDict.handle_enum(arg_type)
                elif description and "options=[" in description:
                    split_line = description.split("options=[")
                    right_of_line_options = split_line[1]
                    options_str = right_of_line_options.split("].")[0]
                    options = options_str.split(",")
                    options = [option.strip() for option in options]
                    description = f"{split_line[0]}{right_of_line_options.split('].')[1].lstrip()}"
                if declared_arg and not inspect.Parameter.empty:
                    default = declared_arg.default
                elif description and "default=" in description:
                    left_of_line_default = description.split("default=")[1]
                    default = left_of_line_default.split(".")[0]
                    after_default = ".".join(left_of_line_default.split(".")[1:])
                    description = f"{description.split('default=')[0].strip()}{after_default.strip()}"
                if description and "secret." in description:
                    secret = True
                    description = description.replace(" secret.", "")
                    description = description.replace("secret.", "")
                if description and "potentially harmful." in description:
                    execution = True
                    description = description.replace(" potentially harmful.", "")
                    description = description.replace("potentially harmful.", "")
                if description and "required." in description:
                    required = True
                    description = description.replace(" required.", "")
                    description = description.replace("required.", "")
                if description and "execution." in description:
                    execution = True
                    description = description.replace(" execution.", "")
                    description = description.replace("execution.", "")

                command_args.append(
                    MetadataToDict.add_arg_metadata(
                        arg_name=input_arg.name,
                        description=description.strip() if description else "",
                        default_value=default,
                        is_array=type(arg_type) is list
                        or arg_type in [list, Union[list, dict]],
                        secret=secret,
                        options=options,
                        execution=execution,
                        required=required,
                    )
                )

        return command_args

    @staticmethod
    def add_arg_metadata(
        arg_name: str,
        description: str,
        default_value: Any,
        is_array: bool = False,
        secret: bool = False,
        options: list = [],
        execution: bool = False,
        required: bool = False,
    ) -> dict:
        """Return a YML metadata dict of a command argument."""
        arg_metadata = {
            "name": arg_name,
            "isArray": False,
            "description": arg_name,
            "required": required,
            "secret": False,
            "default": True if default_value else False,
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
    def organize_outputs(
        command_outputs: list,
        prefix: str,
        multiple_prefixes: bool = False,
        file_output: bool = False,
    ) -> List[dict]:
        """Convert command outputs dict to YML metadata dict."""
        organized_outputs = []
        if file_output:
            command_outputs = command_outputs + [
                OutputArgument(
                    name="EntryID",
                    prefix="InfoFile",
                    output_type=dict,
                    description="The EntryID of the report file.",
                ),
                OutputArgument(
                    name="Extension",
                    prefix="InfoFile",
                    output_type=str,
                    description="The extension of the report file.",
                ),
                OutputArgument(
                    name="Name",
                    prefix="InfoFile",
                    output_type=str,
                    description="The name of the report file.",
                ),
                OutputArgument(
                    name="Info",
                    prefix="InfoFile",
                    output_type=str,
                    description="The info of the report file.",
                ),
                OutputArgument(
                    name="Size",
                    prefix="InfoFile",
                    output_type=int,
                    description="The size of the report file.",
                ),
                OutputArgument(
                    name="Type",
                    prefix="InfoFile",
                    output_type=str,
                    description="The type of the report file.",
                ),
            ]
        for output_key in command_outputs:
            context_path = output_key.name
            if prefix:
                context_path = f"{prefix}.{output_key.name}"
            if multiple_prefixes:
                if output_key.prefix:
                    context_path = f"{output_key.prefix}.{output_key.name}"
                elif "." in output_key.name:
                    context_path = output_key.name

            if output_key:
                organized_outputs.append(
                    {
                        "contextPath": context_path,
                        "description": output_key.description,
                        "type": MetadataToDict.get_metadata_type(
                            output_key.output_type
                        ),
                    }
                )

        return organized_outputs

    @staticmethod
    def google_docstring_to_dict(
        docstring: Optional[str],
        verbose: bool = False,
        file_import: Optional[Any] = None,
    ) -> Tuple[str, list, list]:
        """Parse google style docstring."""

        if not docstring:
            return "", [], []

        regex_sections = r"^(?: {4}|\t)(?P<name>\*{0,4}\w+|\w+\s\w+):\n(?P<desc>(?:(\s|\S)*?(\n\n|\Z)))"
        regex_titles = r"^(?: {4}|\t)(?P<name>\*{0,4}\w+|\w+\s\w+):"
        section_titles = re.findall(regex_titles, docstring, re.MULTILINE)
        regex_description_sections = r"(?P<desc>\A(\s|\S)*?)(\n\n|\Z)"
        descrition_sections = re.findall(
            regex_description_sections, docstring, re.MULTILINE
        )
        description = descrition_sections[0][0] if descrition_sections else ""
        sections = re.findall(regex_sections, docstring, re.MULTILINE)
        if not sections and not description:
            description = docstring
        input_list = []
        output_list = []
        if "Args" in section_titles or "Context Outputs" in section_titles:
            for section in sections:
                if "Args" in section:
                    lines = section[1].split("\n")
                    # get first indent number
                    spaces_num = len(lines[0]) - len(lines[0].lstrip())
                    arg_lines = section[1].split(f'\n{spaces_num*" "}')
                    for arg_line in arg_lines:
                        in_arg, in_arg_type = MetadataToDict.parse_in_argument_lines(
                            arg_line, verbose, file_import
                        )
                        if in_arg:
                            input_list.append((in_arg, in_arg_type))

                if "Context Outputs" in section:
                    lines = section[1].split("\n")
                    spaces_num = len(lines[0]) - len(lines[0].lstrip())
                    out_lines = section[1].split(f'\n{spaces_num*" "}')
                    for out_line in out_lines:
                        out_arg = MetadataToDict.parse_out_argument_lines(
                            out_line, verbose
                        )
                        if out_arg:
                            output_list.append(out_arg)

        return description, input_list, output_list

    @staticmethod
    def parse_in_argument_lines(
        argument_line: str, verbose: bool = False, file_import: Optional[Any] = None
    ) -> Tuple[Optional[InputArgument], Any]:
        """Parse input argument line from docstring."""
        regex_args_with_type = r"^(?: *|\t)(?P<name>\*{0,4}(\w+|\w+\s|\w+\.\w+\s)\((?P<type>.*)\)):(?P<desc>(\s|\S)*)"
        argument_sections = re.findall(
            regex_args_with_type, argument_line, re.MULTILINE
        )
        if len(argument_sections) < 1:
            regex_args_no_type = r"^(?: *|\t)(?P<name>)(\w+|\w+\s|\w+\.\w+\s|\w+\.\w+):(?P<desc>(\s|\S)*)"
            argument_sections = re.findall(
                regex_args_no_type, argument_line, re.MULTILINE
            )
            if len(argument_sections) < 1:
                return None, None
            else:
                name = argument_sections[0][1].strip()
                description = argument_sections[0][2].strip()
                return InputArgument(name=name, description=description), None
        else:
            name = argument_sections[0][1].strip()
            description = argument_sections[0][3].strip()
            input_type_str = argument_sections[0][2]
            try:
                if file_import and input_type_str in dir(file_import):
                    input_type = file_import.__getattribute__(input_type_str)
                else:
                    input_type = eval(input_type_str)
            except Exception as err:
                if verbose:
                    click.secho(
                        f"Problems parsing input type {input_type_str}, setting isArray=False."
                        f"Error was: {err}",
                        fg="yellow",
                    )
                input_type = None

            return InputArgument(name=name, description=description), input_type

    @staticmethod
    def parse_out_argument_lines(
        argument_line: str, verbose: bool = False
    ) -> Optional[OutputArgument]:
        """Parse output argument line from docstring."""
        regex_arguments = r"^(?: *|\t)(?P<name>\*{0,4}(\w+|\w+\s|\w+\.\w+\s)\((?P<type>.*)\)):(?P<desc>(\s|\S)*)"
        argument_sections = re.findall(regex_arguments, argument_line, re.MULTILINE)
        if len(argument_sections) < 1:
            return None
        if len(argument_sections[0]) < 4:
            return None
        name = argument_sections[0][1].strip()
        output_type_str = argument_sections[0][2]
        try:
            out_type = eval(output_type_str.lower())
        except Exception:
            if verbose:
                click.secho(
                    f"Problems parsing output type {output_type_str}, setting as Unknown.",
                    fg="yellow",
                )
            out_type = dict

        description = argument_sections[0][3].strip()
        return OutputArgument(name=name, output_type=out_type, description=description)

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

    def save_dict_as_yaml_integration_file(self, output_file: str):
        """Save the dict to an output file."""
        if self.verbose:
            click.secho(f"Writing collected metadata to {output_file}.")

        write_yml(output_file, self.metadata_dict)
        click.secho("Finished successfully.", fg="green")
