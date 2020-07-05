import argparse
import json
import os
import re
import sys

import autopep8
import yaml
import tempfile
import baseCode
import baseYAML

camelToSnakePattern = re.compile(r'(?<!^)(?=[A-Z])')

illegalChars = ['`', ':', '\n', "'", "<br>", "[", "]", "*", '"']
illegalFunctionNames = ['type', 'from']
prependIllegal = "i"
outputTypes = {
    "string": "String",
    "integer": "Number",
    "object": "Unknown",
    "boolean": "Boolean",
}
removedNames = ['.properties', '.items']


class DemistoIntegration:
    def __init__(self, file_path, baseName, commandpretext, includecommands, verbose=False):
        self.json = None
        self.baseName = baseName
        self.filtercommands = False
        self.includecommands = []
        self.commandpretext = commandpretext
        self.fileLoad = False
        self.swagger = None
        self.openapi = None
        self.commonfields = None
        self.host = None
        self.basePath = None
        self.schemes = None
        self.name = None
        self.display = None
        self.category = None
        self.description = None
        self.configuration = list()
        self.script = None
        self.security = None
        self.dockerimage = None
        self.consumes = list()
        self.produces = list()
        self.category = "Utilities"
        self.security = None
        self.securitySchemes = None
        self.functions = list()
        self.parameters = list()
        self.verbose = verbose
        self.loadFile(file_path, includecommands)

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
                        arr.append({"name": ".".join(context), "type": obj.get('type', 'Unknown'),
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

    def addConfig(self, display, name, defaultValue, intype, required):
        self.configuration.append({
            "display": display,
            "name": name,
            "defaultValue": defaultValue,
            "type": intype,
            "required": required
        })

    def add_function(self, path, method, data, pars, commandpretext):
        new_function = dict()
        new_function['path'] = path
        new_function['method'] = method
        name = data.get('operationId', None)
        if not name:
            try:
                name = data.get('summary', None)
                name = name.replace(" ", "-")
            except:
                name = None
        if not name:
            name = "-".join([x for x in path.split("/")
                             if "{" not in x]).lstrip("-")
        name = camelToSnake(name)
        name = name.replace("_", "-").replace("--", "-").replace(".", "")
        if commandpretext:
            name = "{}-".format(commandpretext.lower()) + name
        new_function['name'] = name
        func_desc = data.get('summary', None)
        if not func_desc:
            func_desc = data.get('description', "")
        for i in illegalChars:
            func_desc = func_desc.replace(i, " ")
        new_function['description'] = func_desc
        new_function['execution'] = True
        new_function['arguments'] = list()
        new_function['parameters'] = data.get('parameters', None)
        if not new_function['parameters']:
            new_function['parameters'] = pars
            iter_item = pars
        else:
            iter_item = data.get('parameters', [])
        for arg in iter_item:
            new_arg = dict()
            arg_name = str(arg.get('name', ""))
            new_arg['name'] = arg_name
            arg_desc = arg.get('description', "")
            for i in illegalChars:
                arg_desc = arg_desc.replace(i, " ")
            new_arg['description'] = f"\"{arg_desc}\""
            new_arg['required'] = arg.get('required')
            new_arg['default'] = arg.get('default', "")
            new_arg['in'] = arg.get('in', None)
            arg_types = {
                "string": "str",
                "integer": "int",
                "boolean": "bool",
                "file": "str",
                "int": "int",
                "str": "str",
            }
            new_arg['type'] = arg_types.get(arg.get('type', "string"), "string")
            new_arg['enums'] = [str(x) for x in arg.get(
                'enum')] if arg.get('enum', None) else None
            new_function['arguments'].append(new_arg)
        new_function['outputs'] = list()
        new_function['responses'] = list()
        for responseCode, response in data.get('responses', {}).items():
            new_response = dict()
            new_response['code'] = responseCode
            new_response['description'] = response.get('description', None)
            if response.get('schema'):
                # try:
                schema = response['schema']
                all_items = self.extract_values(schema, "properties")
                data = self.extract_outputs(all_items, [])
                for v in data:
                    description = v.get('description', '')
                    this_type = v.get('type', 'object')
                    this_type = outputTypes.get(this_type)
                    name = v.get('name')
                    for i in illegalChars:
                        description = description.replace(i, " ")
                    new_function['outputs'].append(
                        {"name": name, "type": this_type, "description": description})
            new_function['responses'].append(new_response)

        self.functions.append(new_function)
        self.functions = sorted(self.functions, key=lambda x: x['name'])

    def loadFile(self, file_path, includecommands):
        error = None
        try:
            self.json = json.load(open(file_path, "rb"))
            self.fileLoad = True
        except Exception as err:
            error = err
        if not self.fileLoad:
            try:
                stream = open(file_path, "rb")
                self.json = yaml.safe_load(stream)
                self.fileLoad = True
            except Exception as err:
                error = err
        if not self.fileLoad:
            print('Failed')
            print(error)
            sys.exit(-1)
        try:
            if includecommands:
                with open(includecommands, "r") as fp:
                    self.includecommands = fp.read().split("\n")
                    self.filtercommands = True
        except:
            self.filtercommands = False
            print("** WARNING ** -- There was an error loading the commands file {}\nIt has been ignored".format(
                includecommands))
        self.swagger = str(self.json.get('swagger', None))
        self.openapi = str(self.json.get('openapi', None))
        if self.json.get('host', None):
            self.host = self.json.get('host', None)
        elif self.json.get('servers', None):
            self.host = self.json.get('servers', [])[0]['url']
        if self.host:
            self.addConfig("Host", "host", self.host, 4, True)
        self.basePath = self.json.get('basePath', "")
        self.name = self.json['info']['title']
        self.display = self.json['info']['title']
        self.description = self.json.get('info', {}).get('description', "")
        self.version = -1
        self.id = self.name
        self.consumes = self.json.get('consumes', [])
        self.produces = self.json.get('produces', [])
        self.security = self.json.get('security', [])
        self.schemes = self.json.get('schemes', [])
        self.securitySchemes = self.json.get('securityDefinitions', {}) if self.swagger == "2.0" else self.json.get(
            'securitySchemes', {})
        self.functions = list()
        self.parameters = self.json.get('parameters', [])
        for path, function in self.json['paths'].items():
            for method, data in function.items():
                if "parameters" not in method:
                    if (self.filtercommands and data.get('operationId',
                                                         "") in self.includecommands) or not self.filtercommands:
                        self.add_function(path, method, data, function.get(
                            'parameters', []), self.commandpretext)
                    else:
                        if self.verbose:
                            print("Ignoring command '{}' as it is not in the include commands list".format(
                                data.get('operationId', "")))
        self.dockerimage = None

    def return_python_code(self):

        # Use the code from baseCode in baseCode.py as the basis
        data = baseCode.baseCode

        # Replace the consume data
        data = data.replace("$CONSUMES$", ", ".join(self.consumes))

        # Build the functions from swagger file
        these_functions = list()
        for func in self.functions:
            function_name = func['name'].replace("-", "_")
            this_function = baseCode.baseFunction.replace(
                "$FUNCTIONNAME$", function_name)
            new_params = [x['name']
                         for x in func['arguments'] if "query" in x['in']]
            new_data = [x['name']
                       for x in func['arguments'] if "body" in x['in']]
            arguments = list()
            arguments_found = False

            for arg in func['arguments']:
                arguments_found = True
                if arg['required']:
                    argument_default = ")"
                elif arg['type'] == 'int':
                    argument_default = f", {arg['default']})"
                else:
                    argument_default = f", '{arg['default']}')"
                # argumentDefault = ")" if arg['required'] else f", '{arg['default']}')"
                this_argument = baseCode.baseArgument.replace(
                    "$DARGNAME$", arg['name']) + argument_default
                new_arg_name = arg['name']
                if new_arg_name in illegalFunctionNames:
                    new_arg_name = f"{prependIllegal}{new_arg_name}"
                this_argument = this_argument.replace("$SARGNAME$", new_arg_name)
                this_argument = this_argument.replace("$ARGTYPE$", arg['type'])

                arguments.append(this_argument)

            if arguments_found:
                this_function = this_function.replace(
                    "$ARGUMENTS$", "\n    ".join(arguments))
            else:
                this_function = "\n".join(
                    [x for x in this_function.split("\n") if "$ARGUMENTS$" not in x])

            if new_params:
                modified_params = list()
                for p in new_params:
                    if p in illegalFunctionNames:
                        modified_params.append(f"\"{p}\": {prependIllegal}{p}")
                    else:
                        modified_params.append(f"\"{p}\": {p}")
                params = baseCode.baseParams.replace(
                    "$PARAMS$", ", ".join(modified_params))
                this_function = this_function.replace("$PARAMETERS$", params)
            else:
                this_function = "\n".join(
                    [x for x in this_function.split("\n") if "$PARAMETERS$" not in x])
                # params = ""
            # thisFunction = thisFunction.replace("$PARAMETERS$", params)

            if new_data:
                all_new_data = ",".join(new_data)
                this_function = this_function.replace(
                    "$DATA$", f"data = {all_new_data}")
            else:
                this_function = "\n".join(
                    [x for x in this_function.split("\n") if "$DATA$" not in x])

            this_function = this_function.replace("$METHOD$", func['method'])
            func['path'] = f"'{func['path']}'" if "'" not in func['path'] else func['path']
            func['path'] = f"f{func['path']}" if "{" in func['path'] else func['path']
            this_function = this_function.replace("$PATH$", func['path'])

            if new_params:
                this_function = this_function.replace(
                    "$NEWPARAMS$", ", params=params")
            else:
                this_function = this_function.replace("$NEWPARAMS$", "")
            if new_data:
                this_function = this_function.replace("$NEWDATA$", ", data=data")
            else:
                # thisFunction = "\n".join([x for x in thisFunction.split("\n") if "$NEWDATA$" not in x])
                this_function = this_function.replace("$NEWDATA$", "")

            this_function = this_function.replace(
                "$CONTEXTNAME$", func['name'].title().replace("-", ""))
            contextcontext = func['name'].title().replace("-", "")
            if self.commandpretext:
                contextcontext = f"{self.commandpretext}.{contextcontext}"
            this_function = this_function.replace(
                "$CONTEXTCONTEXT$", contextcontext)
            these_functions.append(this_function)

        data = data.replace("$FUNCTIONS$", "\n".join(these_functions))
        data = data.replace("$BASEURL$", self.basePath)

        listFunctions = list()

        # Add the command mappings:
        for func in self.functions:
            thisListFunction = baseCode.baseListFunctions.replace(
                "$FUNCTIONNAME$", func['name'])
            fn = func['name'].replace("-", "_")
            thisListFunction = thisListFunction.replace(
                "$FUNCTIONCOMMAND$", f"{fn}_command")
            listFunctions.append(thisListFunction)

        data = data.replace("$COMMANDSLIST$", "\n\t".join(listFunctions))
        data = autopep8.fix_code(data)

        return data

    def return_integration(self, noCode):
        # Create a base file for YAML file
        yaml = baseYAML.blankIntegration

        # Create the commands section
        commands = list()
        for func in self.functions:
            args = list()
            for arg in func['arguments']:
                argName = arg['name']
                required = "true" if arg['required'] else "false"
                description = arg.get('description', None)
                if not description and "body" in arg['in']:
                    try:
                        thisType = arg['schema']['properties']['members']['type']
                        properties = ",".join(
                            arg['schema']['properties']['members']['items']['properties'].keys())
                        description = f"An {thisType} containing the following items - {properties}"
                    except KeyError:
                        description = None
                a = f"    - name: {argName}\n      required: {required}\n"
                if description:
                    d = description.split('.')[0]
                    d = d.split("\n")[0]
                    if d.startswith('"') and not d.endswith('"'):
                        d += '"'
                    elif d.endswith('"') and not d.startswith('"'):
                        d = '"' + d
                    a += f"      description: {d}\n"
                    print(d)
                if arg['enums']:
                    enums = str()
                    for enum in arg['enums']:
                        enums += f"      - \"{enum}\"\n"
                    a += f"      auto: PREDEFINED\n      predefined:\n{enums}"
                args.append(a)
            outputs = list()

            for output in func['outputs']:
                o = "    - contextPath: "
                if self.commandpretext:
                    o += f"{self.commandpretext.title()}."
                fn = func['name'].title().replace("-", "")
                outputName = output['name']
                outputDescription = output['description']
                outputType = output['type']
                o += f"{fn}.{outputName}\n      description: \"{outputDescription}\"\n      type: {outputType}\n"
                outputs.append(o)
            fn = func['name']
            theseArgs = "".join(args)
            theseOutputs = "".join(outputs)
            thisDescription = func['description']
            s = f"  - name: {fn}\n"
            if len(theseArgs) > 0:
                s = f"{s}    arguments:\n{theseArgs}"
            if len(theseOutputs) > 0:
                s = f"{s}    outputs:\n{theseOutputs}"
            s = f"{s}    description: {thisDescription}"
            commands.append(s)

        # Create the other configurations that might be required
        configurations = list()
        for k, v in self.securitySchemes.items():
            try:
                if "header" in v['in']:
                    pass
            except:
                pass

        yaml = yaml.replace("$ID$", self.id)
        yaml = yaml.replace("$VERSION$", str(self.version))
        yaml = yaml.replace("$NAME$", self.name)
        yaml = yaml.replace("$DISPLAY$", self.display)
        yaml = yaml.replace(
            "$DESCRIPTION$", self.description.replace("\n", " "))
        yaml = yaml.replace("$HOST$", self.host)
        yaml = yaml.replace("$COMMANDS$", "\n".join(commands))
        if noCode:
            yaml = yaml.replace("$SCRIPT$", "''")
        else:
            code = self.return_python_code().replace("\n", "\n    ")
            yaml = yaml.replace("$SCRIPT$", f"|+\n    {code}")
        return yaml.encode(encoding='utf-8')

    def save_python_code(self, directory):
        filename = os.path.join(directory, f"{self.baseName}.py")
        try:
            with open(filename, "w") as fp:
                fp.write(self.return_python_code())
                return filename
        except Exception as err:
            print(f"Error writing {filename} - {err}")
            raise

    def save_yaml(self, directory, no_code=False):
        filename = os.path.join(directory, f"{self.baseName}.yml")
        try:
            with open(filename, "wb") as fp:
                fp.write(self.return_integration(no_code))
            return filename
        except Exception as err:
            print(f"Error writing {filename} - {err}")
            raise

    def savePackage(self, directory):
        code_path = self.save_python_code(directory)
        yml_path = self.save_yaml(directory, no_code=True)
        return code_path, yml_path


def camelToSnake(camel):
    snake = camelToSnakePattern.sub('_', camel).lower()
    return snake


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('swaggerFile', metavar='swaggerFile',
                        help='The swagger file to load')
    parser.add_argument('baseName', metavar='baseName',
                        help='The base filename to use for the generated files')
    parser.add_argument('-p', '--outputPackage', action='store_true',
                        help='Output the integration as a package (separate code and yml files)')
    parser.add_argument('-d', '--directory', metavar='directory',
                        help='Directory to store the output to (default is current working directory)')
    parser.add_argument('-t', '--commandpretext', metavar='commandpretext',
                        help='Add an additional word to each commands text')
    parser.add_argument('-i', '--includecommands', metavar='includecommands',
                        help='A line delimited file containing the commands that should ONLY be generated. This works with the "operationId" of a path.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Be verbose with the log output')

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
            print(f"Error creating directory {directory} - {err}")
            sys.exit(1)
    if not os.path.isdir(directory):
        print(f"The directory provided '{directory}' is not a directory")
        sys.exit(1)

    integration = DemistoIntegration(args.swaggerFile, args.baseName, args.commandpretext, args.includecommands,
                                     verbose=args.verbose)

    if args.outputPackage:
        if integration.savePackage(directory):
            print(f"Created package in {directory}")
        else:
            print(f"There was an error creating the package in {directory}")
    else:
        file_name = integration.save_python_code(directory)
        print(f"Created Python file {file_name}.py")
        filename = integration.save_yaml(directory)
        print(f"Created YAML file {filename}.yml")


if __name__ in ['__main__', 'builtins', 'builtins']:
    main()
