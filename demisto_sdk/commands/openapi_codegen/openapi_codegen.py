import json
import os
import re
import shutil
import sys
from distutils.util import strtobool

import autopep8
import yaml

from demisto_sdk.commands.common.tools import camel_to_snake, print_error
from demisto_sdk.commands.openapi_codegen.base_code import (
    base_argument, base_basic_auth, base_client, base_code, base_credentials,
    base_data, base_function, base_header, base_list_functions, base_params,
    base_props, base_request_function, base_token)
from demisto_sdk.commands.openapi_codegen.XSOARIntegration import \
    XSOARIntegration

ILLEGAL_DESCRIPTION_CHARS = ['\n', 'br', '*', '\r', '\t', 'para', 'span', '«', '»', '<', '>']
ILLEGAL_CODE_CHARS = ILLEGAL_DESCRIPTION_CHARS + [' ', ',', '(', ')', '`', ':', "'", '"', '[', ']']
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
DEFAULT_HOST = 'https://www.example.com/api'
BEARER_AUTH_TYPE = 'apiKey'
BASIC_AUTH_TYPE = 'basic'
MAX_DESCRIPTION_WORDS = 3000


class OpenAPIIntegration:
    def __init__(self, file_path, base_name, command_prefix, context_path, unique_keys=None, root_objects=None,
                 verbose=False, fix_code=False, configuration=None):
        self.json = None
        self.file_path = file_path
        self.base_name = base_name
        self.command_prefix = command_prefix
        self.context_path = context_path
        self.unique_keys = unique_keys.split(',') if unique_keys is not None else []
        self.root_objects = root_objects.split(',') if root_objects is not None else []
        self.configuration = configuration
        self.security_definitions = None
        self.host = None
        self.base_path = None
        self.name = None
        self.description = None
        self.definitions = None
        self.components = None
        self.reference = None
        self.functions = []
        self.parameters = []
        self.verbose = verbose
        self.fix_code = fix_code

    def extract_properties(self, obj, context):
        arr = []

        def extract(extracted_object, prop_arr, current_context):

            if isinstance(extracted_object, list):
                for item in extracted_object:
                    extract(item, prop_arr, current_context)

            elif isinstance(extracted_object, dict):
                if extracted_object.get('type') and type(extracted_object.get('type')) == str:
                    if extracted_object.get('type') in ['array', 'object']:
                        refs = self.extract_values(extracted_object, '$ref')
                        if refs:
                            ref = refs[0].split('/')[-1]
                            prop_arr = extract(self.extract_values(self.reference[ref], 'properties'), prop_arr,
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

    def extract_outputs(self, data, new_function):
        for response_code, response in data.get('responses', {}).items():
            new_response = {}
            try:
                if int(response_code) != 200:
                    continue
            except Exception:
                self.print_with_verbose(f'Could not get the code for the response {response}')
                pass

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
                        if ref_props:
                            for k, prop in ref_props[0].items():
                                if k in self.root_objects:
                                    # We found a root, we need the output of the root only
                                    new_function['root_object'] = k
                                    all_items = [prop]
                                    path = self.extract_values(prop, '$ref')
                                    if path:
                                        new_function['context_path'] = self.clean_function_name(path[0].split('/')[-1],
                                                                                                False)
                                    found_root = True
                            if found_root:
                                break

                            all_items.extend(ref_props)
                        if not new_function.get('context_path'):
                            new_function['context_path'] = self.clean_function_name(ref, False)
                else:
                    all_items.extend(self.extract_values(schema, 'properties'))

                properties = self.extract_properties(all_items, [])
                for prop in properties:
                    description = prop.get('description', '')
                    this_type = prop.get('type', 'object')
                    this_type = OUTPUT_TYPES.get(this_type, 'Unknown')
                    resp_name = prop.get('name')
                    description = self.clean_description(description)
                    new_function['outputs'].append({'name': resp_name, 'type': this_type, 'description': description})
            new_function['responses'].append(new_response)

    def extract_args(self, arguments, new_function):
        for arg in arguments:
            refs = []
            if 'schema' in arg:
                refs = self.extract_values(arg['schema'], '$ref')
                for ref in refs:
                    ref = ref.split('/')[-1]
                    ref_args = self.extract_values(self.reference.get(ref, {}), 'properties')
                    for ref_arg in ref_args:
                        for k, v in ref_arg.items():
                            new_ref_arg = {'name': k, 'in': arg.get('in'),
                                           'required': True if k in self.reference[ref].get('required', []) else False}
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
                            new_function['arguments'].append(self.init_arg(new_ref_arg))
            if not refs:
                if arg.get('schema', {}).get('type'):
                    arg['type'] = arg['schema']['type']
                new_function['arguments'].append(self.init_arg(arg))

    def add_function(self, path, method, data, params):
        new_function = {'path': '/'.join(x.split(' ')[0] for x in path.split('/')).strip('/'), 'method': method}
        name = data.get('operationId', None)
        if not name:
            name = data.get('summary', '').lower()
            name = name.replace(' ', '-')
        if not name:
            name = '_'.join([re.sub(r'\{[^)]*\}', '', x) for x in path.split('/')])
        name = self.clean_function_name(name)
        new_function['name'] = name
        func_desc = data.get('summary', None)
        if not func_desc:
            func_desc = data.get('description', '')
        func_desc = self.clean_description(func_desc)
        new_function['description'] = func_desc
        new_function['arguments'] = []
        new_function['parameters'] = data.get('parameters', None)
        new_function['consumes'] = data.get('consumes', [])
        new_function['produces'] = data.get('produces', [])
        new_function['outputs'] = []
        new_function['responses'] = []
        if not new_function['parameters']:
            new_function['parameters'] = params
            iter_item = params
        else:
            iter_item = data.get('parameters', [])
        self.extract_args(iter_item, new_function)
        self.extract_outputs(data, new_function)

        self.functions.append(new_function)

    def load_file(self):
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
        self.reference = self.definitions or self.components.get('schemas', {})
        self.security_definitions = self.json.get('securityDefinitions', {})
        self.functions = []

        for path, function in self.json['paths'].items():
            try:
                for method, data in function.items():
                    if isinstance(data, list):
                        data = data[0]
                    self.print_with_verbose(f'Adding command for the path: {path}')
                    self.add_function(path, method, data, function.get(
                        'parameters', []))
            except Exception as e:
                print_error(f'Failed adding the command for the path {path}: {e}')
                raise

        self.functions = sorted(self.functions, key=lambda x: x['name'])
        if not self.configuration:
            self.generate_configuration()

    def generate_configuration(self):
        security_types = []
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
            if function['consumes'] and JSON_TYPE_HEADER not in function['consumes']:
                headers.append({'Content-Type': function['consumes'][0]})

            if function['produces'] and JSON_TYPE_HEADER not in function['produces']:
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

            configuration['commands'].append(command)

        configuration['code_type'] = 'python'
        configuration['code_subtype'] = 'python3'
        # TODO: get latest docker image
        configuration['docker_image'] = 'demisto/python3:3.8.3.9324'

        self.configuration = configuration

    def get_python_code(self):
        # Use the code from baseCode in py as the basis
        data = base_code

        # Build the functions from configuration file
        functions = []
        req_functions = []
        for command in self.configuration['commands']:
            function, req_function = self.get_python_command_and_request_functions(command)
            functions.append(function)
            req_functions.append(req_function)

        data = data.replace('$FUNCTIONS$', '\n'.join(functions))
        data = data.replace('$BASEURL$', self.base_path)
        client = base_client.replace('$REQUESTFUNCS$', '\n'.join(req_functions))
        data = data.replace('$CLIENT$', client)

        if BEARER_AUTH_TYPE in self.configuration['auth']:
            data = data.replace('$BEARERAUTHPARAMS$', base_token)
        else:
            data = data.replace('$BEARERAUTHPARAMS$', '')

        if BASIC_AUTH_TYPE in self.configuration['auth']:
            data = data.replace('$BASEAUTHPARAMS$', base_credentials)
            data = data.replace('$BASEAUTH$', base_basic_auth)
        else:
            data = data.replace('$BASEAUTHPARAMS$', '')
            data = data.replace('$BASEAUTH$', 'None')

        list_functions = []

        # Add the command mappings:
        for command in self.functions:
            prefix = ''
            if self.command_prefix:
                prefix = f'{self.command_prefix}-'

            function = base_list_functions.replace(
                '$FUNCTIONNAME$', f"{prefix}{command['name']}".replace('_', '-'))
            fn = command['name'].replace('-', '_')
            function = function.replace('$FUNCTIONCOMMAND$', f'{fn}_command')
            list_functions.append(function)

        data = data.replace('$COMMANDSLIST$', '\n\t'.join(list_functions))
        self.print_with_verbose('Finished creating the python code.')

        if self.fix_code:
            self.print_with_verbose('Fixing the code with autopep8...')
            data = autopep8.fix_code(data)

        return data

    def get_python_command_and_request_functions(self, command):
        function_name = command['name'].replace('-', '_')
        headers = command['headers']
        self.print_with_verbose(f'Adding the function {function_name} to the code...')
        function = base_function.replace('$FUNCTIONNAME$', function_name)
        req_function = base_request_function.replace('$FUNCTIONNAME$', function_name)
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
            params = self.format_params(params_data, base_params, '$PARAMS$')
            req_function = req_function.replace('$PARAMETERS$', params)
        else:
            req_function = '\n'.join(
                [x for x in req_function.split('\n') if '$PARAMETERS$' not in x])
        if body_data:
            body_data = self.format_params(body_data, base_data, '$DATAOBJ$')
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
                    new_headers.append(base_header.replace('$HEADERKEY$', f"'{k}'")
                                       .replace('$HEADERVALUE$', f"'{v}'"))

            req_function = req_function.replace('$HEADERSOBJ$', ' \n        '.join(new_headers))
        else:
            req_function = req_function.replace('$HEADERSOBJ$', '')
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
                    this_prop_argument = f"{base_argument.replace('$DARGNAME$', prop_arg_name)}{prop_default})"
                    this_prop_argument = this_prop_argument.replace('$SARGNAME$', prop_arg_name)
                    if 'None' not in prop_default:
                        this_prop_argument = this_prop_argument.replace('$ARGTYPE$', f'{prop_arg_type}(') + ')'
                    else:
                        this_prop_argument = this_prop_argument.replace('$ARGTYPE$', '')
                    arg_props.append({k: prop_arg_name})
                    arguments.append(this_prop_argument)
                all_props = self.format_params(arg_props, base_props, '$PROPS$')
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

                this_argument = f"{base_argument.replace('$DARGNAME$', ref_arg_name)}{argument_default})"
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

    def get_yaml(self):
        # Create the commands section
        commands = self.get_yaml_commands()
        script = self.get_python_code()
        commonfields = XSOARIntegration.CommonFields(self.configuration['name'], -1)
        name = self.configuration['name']
        display = self.configuration['name']
        category = self.configuration['category']
        description = self.configuration['description']
        configurations = self.get_yaml_params()

        int_script = XSOARIntegration.Script(script, self.configuration['code_type'],
                                             self.configuration['code_subtype'], self.configuration['docker_image'],
                                             self.configuration.get('fetch_incidents', False), commands)

        integration = XSOARIntegration(commonfields, name, display, category, description, configuration=configurations,
                                       script=int_script)
        return integration

    def get_yaml_params(self) -> list:
        url = self.configuration['url']
        configurations = [XSOARIntegration.Configuration(display=f'Server URL (e.g. {url})',
                                                         name='url',
                                                         defaultvalue=url,
                                                         type_=0,
                                                         required=True)]
        if not isinstance(self.configuration['auth'], list):
            self.configuration['auth'] = [self.configuration['auth']]
        if BEARER_AUTH_TYPE in self.configuration['auth']:
            configurations.append(XSOARIntegration.Configuration(display='API Key',
                                                                 name='api_key',
                                                                 required=True,
                                                                 type_=4))
        if BASIC_AUTH_TYPE in self.configuration['auth']:
            configurations.append(XSOARIntegration.Configuration(display='Username',
                                                                 name='credentials',
                                                                 required=True,
                                                                 type_=9))
        if self.configuration.get('fetch_incidents', False):
            configurations.extend([
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
                XSOARIntegration.Configuration(display='API Key',
                                               name='apikey',
                                               type_=4,
                                               required=True),
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
        configurations.extend([XSOARIntegration.Configuration(display='Trust any certificate (not secure)',
                                                              name='insecure',
                                                              type_=8,
                                                              required=False),
                               XSOARIntegration.Configuration(display='Use system proxy settings',
                                                              name='proxy',
                                                              type_=8,
                                                              required=False)])
        return configurations

    def get_yaml_commands(self) -> list:
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

    def save_python_code(self, directory):
        self.print_with_verbose('Creating python file...')
        filename = os.path.join(directory, f'{self.base_name}.py')
        try:
            with open(filename, 'w') as fp:
                fp.write(self.get_python_code())
                return filename
        except Exception as err:
            print_error(f'Error writing {filename} - {err}')
            raise

    def save_yaml(self, directory):
        self.print_with_verbose('Creating yaml file...')
        filename = os.path.join(directory, f'{self.base_name}.yml')
        try:
            with open(filename, 'w') as fp:
                fp.write(yaml.dump(self.get_yaml().to_yaml()))
            return filename
        except Exception as err:
            print_error(f'Error writing {filename} - {err}')
            raise

    def save_config(self, config, directory):
        self.print_with_verbose('Creating configuration file...')
        filename = os.path.join(directory, f'{self.base_name}.json')
        try:
            with open(filename, 'w') as fp:
                json.dump(config, fp, indent=4)
            return filename
        except Exception as err:
            print_error(f'Error writing {filename} - {err}')
            raise

    def print_with_verbose(self, text):
        if self.verbose:
            print(text)

    def save_image_and_desc(self, directory):
        self.print_with_verbose('Creating image and description files...')
        image_path = os.path.join(directory, f'{self.base_name}_image.png')
        desc_path = os.path.join(directory, f'{self.base_name}_description.md')
        try:
            shutil.copy(os.path.join(os.path.dirname(__file__), 'resources', 'Generated_image.png'), image_path)
            shutil.copy(os.path.join(os.path.dirname(__file__), 'resources', 'Generated_description.md'), desc_path)
            return image_path, desc_path
        except Exception as err:
            print_error(f'Error copying image and description files - {err}')

    def save_package(self, directory):
        code_path = self.save_python_code(directory)
        yml_path = self.save_yaml(directory)
        image_path, desc_path = self.save_image_and_desc(directory)
        return code_path, yml_path, image_path, desc_path

    def init_arg(self, arg):
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
        new_arg['enums'] = [str(x) for x in arg.get('enum')] if arg.get('enum', None) else None

        return new_arg

    @staticmethod
    def extract_values(obj, key):
        arr = []

        def extract(obj, arr, key):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == key:
                        arr.append(v)
                    elif isinstance(v, (dict, list)):
                        extract(v, arr, key)

            elif isinstance(obj, list):
                for item in obj:
                    extract(item, arr, key)
            return arr

        results = extract(obj, arr, key)
        return results

    @staticmethod
    def get_arg_default(arg):
        arg_type = ARGUMENT_TYPES.get(arg.get('type', 'string'), 'str')
        arg_default = arg.get('default', '')
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
    def clean_description(description):
        if len(description) > MAX_DESCRIPTION_WORDS:
            description = description[:MAX_DESCRIPTION_WORDS] + '...'
        for i in ILLEGAL_DESCRIPTION_CHARS:
            description = description.replace(i, ' ')

        return description

    @staticmethod
    def clean_function_name(name, snakeify=True):
        for i in ILLEGAL_CODE_CHARS:
            name = name.replace(i, '')

        if snakeify:
            name = camel_to_snake(name)
            name = name.replace('-', '_').replace('__', '_').strip('_')

        return name

    @staticmethod
    def format_params(params, base, base_string):
        modified_params = []
        for p in params:
            for name, code_name in p.items():
                modified_params.append(f'{name}={code_name}')
        params = base.replace(base_string, ', '.join(modified_params))
        return params
