import json
import os
import re
import shutil
import sys
from distutils.util import strtobool

import autopep8
import yaml
from demisto_sdk.commands.common.tools import print_error
from demisto_sdk.commands.openapi_codegen.base_code import (
    base_argument, base_basic_auth, base_client, base_code, base_credentials,
    base_data, base_function, base_header, base_list_functions, base_params,
    base_props, base_request_function, base_token)
from demisto_sdk.commands.openapi_codegen.XSOARIntegration import \
    XSOARIntegration

camel_to_snake_pattern = re.compile(r'(?<!^)(?=[A-Z][a-z])')
illegal_description_chars = ['\n', '<br>', '*', '\r', '\t', '<para/>', '«', '»']
illegal_func_chars = illegal_description_chars + [' ', ',', '(', ')', '`', ':', "'", '"', '[', ']']
illegal_function_names = ['type', 'from', 'id', 'file']
prepend_illegal = '_'
output_types = {
    'string': 'String',
    'integer': 'Number',
    'object': 'Unknown',
    'array': 'Unknown',
    'boolean': 'Boolean',
}
arg_types = {
    'string': 'str',
    'integer': 'int',
    'boolean': 'bool',
    'file': 'str',
    'int': 'int',
    'str': 'str',
}
removed_names = ['.properties', '.items']
JSON_TYPE_HEADER = 'application/json'
DEFAULT_HOST = 'https://www.example.com/api'
API_KEY_AUTH_TYPE = 'apiKey'
CREDENTIALS_AUTH_TYPE = 'basic'


