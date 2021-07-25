import json
import os
import re
import shutil
import sys
from distutils.util import strtobool
from typing import Any, List, Optional, Union

import autopep8
import yaml
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.tools import camel_to_snake, print_error
from demisto_sdk.commands.generate_integration.base_code import (
    BASE_ARGUMENT, BASE_BASIC_AUTH, BASE_CLIENT, BASE_CODE_TEMPLATE,
    BASE_CREDENTIALS, BASE_DATA, BASE_FUNCTION, BASE_HEADER,
    BASE_LIST_FUNCTIONS, BASE_PARAMS, BASE_PROPS, BASE_REQUEST_FUNCTION,
    BASE_TOKEN)
from demisto_sdk.commands.generate_integration.XSOARIntegration import \
    XSOARIntegration

ILLEGAL_DESCRIPTION_CHARS = ['\n', 'br', '*', '\r', '\t', 'para', 'span', '«', '»', '<', '>']
ILLEGAL_CODE_CHARS = ILLEGAL_DESCRIPTION_CHARS + [' ', '.', ',', '(', ')', '`', ':', "'", '"', '[', ']']
ILLEGAL_CODE_NAMES = ['type', 'from', 'id', 'filter', 'list']
NAME_FIX = '_'
OUTPUT_TYPES = {
    'string': 'String',
    'integer': 'Number',
    'object': 'Unknown',
    'array': 'Unknown',
    'boolean': 'Boolean',
}
ARGUMENT_TYPES = {
    'string': 'str',
    'integer': 'int',
    'boolean': 'bool',
    'file': 'str',
    'int': 'int',
    'str': 'str',
}
JSON_TYPE_HEADER = 'application/json'
ALL_TYPE_HEADER = '*/*'
DEFAULT_HOST = 'https://www.example.com/api'
BEARER_AUTH_TYPE = 'apiKey'
BASIC_AUTH_TYPE = 'basic'
MAX_DESCRIPTION_WORDS = 3000


