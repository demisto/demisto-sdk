import argparse
import autopep8
import json
import os
import re
import shutil
import sys
import yaml

from distutils.util import strtobool
from demisto_sdk.commands.openapi_codegen.base_code import (
    base_argument, base_code, base_function, base_list_functions, base_params, base_data)
from demisto_sdk.commands.openapi_codegen.XSOARIntegration import XSOARIntegration

camel_to_snake_pattern = re.compile(r'(?<!^)(?=[A-Z][a-z])')
illegal_description_chars = ['\n', '<br>', '*', '\r', '\t', '<para/>']
illegal_func_chars = illegal_description_chars + [' ', ',', '(', ')', '`', ':', "'", '"', '[', ']']
illegal_function_names = ['type', 'from']
prepend_illegal = 'i'
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


class OpenAPIIntegration:
    def __init__(self, file_path, base_name, command_prefix, context_path, include_commands,
                 verbose=False, fix_code=False):
        self.json = None
        self.baseName = base_name
        self.filter_commands = False
        self.include_commands = []
        self.command_prefix = command_prefix
        self.context_path = context_path
        self.file_load = False
        self.swagger = None
        self.openapi = None
        self.host = None
        self.base_path = None
        self.schemes = None
        self.name = None
        self.description = None
        self.configuration = list()
        self.script = None
        self.security = None
        self.consumes = list()
        self.produces = list()
        self.security = None
        self.securitySchemes = None
        self.definitions = None
        self.components = None
        self.functions = list()
        self.parameters = list()
        self.verbose = verbose
        self.fix_code = fix_code
        self.load_file(file_path, include_commands)

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
        new_function = dict()
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
        new_function['arguments'] = list()
        new_function['parameters'] = data.get('parameters', None)
        if not new_function['parameters']:
            new_function['parameters'] = params
            iter_item = params
        else:
            iter_item = data.get('parameters', [])
        for arg in iter_item:
            # ￿￿TODO: extract args from $ref?
            new_arg = dict()
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
        new_function['outputs'] = list()
        new_function['responses'] = list()
        for response_code, response in data.get('responses', {}).items():
            new_response = dict()
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
                else:
                    all_items.extend(self.extract_values(schema, 'properties'))
                data = self.extract_outputs(all_items, [])
                for v in data:
                    description = v.get('description', '')
                    this_type = v.get('type', 'object')
                    this_type = output_types.get(this_type)
                    resp_name = v.get('name')
                    description = self.clean_description(description)
                    new_function['outputs'].append(
                        {'name': resp_name, 'type': this_type, 'description': description})
            new_function['responses'].append(new_response)

        self.functions.append(new_function)
        self.functions = sorted(self.functions, key=lambda x: x['name'])

    def load_file(self, file_path, includecommands):
        # TODO: add prints
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
            print('Failed')
            print(error)
            sys.exit(-1)
        try:
            if includecommands:
                with open(includecommands, 'r') as fp:
                    self.include_commands = fp.read().split('\n')
                    self.filter_commands = True
        except Exception as e:
            self.filter_commands = False
            print(f'** WARNING ** -- There was an error loading the commands file {includecommands}: {e} '
                  f'\nIt has been ignored')
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
        self.consumes = self.json.get('consumes', [])
        self.produces = self.json.get('produces', [])
        self.security = self.json.get('security', [])
        self.schemes = self.json.get('schemes', [])
        self.securitySchemes = self.json.get('securityDefinitions', {}) if self.swagger == '2.0' else self.json.get(
            'securitySchemes', {})
        self.definitions = self.json.get('definitions', {})
        self.components = self.json.get('components', {})
        self.functions = list()
        self.parameters = self.json.get('parameters', [])
        for path, function in self.json['paths'].items():
            # TODO: try except
            for method, data in function.items():
                if 'parameters' not in method:
                    # TODO: what if there is no operationId?
                    if (self.filter_commands and data.get('operationId',
                                                          '') in self.include_commands) or not self.filter_commands:
                        # TODO: parallel?
                        print(f'Adding command for the path: {path}')
                        self.add_function(path, method, data, function.get(
                            'parameters', []))
                        print(f'Finished adding command for the path: {path}')
                    else:
                        if self.verbose:
                            print('Ignoring command "{}" as it is not in the include commands list'.format(
                                data.get('operationId', '')))

    def return_python_code(self):

        # Use the code from baseCode in py as the basis
        data = base_code

        # Replace the consume data
        # TODO: this + produces
        data = data.replace('$CONSUMES$', ', '.join(self.consumes))

        # Build the functions from swagger file
        these_functions = list()
        for func in self.functions:
            function_name = func['name'].replace('-', '_')
            print(f'Adding the function {function_name} to the code...')
            this_function = base_function.replace('$FUNCTIONNAME$', function_name)
            new_params = [x['name'] for x in func['arguments'] if 'query' in x['in']]
            new_data = [x['name'] for x in func['arguments'] if x['in'] in ['formData', 'body']]
            arguments = list()
            arguments_found = False

            for arg in func['arguments']:
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
                this_function = this_function.replace('$ARGUMENTS$', '\n    '.join(arguments))
            else:
                this_function = '\n'.join(
                    [x for x in this_function.split('\n') if '$ARGUMENTS$' not in x])

            if new_params:
                params = self.format_params(new_params, base_params, '$PARAMS$')
                this_function = this_function.replace('$PARAMETERS$', params)
            else:
                this_function = '\n'.join(
                    [x for x in this_function.split('\n') if '$PARAMETERS$' not in x])

            if new_data:
                new_data = self.format_params(new_data, base_data, '$DATAOBJ$')
                this_function = this_function.replace('$DATA$', new_data)
            else:
                this_function = '\n'.join(
                    [x for x in this_function.split('\n') if '$DATA$' not in x])

            this_function = this_function.replace('$METHOD$', func['method'])
            func['path'] = f"'{func['path']}'" if "'" not in func['path'] else func['path']
            func['path'] = f"f{func['path']}" if "{" in func['path'] else func['path']
            this_function = this_function.replace('$PATH$', func['path'])

            if new_params:
                this_function = this_function.replace(
                    '$NEWPARAMS$', ', params=params')
            else:
                this_function = this_function.replace('$NEWPARAMS$', '')
            if new_data:
                this_function = this_function.replace('$NEWDATA$', ', data=data')
            else:
                this_function = this_function.replace('$NEWDATA$', '')

            this_function = this_function.replace('$CONTEXTNAME$', func['name'].title().replace('_', ''))
            contextcontext = func['name'].title().replace('_', '')
            if self.context_path:
                contextcontext = f'{self.context_path}.{contextcontext}'
            this_function = this_function.replace(
                '$CONTEXTCONTEXT$', contextcontext)
            these_functions.append(this_function)

        data = data.replace('$FUNCTIONS$', '\n'.join(these_functions))
        data = data.replace('$BASEURL$', self.base_path)

        list_functions = list()

        # Add the command mappings:
        for func in self.functions:
            prefix = ''
            if self.command_prefix:
                prefix = f'{self.command_prefix}-'

            function = base_list_functions.replace(
                '$FUNCTIONNAME$', f"{prefix}{func['name']}".replace('_', '-'))
            fn = func['name'].replace('-', '_')
            function = function.replace('$FUNCTIONCOMMAND$', f'{fn}_command')
            list_functions.append(function)

        data = data.replace('$COMMANDSLIST$', '\n\t'.join(list_functions))
        print('Finished creating the python code.')

        if self.fix_code:
            print('Fixing the code with autopep8...')
            data = autopep8.fix_code(data)

        return data

    def format_params(self, new_params, base, base_string):
        modified_params = list()
        for p in new_params:
            if p in illegal_function_names:
                modified_params.append(f'\"{p}\": {prepend_illegal}{p}')
            else:
                modified_params.append(f'\"{p}\": {p}')
        params = base.replace(base_string, ', '.join(modified_params))
        return params

    def return_integration(self, no_code):
        integration = XSOARIntegration.get_base_integration()
        # Create the commands section
        commands = []
        for func in self.functions:
            args = []
            options = None
            auto = None
            for arg in func['arguments']:
                arg_name = arg['name']
                required = True if arg['required'] else False
                description = arg.get('description', None)
                if not description and 'body' in arg['in']:
                    try:
                        type_ = arg['schema']['properties']['members']['type']
                        properties = ','.join(
                            arg['schema']['properties']['members']['items']['properties'].keys())
                        description = f'An {type_} containing the following items - {properties}'
                    except KeyError:
                        description = None
                if description:
                    description = description.split('.')[0].split('\n')[0]
                else:
                    description = ''

                if arg['enums']:
                    auto = 'PREDEFINED'
                    options = arg['enums']

                args.append(XSOARIntegration.Script.Command.Argument(arg_name, description, required, auto, options))

            outputs = []

            for output in func['outputs']:
                output_name = ''
                if self.context_path:
                    output_name = f'{self.context_path}.'
                name = func['name'].title().replace('_', '').split('-')
                if len(name) > 1:
                    name = name[1]
                else:
                    name = name[0]

                output_name += name
                output_postfix = output['name']
                output_description = output['description']
                output_type = output['type']

                outputs.append(XSOARIntegration.Script.Command.Output(output_type, f'{output_name}.{output_postfix}',
                                                                      output_description))
            prefix = ''
            if self.command_prefix:
                prefix = f'{self.command_prefix}-'
            command_name = f"{prefix}{func['name']}".replace('_', '-')
            command_description = func['description']
            commands.append(XSOARIntegration.Script.Command(command_name, command_description, args, outputs))

        script = ''
        if not no_code:
            script = self.return_python_code()

        integration.script.script = script
        integration.script.commands = commands

        if self.name:
            integration.name = self.name
            integration.commonfields.id = self.name
            integration.display = self.name
        if self.description:
            integration.description = self.description

        url = 'https://www.example.com/api'
        if self.host:
            url = self.host

        integration.configuration.append(XSOARIntegration.Configuration(display=f'Server URL (e.g. {url})',
                                                                        name='url',
                                                                        defaultvalue=url,
                                                                        type_=0,
                                                                        required=True))

        return integration

    def save_python_code(self, directory):
        print('Creating python file...')
        filename = os.path.join(directory, f'{self.baseName}.py')
        try:
            with open(filename, 'w') as fp:
                fp.write(self.return_python_code())
                return filename
        except Exception as err:
            print(f'Error writing {filename} - {err}')
            raise

    def save_yaml(self, directory, no_code=False):
        print('Creating yaml file...')
        filename = os.path.join(directory, f'{self.baseName}.yml')
        try:
            with open(filename, 'wb') as fp:
                fp.write(yaml.dump(self.return_integration(no_code).to_yaml()).encode())
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


