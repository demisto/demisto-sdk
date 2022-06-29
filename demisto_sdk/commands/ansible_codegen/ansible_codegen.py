import json
import os
import re
import shutil
import sys
from typing import Dict, List, Optional

import autopep8
import yaml

from demisto_sdk.commands.ansible_codegen.resources.integration_template_code import (
    command_code, integration_code_footer, integration_code_header,
    no_test_command_code, test_command_code)
from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.docker_util import ContainerRunner
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (print_error, print_warning,
                                               to_kebab_case, to_pascal_case)
from demisto_sdk.commands.generate_integration.XSOARIntegration import \
    XSOARIntegration

ILLEGAL_CODE_NAMES = ['type', 'from', 'id', 'filter', 'list']
NAME_FIX = '_'
REQUIRED_KEYS = ['name', 'display', 'category', 'description', 'host_type', 'ansible_modules']
OPTIONAL_KEYS = ['test_command', 'command_prefix', 'ignored_args', 'parameters', 'creds_mapping']
HOST_TYPES = ['ssh', 'winrm', 'nxos', 'ios', 'local']
REMOTE_HOST_TYPES = ['ssh', 'winrm', 'nxos', 'ios']
# The URL of the online module documentation
ANSIBLE_ONLINE_DOCS_URL_BASE = 'https://docs.ansible.com/ansible/latest/collections/'