class OpenAPIIntegration:
    def __init__(self, file_path: str, base_name: str, command_prefix: str, context_path: str,
                 unique_keys: Optional[str] = None, root_objects: Optional[str] = None,
                 verbose: bool = False, fix_code: bool = False, configuration: Optional[dict] = None):
        self.json: dict = {}
        self.file_path = file_path
        self.base_name = base_name
        self.command_prefix = command_prefix
        self.context_path = context_path
        self.unique_keys = unique_keys.split(',') if unique_keys is not None else []
        self.root_objects = root_objects.split(',') if root_objects is not None else []
        self.configuration = configuration if configuration else {}
        self.security_definitions = None
        self.host = ''
        self.base_path = ''
        self.name = ''
        self.description = ''
        self.definitions: dict = {}
        self.components: dict = {}
        self.reference: dict = {}
        self.functions: list = []
        self.parameters: list = []
        self.verbose = verbose
        self.fix_code = fix_code

    def load_file(self):
        """
        Loads a swagger file and parses it into a functions list.
        """

        try:
            with open(self.file_path, 'rb') as json_file:
                self.json = json.load(json_file)
        except Exception as e:
            print_error(f'Failed to load the swagger file: {e}')
            sys.exit(1)

        if self.json.get('host', None):
            self.host = self.json.get('host', None)
        elif self.json.get('servers', None):
            self.host = self.json.get('servers', [])[0]['url']
        else:
            self.host = ''
        self.base_path = self.json.get('basePath', '')
        self.name = self.json['info']['title']
        self.description = self.clean_description(self.json.get('info', {}).get('description', ''))
        self.definitions = self.json.get('definitions', {})
        self.components = self.json.get('components', {})
        self.reference = self.definitions or self.components.get('schemas', {}) or {}
        self.security_definitions = self.json.get('securityDefinitions', {})
        self.functions = []

        for path, function in self.json['paths'].items():
            try:
                for method, data in function.items():
                    if not data:
                        continue
                    if isinstance(data, list):
                        data = data[0]
                    self.print_with_verbose(f'Adding command for the path: {path}')
                    self.add_function(path, method, data, function.get(
                        'parameters', []))
            except Exception as e:
                print_error(f'Failed adding the command for the path {path}: {e}')
                raise
        self.handle_duplicates(self.functions)
        self.functions = sorted(self.functions, key=lambda x: x['name'])
        if not self.configuration:
            self.generate_configuration()

    def generate_configuration(self):
        """
        Generates an integration configuration file according to parsed functions from a swagger file.
        """

        security_types: list = []
        if self.security_definitions:
            all_security_types = [s.get('type') for s in self.security_definitions.values()]
            security_types = [t for t in all_security_types if t in [BEARER_AUTH_TYPE, BASIC_AUTH_TYPE]]
        if not security_types:
            security_types = [BEARER_AUTH_TYPE]

        configuration = {
            'name': self.name or 'GeneratedIntegration',
            'description': self.description or 'This integration was auto generated by the Cortex XSOAR SDK.',
            'category': 'Utilities',
            'url': self.host or DEFAULT_HOST,
            'auth': security_types,
            'context_path': self.context_path,
            'commands': []
        }
        for function in self.functions:
            command = {
                'name': function['name'].replace('_', '-'),
                'path': function['path'],
                'method': function['method'],
                'description': function['description'],
                'arguments': [],
                'outputs': [],
                'context_path': function.get('context_path', ''),
                'root_object': function.get('root_object', '')
            }

            headers = []
            if function['consumes'] and JSON_TYPE_HEADER not in function['consumes'] \
                    and ALL_TYPE_HEADER not in function['consumes']:
                headers.append({'Content-Type': function['consumes'][0]})

            if function['produces'] and JSON_TYPE_HEADER not in function['produces'] \
                    and ALL_TYPE_HEADER not in function['produces']:
                headers.append({'Accept': function['produces'][0]})
            command['headers'] = headers

            for arg in function['arguments']:
                command['arguments'].append({
                    'name': str(arg.get('name', '')),
                    'description': arg.get('description', ''),
                    'required': arg.get('required'),
                    'default': arg.get('default', ''),
                    'in': arg.get('in', ''),
                    'ref': arg.get('ref', ''),
                    'type': arg.get('type', 'string'),
                    'options': arg.get('enums'),
                    'properties': arg.get('properties', {})
                })

            for output in function['outputs']:
                command['outputs'].append({
                    'name': output['name'],
                    'description': output['description'],
                    'type': output['type']
                })

                if output['name'] in self.unique_keys:
                    command['unique_key'] = output['name']

            if 'unique_key' not in command:
                command['unique_key'] = ''

            configuration['commands'].append(command)  # type: ignore

        configuration['code_type'] = 'python'
        configuration['code_subtype'] = 'python3'

        try:
            latest_tag = DockerImageValidator.get_docker_image_latest_tag_request('demisto/python3')
            configuration['docker_image'] = f'demisto/python3:{latest_tag}'
        except Exception as e:
            self.print_with_verbose(f'Failed getting latest docker image for demisto/python3: {e}')

        self.configuration = configuration

    def generate_python_code(self) -> str:
        """
        Generate python code from the base template with the commands from the integration configuration file.

        Returns:
            code: The integration python code.
        """

        # Use the code from base_code in py as the basis
        code: str = BASE_CODE_TEMPLATE

        # Build the functions from configuration file
        functions: list = []
        req_functions: list = []
        for command in self.configuration['commands']:
            function, req_function = self.get_python_command_and_request_functions(command)
            functions.append(function)
            req_functions.append(req_function)

        code = code.replace('$FUNCTIONS$', '\n'.join(functions))
        code = code.replace('$BASEURL$', self.base_path)
        client = BASE_CLIENT.replace('$REQUESTFUNCS$', '\n'.join(req_functions))
        code = code.replace('$CLIENT$', client).replace('$CLIENT_API_KEY$', '')

        if BEARER_AUTH_TYPE in self.configuration['auth']:
            code = code.replace('$BEARERAUTHPARAMS$', BASE_TOKEN)
        else:
            code = '\n'.join(
                [x for x in code.split('\n') if any(ext not in x for ext in ['$BEARERAUTHPARAMS$'])])

        if BASIC_AUTH_TYPE in self.configuration['auth']:
            code = code.replace('$BASEAUTHPARAMS$', BASE_CREDENTIALS)
            code = code.replace('$BASEAUTH$', BASE_BASIC_AUTH)
        else:
            code = '\n'.join(
                [x for x in code.split('\n') if '$BASEAUTHPARAMS$' not in x])
            code = code.replace('$BASEAUTH$', 'None')

        list_functions = []

        # Add the command mappings:
        for command in self.functions:
            prefix = f'{self.command_prefix}-' if self.command_prefix else ''

            if self.command_prefix:
                prefix = f'{self.command_prefix}-'

            function = BASE_LIST_FUNCTIONS.replace(
                '$FUNCTIONNAME$', f"{prefix}{command['name']}".replace('_', '-'))
            fn = command['name'].replace('-', '_')
            function = function.replace('$FUNCTIONCOMMAND$', f'{fn}_command')
            list_functions.append(function)

        code = code.replace('$COMMANDSLIST$', '\n\t'.join(list_functions))
        self.print_with_verbose('Finished generating the Python code.')

        if self.fix_code:
            self.print_with_verbose('Fixing the code with autopep8...')
            code = autopep8.fix_code(code)

        return code

    def get_python_command_and_request_functions(self, command: dict) -> tuple:
        """
        Generates a command function and a request function in python
        according to a given command in the integration configuration file.

        Args:
            command: The integration command from the configuration file.

        Returns:
            function:  The command function in python according to the command.
            req_function: The request function in python according to the command.
        """
        function_name = command['name'].replace('-', '_')
        headers = command['headers']
        self.print_with_verbose(f'Adding the function {function_name} to the code...')
        function = BASE_FUNCTION.replace('$FUNCTIONNAME$', function_name)
        req_function = BASE_REQUEST_FUNCTION.replace('$FUNCTIONNAME$', function_name)
        argument_names, arguments, arguments_found, body_data, params_data = self.process_command_arguments(command)
        if arguments_found:
            function = function.replace('$ARGUMENTS$', '\n    '.join(arguments))
            function = function.replace('$REQARGS$', ', '.join(argument_names))
            req_function = req_function.replace('$REQARGS$', ', $REQARGS$')
            req_function = req_function.replace('$REQARGS$', ', '.join(argument_names))
        else:
            req_function = req_function.replace('$REQARGS$', '')
            function = function.replace('$REQARGS$', '')
            function = '\n'.join(
                [x for x in function.split('\n') if '$ARGUMENTS$' not in x])
        req_function = req_function.replace('$METHOD$', command['method'])
        command['path'] = f"'{command['path']}'" if "'" not in command['path'] else command['path']
        command['path'] = f"f{command['path']}" if "{" in command['path'] else command['path']
        for param in re.findall(r'{([^}]+)}', command['path']):  # get content inside curly brackets
            if param in ILLEGAL_CODE_NAMES:
                command['path'] = command['path'].replace(param, f'{param}{NAME_FIX}')
        req_function = req_function.replace('$PATH$', command['path'])
        if params_data:
            params = self.format_params(params_data, BASE_PARAMS, '$PARAMS$')
            req_function = req_function.replace('$PARAMETERS$', params)
        else:
            req_function = '\n'.join(
                [x for x in req_function.split('\n') if '$PARAMETERS$' not in x])
        if body_data:
            body_data = self.format_params(body_data, BASE_DATA, '$DATAOBJ$')
            req_function = req_function.replace('$DATA$', body_data)
        else:
            req_function = '\n'.join(
                [x for x in req_function.split('\n') if '$DATA$' not in x])
        if params_data:
            req_function = req_function.replace(
                '$NEWPARAMS$', ', params=params')
        else:
            req_function = req_function.replace('$NEWPARAMS$', '')
        if body_data:
            req_function = req_function.replace('$NEWDATA$', ', json_data=data')
        else:
            req_function = req_function.replace('$NEWDATA$', '')
        if headers:
            new_headers = []
            for header in headers:
                for k, v in header.items():
                    new_headers.append(BASE_HEADER.replace('$HEADERKEY$', f"'{k}'")
                                       .replace('$HEADERVALUE$', f"'{v}'"))

            req_function = req_function.replace('$HEADERSOBJ$', ' \n        '.join(new_headers))
        else:
            req_function = '\n'.join([x for x in req_function.split('\n') if '$HEADERSOBJ$' not in x])

        if self.configuration['context_path']:
            context_name = self.context_path
        else:
            context_name = command['name'].title().replace('_', '')
        if command.get('context_path'):
            function = function.replace('$CONTEXTPATH$', f'.{command["context_path"]}')
        else:
            function = function.replace('$CONTEXTPATH$', '')
        if command.get('root_object'):
            function = function.replace('$OUTPUTS$', f"response.get('{command['root_object']}')")
        else:
            function = function.replace('$OUTPUTS$', 'response')
        if command['unique_key']:
            function = function.replace('$UNIQUEKEY$', command['unique_key'])
        else:
            function = function.replace('$UNIQUEKEY$', '')
        function = function.replace('$CONTEXTNAME$', context_name)
        return function, req_function

    def process_command_arguments(self, command: dict) -> tuple:
        """
        Processes the arguments for a command and set them up to paste in the python code.
        Args:
            command: The command from the integration configuration file.

        Returns:
            argument_names: A list of processed argument names.
            arguments: A list of the processed arguments to paste in the python code, e.g.:
            >>> str(args.get('accountId', ''))
            arguments_found: Whether any arguments were found for the command.
            body_data: The arguments to set in the body of the request.
            params_data: The arguments to set in the query of the request.
        """
        params_data = []
        body_data = []
        arguments = []
        argument_names = []
        arguments_found = False
        for arg in command['arguments']:
            arguments_found = True
            code_arg_name = arg['name']
            ref_arg_name = arg['name']
            arg_type = arg.get('type')
            arg_props = []
            if arg.get('ref'):
                ref_arg_name = f'{arg["ref"]}_{ref_arg_name}'.lower()
                code_arg_name = f'{arg["ref"]}_{code_arg_name}'.lower()
            if code_arg_name in ILLEGAL_CODE_NAMES:
                code_arg_name = f'{code_arg_name}{NAME_FIX}'
            if arg['properties']:
                for k, v in arg['properties'].items():
                    prop_default = self.get_arg_default(v)
                    prop_arg_name = f'{code_arg_name}_{k}'.lower()
                    prop_arg_type = ARGUMENT_TYPES.get(v.get('type', 'string'), 'str')
                    if prop_arg_type == 'bool':
                        prop_arg_type = 'argToBoolean'
                    if prop_arg_name in ILLEGAL_CODE_NAMES:
                        prop_arg_name = f'{prop_arg_name}{NAME_FIX}'
                    this_prop_argument = f"{BASE_ARGUMENT.replace('$DARGNAME$', prop_arg_name)}{prop_default})"
                    this_prop_argument = this_prop_argument.replace('$SARGNAME$', prop_arg_name)
                    if 'None' not in prop_default:
                        this_prop_argument = this_prop_argument.replace('$ARGTYPE$', f'{prop_arg_type}(') + ')'
                    else:
                        this_prop_argument = this_prop_argument.replace('$ARGTYPE$', '')
                    arg_props.append({k: prop_arg_name})
                    arguments.append(this_prop_argument)
                all_props = self.format_params(arg_props, BASE_PROPS, '$PROPS$')
                this_argument = f'{code_arg_name} = {all_props}'
                if arg_type == 'array':
                    this_argument = f'argToList({this_argument})'
            else:
                if arg_type == 'array':
                    argument_default = ', []'
                    new_arg_type = 'argToList'
                else:
                    argument_default = self.get_arg_default(arg)
                    new_arg_type = ARGUMENT_TYPES.get(arg['type'], 'str')
                    if new_arg_type == 'bool':
                        new_arg_type = 'argToBoolean'

                this_argument = f"{BASE_ARGUMENT.replace('$DARGNAME$', ref_arg_name)}{argument_default})"
                if 'None' not in argument_default:
                    this_argument = this_argument.replace('$ARGTYPE$', f'{new_arg_type}(') + ')'
                else:
                    this_argument = this_argument.replace('$ARGTYPE$', '')

            this_argument = this_argument.replace('$SARGNAME$', code_arg_name)
            argument_names.append(code_arg_name)
            arguments.append(this_argument)
            if 'query' in arg['in']:
                params_data.append({
                    arg['name']: ref_arg_name
                })
            elif arg['in'] in ['formData', 'body']:
                body_data.append({
                    arg['name']: ref_arg_name
                })

        return argument_names, arguments, arguments_found, body_data, params_data

    def generate_yaml(self) -> XSOARIntegration:
        """
        Generates the yaml structure of the integration.

        Returns:
            integration: An object representation of the integration yaml structure.

        """
        # Create the commands section
        commands = self.get_yaml_commands()
        commonfields = XSOARIntegration.CommonFields(self.configuration['name'])
        name = self.configuration['name']
        display = self.configuration['name']
        category = self.configuration['category']
        description = self.configuration['description']
        configurations = self.get_yaml_params()

        int_script = XSOARIntegration.Script('', self.configuration['code_type'],
                                             self.configuration['code_subtype'], self.configuration['docker_image'],
                                             self.configuration.get('fetch_incidents', False), commands)

        integration = XSOARIntegration(commonfields, name, display, category, description, configuration=configurations,
                                       script=int_script)
        return integration

    def get_yaml_params(self) -> list:
        """
        Gets the configuration params for the integration.

        Returns:
            params: A list of integration params.
        """
        url = self.configuration['url']
        params = [XSOARIntegration.Configuration(display=f'Server URL (e.g. {url})',
                                                 name='url',
                                                 defaultvalue=url,
                                                 type_=0,
                                                 required=True)]
        if not isinstance(self.configuration['auth'], list):
            self.configuration['auth'] = [self.configuration['auth']]
        if BEARER_AUTH_TYPE in self.configuration['auth']:
            params.append(XSOARIntegration.Configuration(display='API Key',
                                                         name='api_key',
                                                         required=True,
                                                         type_=4))
        if BASIC_AUTH_TYPE in self.configuration['auth']:
            params.append(XSOARIntegration.Configuration(display='Username',
                                                         name='credentials',
                                                         required=True,
                                                         type_=9))
        if self.configuration.get('fetch_incidents', False):
            params.extend([
                XSOARIntegration.Configuration(display='Fetch incidents',
                                               name='isFetch',
                                               type_=8,
                                               required=False),
                XSOARIntegration.Configuration(display='Incident type',
                                               name='incidentType',
                                               type_=13,
                                               required=False),
                XSOARIntegration.Configuration(display='Maximum number of incidents per fetch',
                                               name='max_fetch',
                                               defaultvalue='10',
                                               type_=0,
                                               required=False),
                XSOARIntegration.Configuration(display='Fetch alerts with status (ACTIVE, CLOSED)',
                                               name='alert_status',
                                               defaultvalue='ACTIVE',
                                               type_=15,
                                               required=False,
                                               options=['ACTIVE', 'CLOSED']),
                XSOARIntegration.Configuration(display='Fetch alerts with type',
                                               name='alert_type',
                                               type_=0,
                                               required=False),
                XSOARIntegration.Configuration(display='Minimum severity of alerts to fetch',
                                               name='min_severity',
                                               defaultvalue='Low',
                                               type_=15,
                                               required=True,
                                               options=['Low', 'Medium', 'High', 'Critical'])])
        params.extend([XSOARIntegration.Configuration(display='Trust any certificate (not secure)',
                                                      name='insecure',
                                                      type_=8,
                                                      required=False),
                       XSOARIntegration.Configuration(display='Use system proxy settings',
                                                      name='proxy',
                                                      type_=8,
                                                      required=False)])
        return params

    def get_yaml_commands(self) -> list:
        """
        Gets the integration commands in yaml format (in object representation) according to the configuration.

        Returns:
            commands: A list of integration commands in yaml format.
        """
        commands = []
        for command in self.configuration['commands']:
            args = []
            for arg in command['arguments']:
                options = None
                auto = None
                arg_name = arg['name']
                if arg.get('ref'):
                    arg_name = f"{arg['ref']}_{arg_name}".lower()
                required = True if arg['required'] else False
                description = arg.get('description', '')
                is_array = True if arg['type'] == 'array' else False
                if arg['properties']:
                    for k, v in arg['properties'].items():
                        prop_arg_name = f'{arg_name}_{k}'
                        if description:
                            prop_description = f'{description} - {k}'
                        else:
                            prop_description = f'{arg_name} {k}'
                        prop_required = True if required is True and v.get('required') else False
                        options = None
                        auto = None
                        if v.get('options'):
                            auto = 'PREDEFINED'
                            options = v['options']
                        args.append(XSOARIntegration.Script.Command.Argument(prop_arg_name, prop_description,
                                                                             prop_required, auto, options))
                else:
                    if arg['options']:
                        auto = 'PREDEFINED'
                        options = arg['options']

                    args.append(XSOARIntegration.Script.Command.Argument(arg_name, description, required,
                                                                         auto, options, is_array))

            outputs = []
            context_path = command['context_path']
            for output in command['outputs']:
                output_name = output['name']
                if context_path:
                    output_name = f'{context_path}.{output_name}'
                if self.context_path:
                    output_name = f'{self.context_path}.{output_name}'
                output_description = output['description']
                output_type = output['type']

                outputs.append(XSOARIntegration.Script.Command.Output(output_type, output_name, output_description))

            prefix = ''
            if self.command_prefix:
                prefix = f'{self.command_prefix}-'
            command_name = f"{prefix}{command['name']}".replace('_', '-')
            command_description = command['description']
            commands.append(XSOARIntegration.Script.Command(command_name, command_description, args, outputs))

        return commands

    def extract_properties(self, obj: Union[dict, list], context: list) -> list:
        """
        Extracts properties recursively from an object in the swagger file.
        Args:
            obj: The swagger file object.
            context: The context of the object in the swagger file.

        Returns:
            results: A list of the object's properties.
        """
        arr: list = []

        def extract(extracted_object: Union[dict, list], prop_arr: list, current_context: list) -> list:

            if isinstance(extracted_object, list):
                for item in extracted_object:
                    extract(item, prop_arr, current_context)

            elif isinstance(extracted_object, dict):
                if extracted_object.get('type') and type(extracted_object.get('type')) == str:
                    if extracted_object.get('type') in ['array', 'object']:
                        refs = self.extract_values(extracted_object, '$ref')
                        if refs:
                            ref = refs[0].split('/')[-1]
                            prop_arr = extract(self.extract_values(self.reference.get(ref, {}), 'properties'), prop_arr,
                                               current_context)
                        elif extracted_object.get('items'):
                            for k, v in extracted_object.get('items', {}).items():
                                prop_arr = extract(v, prop_arr, current_context)
                        elif extracted_object.get('properties'):
                            prop_arr = extract(
                                extracted_object.get('properties', {}), prop_arr, current_context)
                        elif extracted_object.get('allOf'):
                            for item in extracted_object.get('allOf', []):
                                prop_arr = extract(item, prop_arr, current_context)
                    else:
                        prop_arr.append({'name': '.'.join(current_context), 'type': extracted_object.get('type',
                                                                                                         'Unknown'),
                                         'description': extracted_object.get('description', '')})
                elif extracted_object.get('type') and type(extracted_object.get('type')) == dict:
                    for k, v in extracted_object.items():
                        current_context.append(k)
                        prop_arr = extract(v, prop_arr, current_context)
                        current_context.pop()
                else:
                    for k, v in extracted_object.items():
                        current_context.append(k)
                        prop_arr = extract(v, prop_arr, current_context)
                        current_context.pop()

            return prop_arr

        results = extract(obj, arr, context)
        return results

    def extract_outputs(self, data: dict) -> tuple:
        """
        Extracts outputs from a function(path) in a swagger file.
        Args:
            data: The data of the swagger function.

        Returns:
            outputs: The extracted outputs.
            root_object: The root object of the command output.
            context_path: The context path of the command output.
        """
        outputs: list = []
        root_object: str = ''
        context_path: str = ''
        for response_code, response in data.get('responses', {}).items():
            new_response = {}
            try:
                if int(response_code) != 200:
                    continue
            except Exception:
                self.print_with_verbose(f'Could not get the code for the response {response}')

            new_response['description'] = response.get('description', None)
            all_items = []
            schemas = self.extract_values(response, 'schema')
            if schemas:
                schema = schemas[0]
                refs = self.extract_values(schema, '$ref')
                found_root = False
                if refs:
                    for ref in refs:
                        ref = ref.split('/')[-1]
                        ref_props = self.extract_values(self.reference.get(ref, {}), 'properties')
                        # Addition of filtering dicts only was added because some swaggers contain example files
                        # Which are written in string and caused errors on ref_props[0].items()
                        ref_props = [ref_prop for ref_prop in ref_props if isinstance(ref_prop, dict)]
                        if ref_props:
                            for k, prop in ref_props[0].items():
                                if k in self.root_objects:
                                    # We found a root, we need the output of the root only
                                    root_object = k
                                    all_items = [prop]
                                    path = self.extract_values(prop, '$ref')
                                    if path:
                                        context_path = self.clean_function_name(path[0].split('/')[-1], False)
                                    found_root = True
                            if found_root:
                                break

                            all_items.extend(ref_props)
                        if not context_path:
                            context_path = self.clean_function_name(ref, False)
                else:
                    all_items.extend(self.extract_values(schema, 'properties'))

                properties = self.extract_properties(all_items, [])
                for prop in properties:
                    description = prop.get('description', '')
                    this_type = prop.get('type', 'object')
                    this_type = OUTPUT_TYPES.get(this_type, 'Unknown')
                    resp_name = prop.get('name')
                    description = self.clean_description(description)
                    outputs.append({'name': resp_name, 'type': this_type, 'description': description})

        return outputs, root_object, context_path

    def extract_args(self, arguments: list) -> list:
        """
        Extracts arguments from a function(path) in a swagger file.
        Args:
            arguments: The list of arguments from a function(path) in the swagger file.

        Returns:
            extracted_arguments: The extracted arguments.
        """
        extracted_arguments: list = []
        for arg in arguments:
            refs = []
            if 'schema' in arg:
                refs = self.extract_values(arg['schema'], '$ref')
                for ref in refs:
                    ref = ref.split('/')[-1]
                    ref_args = self.extract_values(self.reference.get(ref, {}), 'properties')
                    # Addition of filtering dicts only was added because some swaggers contain example files
                    # Which are written in string and caused errors on ref_props[0].items()
                    ref_args = [ref_arg for ref_arg in ref_args if isinstance(ref_arg, dict)]
                    for ref_arg in ref_args:
                        for k, v in ref_arg.items():
                            new_ref_arg = {'name': k, 'in': arg.get('in'),
                                           'required': True if k in self.reference.get(ref, {}).get('required', [])
                                           else False}
                            if '$ref' in ref_arg[k]:
                                new_ref_arg['properties'] = {}
                                c_ref = ref_arg[k]['$ref'].split('/')[-1]
                                complex_refs = self.extract_values(self.reference.get(c_ref, {}), 'properties')
                                for complex_ref in complex_refs:
                                    for ck, cv in complex_ref.items():
                                        new_ref_arg['properties'][ck] = {}
                                        new_ref_arg['properties'][ck]['type'] = cv.get('type', 'string')
                                        new_ref_arg['properties'][ck]['description'] = cv.get('description', '')
                                        new_ref_arg['properties'][ck]['required'] = True \
                                            if ck in self.reference.get(c_ref, {}).get('required', []) else False
                                        new_ref_arg['properties'][ck]['options'] = [str(x) for x in cv.get('enum')] \
                                            if arg.get('enum', None) else None
                            else:
                                new_ref_arg.update(v)
                            new_ref_arg['ref'] = ref
                            extracted_arguments.append(self.init_arg(new_ref_arg))
            if not refs:
                if arg.get('schema', {}).get('type'):
                    arg['type'] = arg['schema']['type']
                extracted_arguments.append(self.init_arg(arg))

        return extracted_arguments

    def add_function(self, path: str, method: str, data: dict, params: list):
        """
        Adds a function parsed from the swagger data.
        Args:
            path: The function path.
            method: The function request method.
            data: The function data.
            params: The function parameters.

        """
        new_function: dict = {'path': '/'.join(x.split(' ')[0] for x in path.split('/')).strip('/'), 'method': method}
        name = data.get('operationId', None)
        if not name:
            name = data.get('summary', '').lower()
            name = name.replace(' ', '-')
        if not name:
            name = '_'.join([re.sub(r'{[^)]*\}', '', x) for x in path.split('/')])

        name = self.clean_function_name(name)
        new_function['name'] = name
        func_desc = data.get('summary', None)
        if not func_desc:
            func_desc = data.get('description', '')
        new_function['description'] = self.clean_description(func_desc)
        new_function['arguments'] = []
        new_function['parameters'] = data.get('parameters', None)
        new_function['consumes'] = data.get('consumes', [])
        new_function['produces'] = data.get('produces', [])
        new_function['outputs'] = []
        if not new_function['parameters']:
            new_function['parameters'] = params
            iter_item = params
        else:
            iter_item = data.get('parameters', [])
        new_function['arguments'] = self.extract_args(iter_item)
        outputs, root_object, context_path = self.extract_outputs(data)
        new_function['outputs'] = outputs
        new_function['root_object'] = root_object
        new_function['context_path'] = context_path
        self.functions.append(new_function)

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

    def save_yaml(self, directory: str) -> str:
        """
        Writes the yaml to a file.
        Args:
            directory: The directory to save the file to.

        Returns:
            yaml_file: The path to the yaml file.
        """
        self.print_with_verbose('Creating yaml file...')
        yaml_file = os.path.join(directory, f'{self.base_name}.yml')
        try:
            with open(yaml_file, 'w') as fp:
                fp.write(yaml.dump(self.generate_yaml().to_dict()))
            return yaml_file
        except Exception as err:
            print_error(f'Error writing {yaml_file} - {err}')
            raise

    def save_config(self, config: dict, directory: str) -> str:
        """
        Writes the integration configuration to a file in JSON format.
        Args:
            config: The integration configuration.
            directory: The directory to save the file to.

        Returns:
            config_file: The path to the configuration file.
        """
        self.print_with_verbose('Creating configuration file...')
        config_file = os.path.join(directory, f'{self.base_name}_config.json')
        try:
            with open(config_file, 'w') as fp:
                json.dump(config, fp, indent=4)
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

    def save_package(self, directory: str) -> tuple:
        """
        Creates a package for the integration including python, yaml, image and description files.
        Args:
            directory: The directory to create the package in.

        Returns:
            code_path: The path to the python code file.
            yml_path: the path to the yaml file.
            image_path: The path to the image file.
            desc_path: The path to the description file.
        """
        code_path = self.save_python_code(directory)
        yml_path = self.save_yaml(directory)
        image_path, desc_path = self.save_image_and_desc(directory)
        return code_path, yml_path, image_path, desc_path

    def print_with_verbose(self, text: str):
        """
        Prints a text verbose is set to true.
        Args:
            text: The text to print.
        """
        if self.verbose:
            print(text)

    def init_arg(self, arg: dict):
        """
        Parses an argument.
        Args:
            arg: The argument to parse.

        Returns:
            new_arg: The parsed argument.
        """
        new_arg = {}
        arg_desc = arg.get('description', '')
        arg_desc = self.clean_description(arg_desc)
        new_arg['name'] = arg.get('name', '')
        new_arg['description'] = arg_desc
        new_arg['required'] = arg.get('required')
        new_arg['default'] = arg.get('default', '')
        new_arg['in'] = arg.get('in', 'path')
        new_arg['type'] = arg.get('type', 'string')
        new_arg['properties'] = arg.get('properties', {})
        new_arg['ref'] = arg.get('ref', '')
        new_arg['enums'] = [str(x) for x in arg.get('enum', [])] if arg.get('enum', None) else None

        return new_arg

    @staticmethod
    def extract_values(obj: Union[dict, list], key: str) -> list:
        """
        Extracts values from an object by a provided key.
        Args:
            obj: The object to extract.
            key: The key to extract by.

        Returns:
            results: The extracted values.
        """
        arr: list = []

        def extract(extracted_object: Union[dict, list], values: list, key_to_extract: str) -> list:
            if isinstance(extracted_object, dict):
                for k, v in extracted_object.items():
                    if k == key_to_extract:
                        values.append(v)
                    elif isinstance(v, (dict, list)):
                        extract(v, values, key_to_extract)

            elif isinstance(extracted_object, list):
                for item in extracted_object:
                    extract(item, values, key_to_extract)
            return values

        results = extract(obj, arr, key)
        return results

    @staticmethod
    def get_arg_default(arg: dict):
        """
        Gets the format for an argument default value, e.g.:
        >>> , ''
        >>> , False
        Args:
            arg: The argument to get the default format for.

        Returns:
            argument_default: The default format for the argument.
        """
        arg_type = ARGUMENT_TYPES.get(arg.get('type', 'string'), 'str')
        arg_default = arg.get('default', '')
        default: Optional[Any]
        if arg_type == 'int':
            try:
                default = int(arg_default)
            except Exception:
                default = None
            argument_default = f', {default}'
        elif arg_type == 'bool':
            try:
                default = strtobool(arg_default)
            except Exception:
                default = False
            argument_default = f', {default}'
        else:
            argument_default = f", '{arg_default}'"

        return argument_default

    @staticmethod
    def clean_description(description: str) -> str:
        """
        Cleans a description string.
        Args:
            description: The description string to clean.

        Returns:
            description: The clean description.
        """
        if len(description) > MAX_DESCRIPTION_WORDS:
            description = description[:MAX_DESCRIPTION_WORDS] + '...'
        for i in ILLEGAL_DESCRIPTION_CHARS:
            description = description.replace(i, ' ')

        return description

    @staticmethod
    def clean_function_name(name: str, snakeify: bool = True) -> str:
        """
        Cleans a function name.
        Args:
            name: The function name to clean.
            snakeify: Whether to format the name to snake-case.

        Returns:
            name: The clean name.
        """
        for i in ILLEGAL_CODE_CHARS:
            name = name.replace(i, '')

        if snakeify:
            name = camel_to_snake(name)
            name = name.replace('-', '_').replace('__', '_').strip('_')

        return name

    @staticmethod
    def format_params(params: list, base: str, base_string: str) -> str:
        """
        Formats a list of params to a string of params assignment, e.g. param1=param_name, param2=param_name2
        Args:
            params: A list of params with mapping of name to code name
            base: The base code to use
            base_string: The base string to replace with the params

        Returns:
            params: Formatted params string
        """
        modified_params = []
        for p in params:
            for name, code_name in p.items():
                modified_params.append(f'{name}={code_name}')

        params_string = base.replace(base_string, ', '.join(modified_params))
        return params_string

    def handle_duplicates(self, functions: List):
        """
        Find duplicates command names and update the names according to path
        Args:
            functions: the list of functions
        """
        duplicate_names = [d['name'] for d in functions]
        duplicate_names = [n for n in duplicate_names if duplicate_names.count(n) > 1]
        if duplicate_names:
            for func in functions:
                name = func.get('name')
                if name in duplicate_names:
                    path = func.get('path')
                    method = func.get('method')
                    # getting the last curly brackets is exists and keeping its value
                    function_path = re.sub(r'{([\w]*)\}$', r'by/\g<1>', path)
                    # Remove the rest curly brackets from the path.
                    path_name = '_'.join([re.sub(r'{[^)]*\}', '', x) for x in function_path.split('/')])
                    name = self.clean_function_name(path_name)
                    func['name'] = f'{method}_{name}'