class OpenAPIIntegration:
    def __init__(self, file_path, base_name, command_prefix, context_path,
                 verbose=False, fix_code=False, configuration=None):
        self.json = None
        self.baseName = base_name
        self.filter_commands = False
        self.include_commands = []
        self.command_prefix = command_prefix
        self.context_path = context_path
        self.configuration = configuration
        self.file_load = False
        self.swagger = None
        self.openapi = None
        self.security_definitions = None
        self.host = None
        self.base_path = None
        self.schemes = None
        self.name = None
        self.description = None
        self.script = None
        self.definitions = None
        self.components = None
        self.functions = []
        self.parameters = []
        self.verbose = verbose
        self.fix_code = fix_code
        self.load_file(file_path)

    def extract_values(self, obj, key):
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

    def extract_outputs(self, obj, context):
        arr = []

        def extract(obj, arr, context):

            if isinstance(obj, list):
                for item in obj:
                    extract(item, arr, context)

            elif isinstance(obj, dict):
                if obj.get('type') and type(obj.get('type')) == str:
                    if obj.get('type') in ['array', 'object']:
                        if obj.get('items'):
                            for k, v in obj.get('items', {}).items():
                                arr = extract(v, arr, context)
                        elif obj.get('properties'):
                            arr = extract(
                                obj.get('properties', {}), arr, context)
                        elif obj.get('allOf'):
                            for item in obj.get('allOf', []):
                                arr = extract(item, arr, context)
                    else:
                        arr.append({'name': '.'.join(context), 'type': obj.get('type', 'Unknown'),
                                    'description': obj.get('description', '')})

                elif obj.get('type') and type(obj.get('type')) == dict:
                    for k, v in obj.items():
                        context.append(k)
                        arr = extract(v, arr, context)
                        context.pop()

                else:
                    for k, v in obj.items():
                        context.append(k)
                        arr = extract(v, arr, context)
                        context.pop()

            return arr

        results = extract(obj, arr, context)
        return results

    def add_function(self, path, method, data, params):
        new_function = {}
        new_function['path'] = '/'.join(x.split(' ')[0] for x in path.split('/')).strip('/')
        new_function['method'] = method
        name = data.get('operationId', None)
        if not name:
            try:
                name = data.get('summary', None)
                name = name.replace(" ", "-")
            except Exception:
                name = None
        if not name:
            name = '_'.join([re.sub(r'\{[^)]*\}', '', x) for x in path.split('/')])
        name = self.clean_function_name(name)
        new_function['name'] = name
        func_desc = data.get('summary', None)
        if not func_desc:
            func_desc = data.get('description', '')
        func_desc = self.clean_description(func_desc)
        new_function['description'] = func_desc
        new_function['execution'] = False
        new_function['arguments'] = []
        new_function['parameters'] = data.get('parameters', None)
        new_function['consumes'] = data.get('consumes', [])
        new_function['produces'] = data.get('produces', [])
        if not new_function['parameters']:
            new_function['parameters'] = params
            iter_item = params
        else:
            iter_item = data.get('parameters', [])
        for arg in iter_item:
            refs = []
            if 'schema' in arg:
                refs = self.extract_values(arg['schema'], '$ref')
                for ref in refs:
                    ref = ref.split('/')[-1]
                    ref_args = []
                    context = {}
                    if self.definitions:
                        ref_args = self.extract_values(self.definitions.get(ref, {}), 'properties')
                        context = self.definitions
                    elif self.components:
                        ref_args = self.extract_values(self.components.get('schemas', {}).get(ref, {}), 'properties')
                        context = self.components.get('schemas', {})
                    for ref_arg in ref_args:
                        for k, v in ref_arg.items():
                            new_ref_arg = {'name': k, 'in': arg.get('in')}
                            new_ref_arg['required'] = True if k in context[ref].get('required', []) else False
                            if '$ref' in ref_arg[k]:
                                new_ref_arg['properties'] = {}
                                c_ref = ref_arg[k]['$ref'].split('/')[-1]
                                complex_refs = self.extract_values(context.get(c_ref, {}), 'properties')
                                for complex_ref in complex_refs:
                                    for ck, cv in complex_ref.items():
                                        new_ref_arg['properties'][ck] = {}
                                        new_ref_arg['properties'][ck]['type'] = cv.get('type', 'string')
                                        new_ref_arg['properties'][ck]['description'] = cv.get('description', '')
                                        new_ref_arg['properties'][ck]['required'] = True \
                                            if ck in context.get(c_ref, {}).get('required', []) else False
                                        new_ref_arg['properties'][ck]['options'] = [str(x) for x in cv.get('enum')]\
                                            if arg.get('enum', None) else None
                            else:
                                new_ref_arg.update(v)
                            new_ref_arg['ref'] = ref
                            new_function['arguments'].append(self.init_arg(new_ref_arg))
            if not refs:
                if arg.get('schema', {}).get('type'):
                    arg['type'] = arg['schema']['type']
                new_function['arguments'].append(self.init_arg(arg))
        new_function['outputs'] = []
        new_function['responses'] = []
        for response_code, response in data.get('responses', {}).items():
            new_response = {}
            try:
                if int(response_code) != 200:
                    continue
            except Exception:
                pass

            new_response['description'] = response.get('description', None)
            all_items = []
            schemas = self.extract_values(response, 'schema')
            if schemas:
                schema = schemas[0]
                refs = self.extract_values(schema, '$ref')
                if refs:
                    for ref in refs:
                        ref = ref.split('/')[-1]
                        if self.definitions:
                            all_items.extend(self.extract_values(self.definitions.get(ref, {}), 'properties'))
                        elif self.components:
                            all_items.extend(self.extract_values(self.components.get('schemas', {}).get(ref, {}),
                                                                 'properties'))
                        new_function['context_path'] = self.clean_function_name(ref, False)
                else:
                    all_items.extend(self.extract_values(schema, 'properties'))
                data = self.extract_outputs(all_items, [])
                for v in data:
                    description = v.get('description', '')
                    this_type = v.get('type', 'object')
                    this_type = output_types.get(this_type)
                    resp_name = v.get('name')
                    description = self.clean_description(description)
                    new_function['outputs'].append({'name': resp_name, 'type': this_type, 'description': description})
            new_function['responses'].append(new_response)

        self.functions.append(new_function)
        self.functions = sorted(self.functions, key=lambda x: x['name'])

    def load_file(self, file_path):
        error = None
        try:
            self.json = json.load(open(file_path, 'rb'))
            self.file_load = True
        except Exception as err:
            error = err
        if not self.file_load:
            try:
                stream = open(file_path, 'rb')
                self.json = yaml.safe_load(stream)
                self.file_load = True
            except Exception as err:
                error = err
        if not self.file_load:
            print_error(f'Failed to load the swagger file: {error}')
            sys.exit(1)

        self.swagger = str(self.json.get('swagger', None))
        self.openapi = str(self.json.get('openapi', None))
        if self.json.get('host', None):
            self.host = self.json.get('host', None)
        elif self.json.get('servers', None):
            self.host = self.json.get('servers', [])[0]['url']
        else:
            self.host = ''
        self.base_path = self.json.get('basePath', '')
        self.name = self.json['info']['title']
        self.description = self.json.get('info', {}).get('description', '')
        self.schemes = self.json.get('schemes', [])
        self.definitions = self.json.get('definitions', {})
        self.components = self.json.get('components', {})
        self.security_definitions = self.json.get('securityDefinitions', {})
        self.functions = []
        if not self.command_prefix:
            self.command_prefix = '-'.join(self.name.split(' ')).lower()

        for path, function in self.json['paths'].items():
            try:
                for method, data in function.items():
                    self.print_with_verbose(f'Adding command for the path: {path}')
                    self.add_function(path, method, data, function.get(
                        'parameters', []))
            except Exception as e:
                print_error(f'Failed adding the command for the path {path}: {e}')

        if not self.configuration:
            self.generate_configuration()

    def generate_configuration(self):
        security_types = []
        if self.security_definitions:
            all_security_types = [s.get('type') for s in self.security_definitions.values()]
            security_types = [t for t in all_security_types if t in [API_KEY_AUTH_TYPE, CREDENTIALS_AUTH_TYPE]]
        if not security_types:
            security_types = [API_KEY_AUTH_TYPE]

        configuration = {
            'swagger_id': self.name,
            'name': self.name or 'GeneratedIntegration',
            'description': self.description or 'This integration was auto generated by the Cortex XSOAR SDK.',
            'category': 'Utilities',
            'url': self.host or DEFAULT_HOST,
            'auth': security_types,
            'fetch_incidents': False,
            'context_path': self.context_path or self.name,
            'commands': []
        }
        for function in self.functions:
            command = {
                'name': function['name'].replace('_', '-'),
                'path': function['path'],
                'method': function['method'],
                'description': function['description'],
                'unique_key': '',
                'arguments': [],
                'outputs': [],
                'context_path': function.get('context_path', '')
            }
            headers = []
            if function['consumes']:
                headers.append({'Content-Type': JSON_TYPE_HEADER
                                if JSON_TYPE_HEADER in function['consumes'] else function['consumes'][0]})
            if function['produces']:
                headers.append({'Accept': JSON_TYPE_HEADER
                                if JSON_TYPE_HEADER in function['produces'] else function['produces'][0]})

            command['headers'] = headers
            for arg in function['arguments']:
                command['arguments'].append({
                    'name': str(arg.get('name', '')),
                    'description': self.clean_description(arg.get('description', '')),
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

            configuration['commands'].append(command)

        configuration['code_type'] = 'python'
        configuration['code_subtype'] = 'python3'
        configuration['docker_image'] = 'demisto/python3:3.8.3.9324'

        self.configuration = configuration

    def get_python_code(self):
        # Use the code from baseCode in py as the basis
        data = base_code

        # Build the functions from configuration file
        functions = []
        req_functions = []
        for command in self.configuration['commands']:
            function, req_function = self.get_command_functions(command)
            functions.append(function)
            req_functions.append(req_function)

        data = data.replace('$FUNCTIONS$', '\n'.join(functions))
        data = data.replace('$BASEURL$', self.base_path)
        client = base_client.replace('$REQUESTFUNCS$', '\n'.join(req_functions))
        data = data.replace('$CLIENT$', client)

        if API_KEY_AUTH_TYPE in self.configuration['auth']:
            data = data.replace('$BEARERAUTHPARAMS$', base_token)
        else:
            data = data.replace('$BEARERAUTHPARAMS$', '')

        if CREDENTIALS_AUTH_TYPE in self.configuration['auth']:
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

    def get_command_functions(self, command):
        function_name = command['name'].replace('-', '_')
        self.print_with_verbose(f'Adding the function {function_name} to the code...')
        function = base_function.replace('$FUNCTIONNAME$', function_name)
        req_function = base_request_function.replace('$FUNCTIONNAME$', function_name)
        new_params = []
        new_data = []
        arguments = []
        argument_names = []
        arguments_found = False
        headers = command['headers']
        for arg in command['arguments']:
            arguments_found = True
            code_arg_name = arg['name']
            ref_arg_name = arg['name']
            arg_type = arg.get('type')
            arg_props = []
            if arg.get('ref'):
                ref_arg_name = f'{arg["ref"]}_{ref_arg_name}'.lower()
                code_arg_name = f'{arg["ref"]}_{code_arg_name}'.lower()
            if code_arg_name in illegal_function_names:
                code_arg_name = f'{code_arg_name}{prepend_illegal}'
            if arg['properties']:
                for k, v in arg['properties'].items():
                    prop_default = self.get_arg_default(v)
                    prop_arg_name = f'{code_arg_name}_{k}'.lower()
                    prop_arg_type = arg_types.get(v.get('type', 'string'), 'str')
                    if prop_arg_type == 'bool':
                        prop_arg_type = 'argToBoolean'
                    if prop_arg_name in illegal_function_names:
                        prop_arg_name = f'{prop_arg_name}{prepend_illegal}'
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
                    new_arg_type = arg_types.get(arg['type'], 'str')
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
                new_params.append({
                    arg['name']: ref_arg_name
                })
            elif arg['in'] in ['formData', 'body']:
                new_data.append({
                    arg['name']: ref_arg_name
                })
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
            if param in illegal_function_names:
                command['path'] = command['path'].replace(param, f'{param}{prepend_illegal}')
        req_function = req_function.replace('$PATH$', command['path'])
        if new_params:
            params = self.format_params(new_params, base_params, '$PARAMS$')
            req_function = req_function.replace('$PARAMETERS$', params)
        else:
            req_function = '\n'.join(
                [x for x in req_function.split('\n') if '$PARAMETERS$' not in x])
        if new_data:
            new_data = self.format_params(new_data, base_data, '$DATAOBJ$')
            req_function = req_function.replace('$DATA$', new_data)
        else:
            req_function = '\n'.join(
                [x for x in req_function.split('\n') if '$DATA$' not in x])
        if new_params:
            req_function = req_function.replace(
                '$NEWPARAMS$', ', params=params')
        else:
            req_function = req_function.replace('$NEWPARAMS$', '')
        if new_data:
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
        if 'context_path' in command and command['context_path']:
            function = function.replace('$CONTEXTPATH$', f'.{command["context_path"]}')
        else:
            function = function.replace('$CONTEXTPATH$', '')
        if command['unique_key']:
            function = function.replace('$UNIQUEKEY$', command['unique_key'])
        else:
            function = function.replace('$UNIQUEKEY$', '')
        function = function.replace('$CONTEXTNAME$', context_name)
        return function, req_function

    def get_yaml(self, no_code):
        # Create the commands section
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
                description = arg.get('description', None)
                is_array = True if arg['type'] == 'array' else False
                if description:
                    description = self.clean_description(description)
                else:
                    description = ''
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

        script = ''
        if not no_code:
            script = self.get_python_code()

        commonfields = XSOARIntegration.CommonFields(self.configuration['name'], -1)
        name = self.configuration['name']
        display = self.configuration['name']
        category = self.configuration['category']
        description = self.configuration['description']
        url = self.configuration['url']
        configurations = [XSOARIntegration.Configuration(display=f'Server URL (e.g. {url})',
                                                         name='url',
                                                         defaultvalue=url,
                                                         type_=0,
                                                         required=True)]
        if not isinstance(self.configuration['auth'], list):
            self.configuration['auth'] = [self.configuration['auth']]

        if API_KEY_AUTH_TYPE in self.configuration['auth']:
            configurations.append(XSOARIntegration.Configuration(display='API Key',
                                                                 name='api_key',
                                                                 required=True,
                                                                 type_=4))
        if CREDENTIALS_AUTH_TYPE in self.configuration['auth']:
            configurations.append(XSOARIntegration.Configuration(display='Username',
                                                                 name='credentials',
                                                                 required=True,
                                                                 type_=9))
        if self.configuration['fetch_incidents']:
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

        int_script = XSOARIntegration.Script(script, self.configuration['code_type'],
                                             self.configuration['code_subtype'], self.configuration['docker_image'],
                                             self.configuration['fetch_incidents'], commands)

        integration = XSOARIntegration(commonfields, name, display, category, description, configuration=configurations,
                                       script=int_script)
        return integration

    def save_python_code(self, directory):
        self.print_with_verbose('Creating python file...')
        filename = os.path.join(directory, f'{self.baseName}.py')
        try:
            with open(filename, 'w') as fp:
                fp.write(self.get_python_code())
                return filename
        except Exception as err:
            print(f'Error writing {filename} - {err}')
            raise

    def save_yaml(self, directory, no_code=False):
        self.print_with_verbose('Creating yaml file...')
        filename = os.path.join(directory, f'{self.baseName}.yml')
        try:
            with open(filename, 'w') as fp:
                fp.write(yaml.dump(self.get_yaml(no_code).to_yaml()))
            return filename
        except Exception as err:
            print(f'Error writing {filename} - {err}')
            raise

    def save_config(self, config, directory):
        self.print_with_verbose('Creating configuration file...')
        filename = os.path.join(directory, f'{self.baseName}.json')
        try:
            with open(filename, 'w') as fp:
                json.dump(config, fp)
            return filename
        except Exception as err:
            print(f'Error writing {filename} - {err}')
            raise

    def print_with_verbose(self, text):
        if self.verbose:
            print(text)

    def save_image_and_desc(self, directory):
        self.print_with_verbose('Creating image and description files...')
        image_path = os.path.join(directory, f'{self.baseName}_image.png')
        desc_path = os.path.join(directory, f'{self.baseName}_description.md')
        try:
            shutil.copy(os.path.join(os.path.dirname(__file__), 'Generated_image.png'), image_path)
            shutil.copy(os.path.join(os.path.dirname(__file__), 'Generated_description.md'), desc_path)
            return image_path, desc_path
        except Exception as err:
            print(f'Error copying image and description files - {err}')

    def save_package(self, directory):
        code_path = self.save_python_code(directory)
        yml_path = self.save_yaml(directory, no_code=True)
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
    def get_arg_default(arg):
        arg_type = arg_types.get(arg.get('type', 'string'), 'str')
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
        for i in illegal_description_chars:
            description = description.replace(i, ' ')
        return description

    @staticmethod
    def clean_function_name(name, snakeify=True):
        for i in illegal_func_chars:
            name = name.replace(i, '')

        if snakeify:
            name = OpenAPIIntegration.camel_to_snake(name)
            name = name.replace('-', '_').replace('__', '_').strip('_')

        return name

    @staticmethod
    def format_params(params, base, base_string):
        modified_params = []
        for p in params:
            for name, code_name in p.items():
                # modified_params.append(f'\"{name}\"={code_name}')
                modified_params.append(f'{name}={code_name}')
        params = base.replace(base_string, ', '.join(modified_params))
        return params

    @staticmethod
    def camel_to_snake(camel):
        snake = camel_to_snake_pattern.sub('_', camel).lower()
        return snake
