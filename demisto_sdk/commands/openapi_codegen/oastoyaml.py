import argparse
import autopep8
import json
import os
import re
import shutil
import sys
import yaml

from distutils.util import strtobool
from demisto_sdk.commands.common.tools import print_error, print_success
from demisto_sdk.commands.openapi_codegen.base_code import (
    base_argument, base_code, base_function, base_list_functions, base_params, base_data, base_headers,
    base_credentials, base_token, base_basic_auth, base_client, base_request_function)
from demisto_sdk.commands.openapi_codegen.XSOARIntegration import XSOARIntegration

camel_to_snake_pattern = re.compile(r'(?<!^)(?=[A-Z][a-z])')
illegal_description_chars = ['\n', '<br>', '*', '\r', '\t', '<para/>']
illegal_func_chars = illegal_description_chars + [' ', ',', '(', ')', '`', ':', "'", '"', '[', ']']
illegal_function_names = ['type', 'from']
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
API_KEY_AUTH_TYPE = 'bearer'
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
            # ￿￿TODO: extract args from $ref?
            new_arg = {}
            arg_name = str(arg.get('name', ''))
            new_arg['name'] = arg_name
            arg_desc = arg.get('description', '')
            arg_desc = self.clean_description(arg_desc)
            new_arg['description'] = arg_desc
            new_arg['required'] = arg.get('required')
            new_arg['default'] = arg.get('default', '')
            new_arg['in'] = arg.get('in', None)
            new_arg['type'] = arg_types.get(arg.get('type', 'string'), 'str')
            new_arg['enums'] = [str(x) for x in arg.get('enum')] if arg.get('enum', None) else None
            new_function['arguments'].append(new_arg)
        new_function['outputs'] = []
        new_function['responses'] = []
        for response_code, response in data.get('responses', {}).items():
            new_response = {}
            new_response['code'] = response_code
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
                        new_function['context_path'] = ref
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
        self.functions = []
        if not self.command_prefix:
            self.command_prefix = '-'.join(self.name.split(' ')).lower()

        for path, function in self.json['paths'].items():
            # TODO: try except
            for method, data in function.items():
                print(f'Adding command for the path: {path}')
                self.add_function(path, method, data, function.get(
                    'parameters', []))
                print(f'Finished adding command for the path: {path}')

        if not self.configuration:
            self.generate_configuration()

    def generate_configuration(self):
        configuration = {
            'swagger_id': self.name,
            'name': self.name or 'GeneratedIntegration',
            'description': self.description or 'This integration was auto generated by the Cortex XSOAR SDK.',
            'category': 'Utilities',
            'url': self.host or DEFAULT_HOST,
            'auth': [API_KEY_AUTH_TYPE],
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
                    'type': arg_types.get(arg.get('type', 'string'), 'string'),
                    'options': [str(x) for x in arg.get('enum')] if arg.get('enum', None) else []
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
        configuration['run_once'] = False

        self.configuration = configuration

    def get_python_code(self):
        # Use the code from baseCode in py as the basis
        data = base_code

        # Build the functions from configuration file
        functions = []
        req_functions = []
        for command in self.configuration['commands']:
            function_name = command['name'].replace('-', '_')
            print(f'Adding the function {function_name} to the code...')
            function = base_function.replace('$FUNCTIONNAME$', function_name)
            req_function = base_request_function.replace('$FUNCTIONNAME$', function_name)

            new_params = [x['name'] for x in command['arguments'] if 'query' in x['in']]
            new_data = [x['name'] for x in command['arguments'] if x['in'] in ['formData', 'body']]
            arguments = []
            arguments_found = False
            headers = command['headers']

            for arg in command['arguments']:
                arguments_found = True
                argument_default = ''
                if not arg['required']:
                    if arg['type'] == 'int':
                        try:
                            default = int(arg['default'])
                        except Exception:
                            default = 0
                        argument_default = f', {default}'
                    elif arg['type'] == 'bool':
                        try:
                            default = strtobool(arg['default'])
                        except Exception:
                            default = False
                        argument_default = f', {default}'
                    else:
                        argument_default = f", '{arg['default']}'"
                this_argument = f"{base_argument.replace('$DARGNAME$', arg['name'])}{argument_default}))"
                new_arg_name = arg['name']
                if new_arg_name in illegal_function_names:
                    new_arg_name = f'{prepend_illegal}{new_arg_name}'
                this_argument = this_argument.replace('$SARGNAME$', new_arg_name)
                this_argument = this_argument.replace('$ARGTYPE$', arg['type'])

                arguments.append(this_argument)

            if arguments_found:
                function = function.replace('$ARGUMENTS$', '\n    '.join(arguments))
            else:
                function = '\n'.join(
                    [x for x in function.split('\n') if '$ARGUMENTS$' not in x])

            if new_params:
                req_function = req_function.replace('$REQARGS1$', ', '.join(new_params))
                params = self.format_params(new_params, base_params, '$PARAMS$')
                req_function = req_function.replace('$PARAMETERS$', params)
            else:
                req_function = req_function.replace('$REQARGS1$', '')
                req_function = '\n'.join(
                    [x for x in req_function.split('\n') if '$PARAMETERS$' not in x])

            if new_data:
                if new_params:
                    req_function = req_function.replace('$REQARGS2$', ', $REQARGS2$')
                req_function = req_function.replace('$REQARGS2$', ', '.join(new_data))
                new_data = self.format_params(new_data, base_data, '$DATAOBJ$')
                req_function = req_function.replace('$DATA$', new_data)
            else:
                req_function = '\n'.join(
                    [x for x in req_function.split('\n') if '$DATA$' not in x])

            if headers:
                new_headers = ''
                for header in headers:
                    for k, v in header.items():
                        new_headers = f"{new_headers}'{k}':'{v}', "

                new_headers = new_headers[:-2]
                new_headers = base_headers.replace('$HEADERSOBJ$', new_headers)
            else:
                new_headers = ''

            req_function = req_function.replace('$HEADERS$', f', {new_headers}')
            req_function = req_function.replace('$METHOD$', command['method'])
            command['path'] = f"'{command['path']}'" if "'" not in command['path'] else command['path']
            command['path'] = f"f{command['path']}" if "{" in command['path'] else command['path']
            req_function = req_function.replace('$PATH$', command['path'])

            if new_params:
                req_function = req_function.replace(
                    '$NEWPARAMS$', ', params=params')
            else:
                req_function = req_function.replace('$NEWPARAMS$', '')
            if new_data:
                req_function = req_function.replace('$NEWDATA$', ', data=data')
            else:
                req_function = req_function.replace('$NEWDATA$', '')

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
            functions.append(function)
            req_functions.append(req_function)

        data = data.replace('$FUNCTIONS$', '\n'.join(functions))
        data = data.replace('$BASEURL$', self.base_path)
        client = base_client.replace(('$REQUESTFUNCS$', '\n'.join(req_functions)))
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
        print('Finished creating the python code.')

        if self.fix_code:
            print('Fixing the code with autopep8...')
            data = autopep8.fix_code(data)

        return data

    def get_yaml(self, no_code):
        # Create the commands section
        commands = []
        for command in self.configuration['commands']:
            args = []
            options = None
            auto = None
            for arg in command['arguments']:
                arg_name = arg['name']
                required = True if arg['required'] else False
                description = arg.get('description', None)
                if description:
                    description = self.clean_description(description)
                else:
                    description = ''

                if arg['options']:
                    auto = 'PREDEFINED'
                    options = arg['options']

                args.append(XSOARIntegration.Script.Command.Argument(arg_name, description, required, auto, options))

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
                                             self.configuration['fetch_incidents'], self.configuration['run_once'],
                                             commands)

        integration = XSOARIntegration(commonfields, name, display, category, description, configuration=configurations,
                                       script=int_script)
        return integration

    def save_python_code(self, directory):
        print('Creating python file...')
        filename = os.path.join(directory, f'{self.baseName}.py')
        try:
            with open(filename, 'w') as fp:
                fp.write(self.get_python_code())
                return filename
        except Exception as err:
            print(f'Error writing {filename} - {err}')
            raise

    def save_yaml(self, directory, no_code=False):
        print('Creating yaml file...')
        filename = os.path.join(directory, f'{self.baseName}.yml')
        try:
            with open(filename, 'w') as fp:
                fp.write(yaml.dump(self.get_yaml(no_code).to_yaml()))
            return filename
        except Exception as err:
            print(f'Error writing {filename} - {err}')
            raise

    def save_config(self, config, directory):
        print('Creating configuration file...')
        filename = os.path.join(directory, f'{self.baseName}.json')
        try:
            with open(filename, 'w') as fp:
                json.dump(config, fp)
            return filename
        except Exception as err:
            print(f'Error writing {filename} - {err}')
            raise

    def save_image_and_desc(self, directory):
        print('Creating image and description files...')
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

    @staticmethod
    def clean_description(description):
        for i in illegal_description_chars:
            description = description.replace(i, ' ')
        return description

    @staticmethod
    def clean_function_name(name):
        for i in illegal_func_chars:
            name = name.replace(i, '')

        name = camel_to_snake(name)
        name = name.replace('-', '_').replace('__', '_').strip('_')

        return name

    @staticmethod
    def format_params(new_params, base, base_string):
        modified_params = []
        for p in new_params:
            if p in illegal_function_names:
                modified_params.append(f'\"{p}\": {p}{prepend_illegal}')
            else:
                modified_params.append(f'\"{p}\": {p}')
        params = base.replace(base_string, ', '.join(modified_params))
        return params


