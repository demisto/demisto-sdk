import json
import os
import re
import shutil
import sys
from distutils.util import strtobool
from typing import Any, List, Optional, Union

import autopep8
import yaml

from demisto_sdk.commands.common.docker_util import \
    ContainerRunner
from demisto_sdk.commands.common.tools import to_pascal_case, to_kebab_case, print_error
from demisto_sdk.commands.common.constants import (FileType)
from demisto_sdk.commands.generate_integration.XSOARIntegration import \
    XSOARIntegration
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator


ILLEGAL_CODE_NAMES = ['type', 'from', 'id', 'filter', 'list']
NAME_FIX = '_'
REQUIRED_KEYS = ['name','display','category','description','host_type','ansible_modules']
OPTIONAL_KEYS = ['test_command','command_prefix', 'ignored_args', 'configuration']
HOST_TYPES = ['ssh', 'winrm', 'nxos', 'ios', 'local']
REMOTE_HOST_TYPES = ['ssh', 'winrm', 'nxos', 'ios']
ANSIBLE_ONLINE_DOCS_URL_BASE = 'https://docs.ansible.com/ansible/latest/collections/'  # The URL of the online module documentation


class AnsibleIntegration:
    def __init__(self, base_name: str, verbose: bool = False, codegen_configuration: Optional[dict] = None, container_image: str = None, output_dir: str = ".", fix_code: bool = False):
        self.codegen_configuration = codegen_configuration if codegen_configuration else {}
        self.base_path = output_dir
        self.base_name = base_name
        self.name = ''
        self.display = ''
        self.category = ''
        self.description = ''
        self.host_type = 'local'
        self.test_command = None
        self.command_prefix = None
        self.ansible_modules: list = []
        self.ignored_args = None
        self.ansible_docs: dict = {}
        self.commands: dict = {}
        self.example_commands: list = []
        self.parameters: list = []
        self.verbose = verbose
        self.container_image = container_image
        self.fix_code = fix_code


    def load_config(self):
        """
        Loads the ansible codgen config
        """
        self.name = self.codegen_configuration.get('name')
        self.host_type = self.codegen_configuration.get('host_type')
        self.display = self.codegen_configuration.get('display')
        self.category = self.codegen_configuration.get('category')
        self.description = self.codegen_configuration.get('description')
        self.test_command = self.codegen_configuration.get('test_command', None)
        self.command_prefix = self.codegen_configuration.get('command_prefix', None)
        self.ansible_modules = self.codegen_configuration.get('ansible_modules')
        self.ignored_args = self.codegen_configuration.get('ignored_args', None)
        self.parameters = self.codegen_configuration.get('parameters', [])

        # Add concurrency tunable relating to non-local based targets
        if self.host_type != 'local':
            concurrency_factor = {}
            concurrency_factor['display'] = "Concurrency Factor"
            concurrency_factor['name'] = "concurrency"
            concurrency_factor['type'] = 0
            concurrency_factor['required'] = True
            concurrency_factor['defaultvalue'] = "4"
            concurrency_factor['additionalinfo'] = "If multiple hosts are specified in a command, how many hosts should be interacted with concurrently."
            self.parameters.append(concurrency_factor)
        
        # Set a command_prefix if not already provided
        if self.command_prefix is None:
            if len(self.name.split(' ')) == 1:  # If the config `name` is a single word then trust the caps
                self.command_prefix = self.name.lower()
            else:
                self.command_prefix = to_kebab_case(self.name)


    def fetch_ansible_docs(self):
        """
        Fetches the ansible documentation for the modules specified from the container image.
        Requires docker to function
        """
        # Lookup ansible module docs from container
        self.print_with_verbose('Creating container for module documentation lookup...')
        lookup_container = ContainerRunner(image=self.container_image, container_name="demisto-sdk-ansiblecodegen-lookup")

        # Make sure ansible-docs is present in container
        ansibledoc_version = str(lookup_container.exec(command = f"ansible-doc --version").get("Outputs"))
        if "ansible-doc 2." not in ansibledoc_version:    # Tested with ansible-doc 2.12.1
            print_error(f'ansible-doc 2.x not found in container or not compatible version. Is Ansible installed in container image?\nansible-docs reports: {ansibledoc_version}')
            raise
        
        for module in self.ansible_modules:
            ansibledoc_lookup = lookup_container.exec(command = f"ansible-doc -t module -j \"{module}\"").get("Outputs")
            # Unfortunately we can't rely on the status code and need to parse the text output :(

            # Check for ansible-doc error text
            if f"module {module} not found" in str(ansibledoc_lookup):
                print_error(f'Module {module} not found in container')
                raise

            try:
                self.ansible_docs.update(json.loads(ansibledoc_lookup))
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

        # Check that config is not empty
        if self.codegen_configuration == {}:
            return(False,"AnsibleCodeGen Config is empty")

        # Check for any config options not in defintion
        valid_keys = REQUIRED_KEYS + OPTIONAL_KEYS
        for key, value in self.codegen_configuration.items():
            if key not in valid_keys:
                validation = False
                validation_message += f"\n  * Invalid key found in config yaml: {key}"

        # Check that all required config options set
        for required_key in REQUIRED_KEYS:
            if self.codegen_configuration.get(required_key, False) == False:
                validation = False
                validation_message += f"\n  * Missing required key config in config yaml: {key}"

        # Check config options with fixed possible values are valid
        host_type = self.codegen_configuration.get('host_type')

        if host_type not in HOST_TYPES:
            validation = False
            validation_message += f"\n  * Invalid option for host_type: {host_type}"

        # Check if XSOAR config parameters provided are valid
        if self.codegen_configuration.get('configuration') is not None:

            self.print_with_verbose('Creating partial integration yaml file for config validation...')
            yaml_file = self.save_yaml(self.base_path, skip_commands=True)

            structure_validator = StructureValidator(yaml_file, predefined_scheme=FileType.INTEGRATION)
            integration_validator = IntegrationValidator(structure_validator)

            # Schema Validation
            schema_check = structure_validator.is_valid_scheme()
            if schema_check is False:
                validation = False
                validation_message += f"\n  * Failed Schema validation"

            # Param Validation tests
            param_valid = all([integration_validator.has_no_duplicate_params,
                integration_validator.is_proxy_configured_correctly,
                integration_validator.is_insecure_configured_correctly,
                integration_validator.is_checkbox_param_configured_correctly,
                integration_validator.is_checkbox_param_configured_correctly,
                integration_validator.is_not_valid_display_configuration,
                integration_validator.is_valid_hidden_params,
                integration_validator.is_valid_parameters_display_name,
                integration_validator.default_params_have_default_additional_info])

            if param_valid is not True:
                validation = False
                validation_message += f"\n  * Failed Param validation"

        # Check catgory
        category_valid = integration_validator.is_valid_category
        if category_valid is False:
            validation = False
            validation_message += f"\n  * Invalid category"

        # Check Docker image is valid
        container_image_valid = integration_validator.is_docker_image_valid
        if container_image_valid is False:
            validation = False
            validation_message += f"\n  * Failed container image validation"

        return(validation, validation_message)


    def generate_python_code(self) -> str:
        """
        Generate python code with the commands from the integration configuration file.

        Returns:
            code: The integration python code.
        """
        name = self.name
        code = '''import traceback
import ssh_agent_setup
import demistomock as demisto  # noqa: F401
from CommonServerPython import *  # noqa: F401

# Import Generated code
from AnsibleApiModule import *  # noqa: E402

'''

        code +="host_type = '%s'" % self.host_type
        
        code += '''

# MAIN FUNCTION


def main() -> None:
    """main function, parses params and runs command functions

    :return:
    :rtype:
    """

    # SSH Key integration requires ssh_agent to be running in the background
    ssh_agent_setup.setup()

    # Common Inputs
    command = demisto.command()
    args = demisto.args()
    int_params = demisto.params()

    try:

        if command == 'test-module':
'''

        if self.test_command is not None:
            test_command = self.test_command
            code += '''            # This is the call made when pressing the integration Test button.
            result = generic_ansible('%s', '%s', args, int_params, host_type)

            if result:
                return_results('ok')
            else:
                return_results(result)
''' % (name.lower(), test_command)
        else:
            code += '''            # This is the call made when pressing the integration Test button.
            return_results('This integration does not support testing from this screen. \\
                           Please refer to the documentation for details on how to perform \\
                           configuration tests.')'''
        
        self.print_with_verbose('Adding Ansible modules to the Python code.')
        for ansible_module in self.ansible_modules:

            demisto_command = ""

            ansible_module = ansible_module.split(".")[-1]  # In case ansible module has been provided in collection namespace form. We want just the module name

            if not to_kebab_case(ansible_module).startswith(self.command_prefix + '-'):
                demisto_command = self.command_prefix + '-' + to_kebab_case(ansible_module)
            else:
                demisto_command = to_kebab_case(ansible_module)

            code += "\n        elif command == '%s':\n            return_results(generic_ansible('%s', '%s', args, int_params, host_type))" % (demisto_command, name.lower(), ansible_module,)

        code += '''
    # Log exceptions and return errors
    except Exception as e:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute {command} command.\\nError:\\n{str(e)}')


# ENTRY POINT


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
'''

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

        int_script = XSOARIntegration.Script('', "python", "python3", self.container_image,False, commands)

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
                fp.write(yaml.dump(self.generate_yaml(skip_commands = skip_commands).to_dict()))
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


    def generate_command_example(self, module: str, command_name: str) -> str:
        """
        Reads ansible-docs examples and outputs a equivalent XSOAR command example.

        Returns:
            example_command: List of command examples
        """
        self.print_with_verbose('Looking up command example for {module}...')

        example_command = ""

        module_examples = self.ansible_docs.get(module).get("doc").get("examples")  # Pull up the examples section
        module_example = module_examples.split("- name:")[0]  # If there are multiple just use the first, it's normally the most straight forward

        # Get actual example
        example_command = f"!{command_name} "  # Start of command
        if self.host_type in REMOTE_HOST_TYPES:  # Add a example host target
            example_command += "host=\"123.123.123.123\" "
        if module_example is not None:
            for line in module_example.split("\n")[1:]:  # Quick yaml to dict skipping the task "- name" line
                for arg, value in line.split(": ").items():
                    # Skip args that the config says to ignore
                    if arg in self.ignored_args:
                        continue
                    value = str(value).replace("\n", "\"")
                    value = str(value).replace("\\", "\\\\")
                    example_command += "%s=\"%s\" " % (arg, value)
        
        self.example_commands.append(example_command)


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
                fp.writelines(self.example_commands)
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


    def get_yaml_commands(self) -> list:
        """
        Looks up the Ansible module documentation and format it into XSOAR
        integration commands in yaml format (in object representation).

        Returns:
            commands: A list of integration commands in yaml format.
        """

        commands = []

        for module in self.ansible_modules:

            command_name = ''
            command_description = ''
            command_doc = self.ansible_docs.get(module).get("doc")
            command_namespace = command_doc.get("collection").split(".")[0]
            command_collection = command_doc.get("collection").split(".")[1]
            command_module = command_doc.get("module")
            command_options = command_doc.get("options")
            command_returns = self.ansible_docs.get(module).get("return")

            if not to_kebab_case(module).startswith(self.command_prefix + '-'):  # Don't double up with the prefix, if the module name already has the prefix
                command_name = self.command_prefix + '-' + to_kebab_case(module)
            else:
                command_name = to_kebab_case(module)
            module_online_help = f"{ANSIBLE_ONLINE_DOCS_URL_BASE}{command_namespace}/{command_collection}/{command_module}_module.html"
            command_description = str(command_doc.get('short_description')) + "\n Further documentation available at " + module_online_help

            args = []
            # Add Arguments

            # Add static arguments if integration uses host based targets
            if self.host_type in REMOTE_HOST_TYPES:
                remote_host_desc = "hostname or IP of target. Optionally the port can be specified using :PORT. If multiple targets are specified using an array, the integration will use the configured concurrency factor for high performance."
                args.append(XSOARIntegration.Script.Command.Argument(name = "host", description = remote_host_desc, required = True, is_array = True))

            for arg, option in command_options.items():

                # Skip args that the config says to ignore
                if self.ignored_args:
                    if arg in self.ignored_args:
                        continue

                    argument = {}
                    argument['name'] = str(arg)

                    if isinstance(option.get('description'),list):
                        argument['description'] = ""
                        for line_of_doco in option.get('description'):
                            if not line_of_doco.isspace():
                                clean_line_of_doco = line_of_doco.strip()  # remove begin/end whitespace

                                # remove ansible link markup 
                                # https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#linking-within-module-documentation
                                clean_line_of_doco = re.sub('[ILUCMB]\((.+?)\)','`\g<1>`',clean_line_of_doco) 

                                argument['description'] = argument['description'] + ' ' + clean_line_of_doco
                        argument['description'] = argument['description'].strip()
                    else:
                        argument['description'] = str(option.get('description'))

                    # if arg is deprecicated skip it
                    if argument['description'].startswith('`Deprecated'):
                        print("Skipping arg %s as it is Deprecated" % str(arg))
                        continue

                    if option.get('required') == True:
                        argument['required'] = True

                    if str(option.get('default')) not in ['[]', '{}']:  # Ansible docs have a empty list/dict as defaults....
                        if option.get('default') is not None:
                            if type(option.get('default')) is bool:  # The default True/False str cast of bool can be confusing. Using Yes/No instead.
                                if option.get('default') is True:
                                    argument['defaultValue'] = "Yes"
                                if option.get('default') is False:
                                    argument['defaultValue'] = "No"
                            else:
                                argument['defaultValue'] = str(option.get('default'))

                    if option.get('choices') is not None:
                        argument['predefined'] = []
                        argument['auto'] = "PREDEFINED"
                        for choice in option.get('choices'):
                            argument['predefined'].append(str(choice))
                    else:
                        # Ansible Docs don't explicitly mark true/false as choices for bools, so we must do add it ourselves
                        if type(option.get('default')) is bool:
                            argument['predefined'] = ['Yes', 'No']
                            argument['auto'] = "PREDEFINED"


                    if option.get('type') in ["list", "dict"]:
                        argument['isArray'] = True

                    args.append(argument)

            # Add Outputs
            outputs = []
            if command_returns is not None:  # Some older ansible modules have no documented output
                for output, details in command_returns.items():
                    output_to_add = {}
                    if details is not None:
                        output_to_add['contextPath'] = str("%s.%s.%s" % (self.name, to_pascal_case(command_module), output))

                        # remove ansible link markup 
                        # https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#linking-within-module-documentation
                        if type(details.get('description')) == list:
                            # Do something if it is a list
                            output_to_add['description'] = ""
                            for line in details.get('description'):
                                clean_line_of_description = re.sub('[ILUCMB]\((.+?)\)','`\g<1>`', line) 
                                output_to_add['description'] = output_to_add['description'] + "\n" + clean_line_of_description
                            output_to_add['description'] = output_to_add['description'].strip()
                        else:
                            clean_line_of_description = re.sub('[ILUCMB]\((.+?)\)','`\g<1>`',str(details.get('description'))) 
                            output_to_add['description'] = clean_line_of_description.strip()

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
            commands.append(XSOARIntegration.Script.Command(command_name, command_description, args, outputs))

        return commands