def camel_to_snake(camel):
    snake = camel_to_snake_pattern.sub('_', camel).lower()
    return snake


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('swagger_file', metavar='swagger_file',
                        help='The swagger file to load')
    parser.add_argument('base_name', metavar='base_name',
                        help='The base filename to use for the generated files')
    parser.add_argument('-p', '--output_package', action='store_true',
                        help='Output the integration as a package (separate code and yml files)')
    parser.add_argument('-d', '--directory', metavar='directory',
                        help='Directory to store the output to (default is current working directory)')
    parser.add_argument('-t', '--command_prefix', metavar='command_prefix',
                        help='Add an additional word to each commands text')
    parser.add_argument('-c', '--context_path', metavar='context_path',
                        help='Context output path')
    parser.add_argument('-i', '--include_commands', metavar='include_commands',
                        help='A line delimited file containing the commands that should ONLY be generated.'
                             ' This works with the "operationId" of a path.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Be verbose with the log output')
    parser.add_argument('-f', '--fix_code', action='store_true',
                        help='Fix the python code using autopep8.')

    args = parser.parse_args()

    if not args.directory:
        directory = os.getcwd()
    else:
        directory = args.directory

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

    print('Processing swagger file...')
    integration = OpenAPIIntegration(args.swagger_file, args.base_name, args.command_prefix, args.context_path,
                                     args.include_commands, verbose=args.verbose, fix_code=args.fix_code)

    if args.output_package:
        if integration.save_package(directory):
            print(f'Created package in {directory}')
        else:
            print(f'There was an error creating the package in {directory}')
    else:
        python_file = integration.save_python_code(directory)
        print(f'Created Python file {python_file}.py')
        yaml_file = integration.save_yaml(directory)
        print(f'Created YAML file {yaml_file}.yml')


if __name__ in ['__main__', 'builtins', 'builtins']:
    main()