def camel_to_snake(camel):
    snake = camel_to_snake_pattern.sub('_', camel).lower()
    return snake


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file', metavar='input_file',
                        help='The swagger file to load')
    parser.add_argument('-cf', '--config_file', metavar='config_file',
                        help='The integration configuration file')
    parser.add_argument('-n', '--base_name', metavar='base_name',
                        help='The base filename to use for the generated files')
    parser.add_argument('-p', '--output_package', action='store_true',
                        help='Output the integration as a package (separate code and yml files)')
    parser.add_argument('-o', '--output_dir', metavar='output_dir',
                        help='Directory to store the output to (default is current working directory)')
    parser.add_argument('-t', '--command_prefix', metavar='command_prefix',
                        help='Add an additional word to each commands text')
    parser.add_argument('-c', '--context_path', metavar='context_path',
                        help='Context output path')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Be verbose with the log output')
    parser.add_argument('-f', '--fix_code', action='store_true',
                        help='Fix the python code using autopep8.')
    parser.add_argument('-a', '--use_default', action='store_true',
                        help='Use the automatically generated integration configuration')

    args = parser.parse_args()

    if not args.output_dir:
        directory = os.getcwd()
    else:
        directory = args.output_dir

    # Check the directory exists and if not, try to create it
    if not os.path.exists(directory):
        try:
            os.mkdir(directory)
        except Exception as err:
            print(f'Error creating directory {directory} - {err}')
            sys.exit(1)
    if not os.path.isdir(directory):
        print(f'The directory provided "{directory}" is not a directory')
        sys.exit(1)

    configuration = None
    if args.config_file:
        try:
            with open(args.config_file, 'r') as config_file:
                configuration = json.load(config_file)
        except Exception as e:
            print_error(f'Failed to load configuration file: {e}')

    print('Processing swagger file...')
    integration = OpenAPIIntegration(args.input_file, args.base_name, args.command_prefix, args.context_path,
                                     verbose=args.verbose, fix_code=args.fix_code, configuration=configuration)

    if not args.config_file:
        integration.save_config(integration.configuration, directory)
        print_success(f'Created configuration file in {directory}')
        if not args.use_default:
            print('Run the command again with the created configuration file.')
            sys.exit(0)

    if args.output_package:
        if integration.save_package(directory):
            print_success(f'Created package in {directory}')
        else:
            print_error(f'There was an error creating the package in {directory}')
    else:
        python_file = integration.save_python_code(directory)
        print_success(f'Created Python file {python_file}.py')
        yaml_file = integration.save_yaml(directory)
        print_success(f'Created YAML file {yaml_file}.yml')


if __name__ in ['__main__', 'builtins', 'builtins']:
    main()