class AnsibleIntegration:
    """
    Create a XSOAR Integration based on Ansible modules
    """

    def __init__(self, base_name: str, verbose: bool = False, config_file_path: str = None,
                 container_image: str = None, output_dir: str = ".", fix_code: bool = False):
        """
        base_name:         The name to use for the Integration files.
        verbose:           Increase logging detail
        config_file_path:  Location of the ansible_codegen yaml config. The details of the integration to be generated are stored here.
        container_image:   The container image to run the integration. This image should have ansible-runner and ansible installed as a bare minimum.
        output_dir:        Directory to output the generated integration
        fix_code:          To autopep8 or not the generated code
        """
        self.config_file_path = config_file_path
        self.base_path = output_dir
        self.base_name = base_name
        self.name = ''
        self.display = ''
        self.category = ''
        self.description = ''
        self.creds_mapping = None
        self.host_type = 'local'
        self.test_command = None
        self.command_prefix: Optional[str] = None
        self.ansible_modules: List[str] = []
        self.ignored_args: Optional[List[str]] = None
        self.ansible_docs: Dict = {}
        self.commands: List = []
        self.example_commands: List = []
        self.parameters: List = []
        self.verbose = verbose
        self.container_image = container_image
        self.fix_code = fix_code

    def load_config(self):
        """
        Loads the ansible codgen config
        """

        if self.config_file_path:
            try:
                with open(self.config_file_path, 'r') as config_file:
                    codegen_configuration = yaml.load(config_file, Loader=yaml.Loader)

                    if codegen_configuration is None:
                        print_error('Configuration file is empty')
                        sys.exit(1)

                    # Check for any config options not in defintion
                    valid_keys = REQUIRED_KEYS + OPTIONAL_KEYS

                    invalid_key_message = "Unused keys found in config yaml:"
                    invalid_keys = False
                    for key, value in codegen_configuration.items():
                        if key not in valid_keys:
                            invalid_key_message += f"\n  * {key}"
                            invalid_keys = True

                    if invalid_keys:
                        print_warning(invalid_key_message)

                    self.name = str(codegen_configuration.get('name'))
                    self.host_type = str(codegen_configuration.get('host_type'))
                    self.display = str(codegen_configuration.get('display'))
                    self.category = str(codegen_configuration.get('category'))
                    self.description = str(codegen_configuration.get('description'))
                    self.test_command = codegen_configuration.get('test_command')
                    self.command_prefix = codegen_configuration.get('command_prefix')
                    self.ansible_modules = list(codegen_configuration.get('ansible_modules', []))
                    self.ignored_args = codegen_configuration.get('ignored_args')
                    self.parameters = codegen_configuration.get('parameters', [])
                    self.creds_mapping = codegen_configuration.get('creds_mapping')
            except Exception as e:
                print_error(f'Failed to load configuration file: {e}')

        # Add concurrency tunable relating to non-local based targets
        if self.host_type != 'local':
            display = "Concurrency Factor"
            name = "concurrency"
            type = 0
            required = True
            defaultvalue = "4"
            additionalinfo = "If multiple hosts are specified in a command, how many hosts should be interacted with concurrently."

            concurrency_factor = XSOARIntegration.Configuration(name=name, display=display,
                                                                type_=type, required=required, defaultvalue=defaultvalue, additionalinfo=additionalinfo)
            self.parameters.append(concurrency_factor)

        # Set a command_prefix if not already provided
        if self.command_prefix is None and self.name:
            # If the config `name` is a single word then trust the caps
            self.command_prefix = self.name.lower() if len(self.name.split(' ')) == 1 else to_kebab_case(self.name)

    def fetch_ansible_docs(self):
        """
        Fetches the ansible documentation for the modules specified from the container image.
        Requires docker to function
        """
        if self.container_image is None:
            exit("Need a container Image to be specified")

        # Lookup ansible module docs from container
        self.print_with_verbose('Creating container for module documentation lookup...')
        lookup_container = ContainerRunner(
            image=self.container_image,
            container_name="demisto-sdk-ansiblecodegen-lookup")

        # Make sure ansible-docs is present in container
        ansibledoc_version = str(lookup_container.exec(command="ansible-doc --version").get("Outputs"))
        if "ansible-doc 2." not in ansibledoc_version:    # Tested with ansible-doc 2.12.1
            print_error(
                f'ansible-doc 2.x not found in container or not compatible version. Is Ansible installed in container image?\n\
                ansible-docs reports: {ansibledoc_version}')
            sys.exit(1)

        for module in self.ansible_modules:
            ansibledoc_lookup = lookup_container.exec(command=f"ansible-doc -t module -j \"{module}\"").get("Outputs")
            # Unfortunately we can't rely on the status code and need to parse the text output :(

            # Check for ansible-doc error text
            if f"module {module} not found" in str(ansibledoc_lookup):
                print_error(f'Module {module} not found in container')
                sys.exit(1)

            try:
                self.ansible_docs.update(json.loads(ansibledoc_lookup))  # type: ignore[arg-type]
            except Exception as e:
                print_error(f'Failed to load the ansible-docs for module {module}: {e}')
                sys.exit(1)

        self.print_with_verbose('Removing container used for module documentation lookup...')
        lookup_container.remove_container

    def validate(self) -> tuple:
        """
        Validates the codegen configuration.
        """

        validation = True
        validation_message = ""

        # Check that all required config options set
        for required_key in REQUIRED_KEYS:
            if getattr(self, required_key, False) is False:
                validation = False
                validation_message += f"\n  * Missing required key config: {required_key}"

        # Check config options with fixed possible values are valid

        if self.host_type not in HOST_TYPES:
            validation = False
            validation_message += f"\n  * Invalid option for host_type: {self.host_type}"

        # Check if XSOAR config parameters provided are valid
        if self.parameters:

            self.print_with_verbose('Creating partial integration yaml file for config validation...')
            yaml_file = self.save_yaml(self.base_path, skip_commands=True)

            structure_validator = StructureValidator(yaml_file, predefined_scheme=FileType.INTEGRATION)
            integration_validator = IntegrationValidator(structure_validator)

            # Schema Validation
            schema_check = structure_validator.is_valid_scheme()
            if not schema_check:
                validation = False
                validation_message += "\n  * Failed Schema validation"

            # Validation tests
            param_valid = integration_validator.is_valid_ansible_integration()

            if not param_valid:
                validation = False
                validation_message += "\n  * Failed core integration validation"

        return(validation, validation_message)

    def generate_python_code(self) -> str:
        """
        Generate python code with the commands from the integration configuration file.

        Returns:
            code: The integration python code.
        """

        code = integration_code_header.format(host_type=self.host_type, creds_mapping=self.creds_mapping)

        if self.test_command:
            code += test_command_code.format(self.name.lower(), self.test_command)
        else:
            code += no_test_command_code

        self.print_with_verbose('Adding Ansible modules to the Python code.')
        for ansible_module in self.ansible_modules:

            demisto_command = ""

            # In case ansible module has been provided in collection namespace form. We want just the module name
            ansible_module = ansible_module.split(".")[-1]

            if not to_kebab_case(ansible_module).startswith(f"{self.command_prefix}-"):
                demisto_command = f"{self.command_prefix}-{to_kebab_case(ansible_module)}"
            else:
                demisto_command = to_kebab_case(ansible_module)

            code += command_code.format(
                demisto_command, self.name.lower(), ansible_module)

        code += integration_code_footer

        self.print_with_verbose('Finished generating the Python code.')

        if self.fix_code:
            self.print_with_verbose('Fixing the code with autopep8...')
            code = autopep8.fix_code(code)

        return code

    def save_python_code(self, directory: str) -> str:
        """
        Writes the python code to a file.
        Args:
            directory: The directory to save the file to.

        Returns:
            python_file: The path to the python file.
        """
        self.print_with_verbose('Creating python file...')
        python_file = os.path.join(directory, f'{self.base_name}.py')
        try:
            with open(python_file, 'w') as fp:
                fp.write(self.generate_python_code())
                return python_file
        except Exception as err:
            print_error(f'Error writing {python_file} - {err}')
            raise

    def generate_yaml(self, skip_commands: bool = False) -> XSOARIntegration:
        """
        Generate integration yaml file based on configuration file, and Ansible module documentation.
        Args:
            skip_commands: If the generated integration yaml should skip generating the commands.

        Returns:
            integration: An object representation of the integration yaml structure.
        """
        self.print_with_verbose('Generating integration yaml...')

        commands = []
        if skip_commands is False:
            commands = self.get_yaml_commands()

        commonfields = XSOARIntegration.CommonFields(self.name)

        int_script = XSOARIntegration.Script('', "python", "python3", self.container_image, False, commands)

        integration = XSOARIntegration(commonfields, self.name, self.display, self.category, self.description, configuration=self.parameters,
                                       script=int_script)

        return integration

    def save_yaml(self, directory: str, skip_commands: bool = False) -> str:
        """
        Writes the yaml to a file.
        Args:
            directory: The directory to save the file to.
            skip_commands: Skip generating commands

        Returns:
            yaml_file: The path to the yaml file.
        """
        self.print_with_verbose('Creating yaml file...')
        yaml_file = os.path.join(directory, f'{self.base_name}.yml')
        try:
            with open(yaml_file, 'w') as fp:
                fp.write(yaml.dump(self.generate_yaml(skip_commands=skip_commands).to_dict()))
            return yaml_file
        except Exception as err:
            print_error(f'Error writing {yaml_file} - {err}')
            raise

    def save_empty_config(self, directory: str) -> str:
        """
        Writes a example integration configuration to a file in YAML format.
        Args:
            directory: The directory to save the file to.

        Returns:
            config_file: The path to the configuration file.
        """
        self.print_with_verbose('Creating empty configuration file...')
        config_file = os.path.join(directory, f'{self.base_name}_config.yml')
        try:
            shutil.copy(os.path.join(os.path.dirname(__file__), 'resources', 'Generated_config.yml'), config_file)
            return config_file
        except Exception as err:
            print_error(f'Error writing {config_file} - {err}')
            raise

    def save_image_and_desc(self, directory: str) -> tuple:
        """
        Writes template image and description.
        Args:
            directory: The directory to save the file to.

        Returns:
            image_path: The path to the image file.
            desc_path: The path to the description file.
        """
        self.print_with_verbose('Creating image and description files...')
        image_path = os.path.join(directory, f'{self.base_name}_image.png')
        desc_path = os.path.join(directory, f'{self.base_name}_description.md')
        try:
            shutil.copy(os.path.join(os.path.dirname(__file__), 'resources', 'Generated_image.png'), image_path)
            shutil.copy(os.path.join(os.path.dirname(__file__), 'resources', 'Generated_description.md'), desc_path)
            return image_path, desc_path
        except Exception as err:
            print_error(f'Error copying image and description files - {err}')
            return '', ''

    def generate_command_example(self, module: str) -> list:
        """
        Reads ansible-docs examples and outputs a equivalent XSOAR command example.

        Returns:
            example_command: List of command examples
        """
        self.print_with_verbose(f"Looking up command example for {module}...")

        example_command = ""
        command_name = self.get_command_name(module)

        module_examples = self.ansible_docs.get(module, {}).get("examples").strip()  # Pull up the examples section
        if module_examples is None:
            self.print_with_verbose(f"Module {module} has no examples")
            return []

        # If there are multiple just use the first, it's normally the most straight forward
        module_example = module_examples.split("- name:")[1].strip()

        # Get actual example
        example_command = f"!{command_name} "  # Start of command
        if self.host_type in REMOTE_HOST_TYPES:  # Add a example host target
            example_command += "host=\"123.123.123.123\" "
        if module_example:
            module_example_lines = module_example.split("\n")
            for line in module_example_lines[2:]:  # Quick yaml to list skipping the first task "- name" line
                split_line = line.split(": ")
                arg = split_line[0].strip()
                value = split_line[1].strip()
                # Skip args that the config says to ignore
                if (self.ignored_args) and (str(split_line) in self.ignored_args):
                    continue
                value = str(value).replace("\n", "\"")
                value = str(value).replace("\\", "\\\\")
                example_command += "{}=\"{}\" ".format(arg, value)

        self.example_commands.append(example_command)
        return self.example_commands

    def save_command_examples(self, directory: str) -> str:
        """
        Writes command examples to a file.
        Args:
            directory: The directory to save the file to.

        Returns:
            command_examples_file: The path to the command_examples file.
        """
        self.print_with_verbose('Creating command_examples file...')
        command_examples_file = os.path.join(directory, 'command_examples')
        try:
            with open(command_examples_file, 'w') as fp:

                for module in self.ansible_modules:
                    self.generate_command_example(module=module)

                fp.write('\n'.join(self.example_commands))
                return command_examples_file
        except Exception as err:
            print_error(f'Error writing {command_examples_file} - {err}')
            raise

    def save_package(self) -> tuple:
        """
        Creates a package for the integration including python, yaml, image and description files.

        Returns:
            code_path: The path to the python code file.
            yml_path: the path to the yaml file.
            image_path: The path to the image file.
            desc_path: The path to the description file.
            examples_path: The path to the examples file.
        """
        code_path = self.save_python_code(self.base_path)
        yml_path = self.save_yaml(self.base_path)
        image_path, desc_path = self.save_image_and_desc(self.base_path)
        examples_path = self.save_command_examples(self.base_path)
        return code_path, yml_path, image_path, desc_path, examples_path

    def print_with_verbose(self, text: str):
        """
        Prints a text verbose is set to true.
        Args:
            text: The text to print.
        """
        if self.verbose:
            print(text)

    def remove_ansible_markup(self, text: str):
        """
        Removes Ansible documentation link markup as per
        https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#linking-within-module-documentation
        """
        return re.sub('[ILUCMB]\\((.+?)\\)', '`\\g<1>`', text).strip()

    def get_command_name(self, module: str) -> str:
        """
        Determines what the XSOAR command name should be fore the module.

        Returns:
            command_name: XSOAR friendly command name
        """
        # In case ansible module has been provided in collection namespace form. We want just the module name
        module = module.split(".")[-1]

        command_name = ""
        # Don't double up with the prefix, if the module name already has the prefix
        if to_kebab_case(module).startswith(f"{self.command_prefix}-"):
            command_name = to_kebab_case(module)
        else:
            command_name = f"{self.command_prefix}-{to_kebab_case(module)}"
        return command_name

    def get_host_based_static_args(self) -> List[XSOARIntegration.Script.Command.Argument]:
        """
        Returns a XSOAR Command Argument list that would be used for modules that run on a remote host.
        """
        # These are args that are added to all commands that interact with a remote host
        static_args = []

        # host arg
        remote_host_desc = "hostname or IP of target. Optionally the port can be specified using :PORT. \
If multiple targets are specified using an array, the integration will use the configured concurrency \
factor for high performance."
        static_args.append(XSOARIntegration.Script.Command.Argument(
            name="host",
            description=remote_host_desc,
            required=True,
            is_array=True))
        return static_args

    def get_yaml_args(self, module) -> list:
        """
        For a given Ansible module parse it's yaml based documentation and return a list of corresponding XSOAR command arguments.
        Must first have the module documentation loaded via self.fetch_ansible_docs()
        """
        args = []
        command_options = self.ansible_docs.get(module, {}).get("doc").get("options")

        # Add static arguments if integration uses host based targets
        if self.host_type in REMOTE_HOST_TYPES:

            for static_arg in self.get_host_based_static_args():
                args.append(static_arg)

        for arg, option in command_options.items():

            # Skip args that the config says to ignore
            if self.ignored_args:
                if arg in self.ignored_args:
                    continue

            name = str(arg)

            if isinstance(option.get('description'), list):
                description = ""
                for line_of_doco in option.get('description'):
                    if not line_of_doco.isspace():
                        description = f"{description} {self.remove_ansible_markup(line_of_doco)}"
            else:
                description = str(option.get('description'))

            # if arg is deprecated skip it
            if description.startswith('`Deprecated'):
                print("Skipping arg %s as it is Deprecated" % str(arg))
                continue

            required = option.get('required', False)

            # Ansible docs have a empty list/dict as defaults....
            defaultValue = ""
            if option.get('default') and option.get('default') not in ['[]', '{}']:
                # The default True/False str cast of bool can be confusing. Using Yes/No instead.
                if type(option.get('default')) is bool:
                    defaultValue = "Yes" if option.get('default') else "No"
                else:
                    defaultValue = str(option.get('default'))

            predefined = None
            auto = None
            if option.get('choices'):
                predefined = list(option.get('choices'))
                auto = "PREDEFINED"
            else:
                # Ansible Docs don't explicitly mark true/false as choices for bools, so
                # we must do add it ourselves
                if type(option.get('default')) is bool:
                    predefined = ['Yes', 'No']
                    auto = "PREDEFINED"

            isArray = False
            if option.get('type') in ["list", "dict"]:
                isArray = True

            argument = XSOARIntegration.Script.Command.Argument(name=name, description=description,
                                                                is_array=isArray, required=required,
                                                                auto=auto, predefined=predefined,
                                                                defaultValue=defaultValue)
            args.append(argument)
        return args

    def get_yaml_outputs(self, module) -> list:
        """
        For a given Ansible module parse it's yaml based documentation and return a list of corresponding XSOAR command outputs.
        Must first have the module documentation loaded via self.fetch_ansible_docs()
        """
        command_doc = self.ansible_docs.get(module, {}).get("doc")
        command_returns = self.ansible_docs.get(module, {}).get("return")
        command_module = command_doc.get("module")
        outputs = []
        if command_returns:  # Some older ansible modules have no documented output
            for output, details in command_returns.items():
                output_to_add = {}
                if details:
                    output_to_add['contextPath'] = str("%s.%s.%s" %
                                                       (self.name, to_pascal_case(command_module), output))
                    if type(details.get('description')) == list:
                        # Do something if it is a list
                        output_to_add['description'] = ""
                        for line in details.get('description'):
                            output_to_add['description'] = output_to_add['description'] + \
                                "\n" + self.remove_ansible_markup(line)
                    else:
                        output_to_add['description'] = self.remove_ansible_markup(details.get('description'))

                    if details.get('type') == "str":
                        output_to_add['type'] = "string"

                    elif details.get('type') == "int":
                        output_to_add['type'] = "number"

                    # Don't think Ansible has any kind of datetime attribute but just in case...
                    elif details.get('type') == "datetime":
                        output_to_add['type'] = "date"

                    elif details.get('type') == "bool":
                        output_to_add['type'] = "boolean"

                    else:  # If the output is any other type it doesn't directly map to a XSOAR type
                        output_to_add['type'] = "unknown"
                outputs.append(output_to_add)
        return outputs

    def get_yaml_commands(self) -> list:
        """
        Looks up the Ansible module documentation and format it into XSOAR
        integration commands in yaml format (in object representation).

        Returns:
            commands: A list of integration commands in yaml format.
        """

        commands = []

        for module in self.ansible_modules:

            command_name = self.get_command_name(module)
            command_description = ''
            command_doc = self.ansible_docs.get(module, {}).get("doc")
            command_namespace = command_doc.get("collection", {}).split(".")[0]
            command_collection = command_doc.get("collection", {}).split(".")[1]
            command_module = command_doc.get("module")

            module_online_help = f"{ANSIBLE_ONLINE_DOCS_URL_BASE}{command_namespace}/{command_collection}/{command_module}_module.html"
            command_description = str(command_doc.get('short_description')) + \
                "\n Further documentation available at " + module_online_help

            # Add Arguments
            args = self.get_yaml_args(module)

            # Add Outputs
            outputs = self.get_yaml_outputs(module)

            commands.append(XSOARIntegration.Script.Command(command_name, command_description, args, outputs))

        self.commands = commands
        return commands
