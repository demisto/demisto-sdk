import yaml
import argparse
import json
import sys
import dateparser
from demisto_sdk.common.tools import print_error, print_warning, print_color, LOG_COLORS

"""
This script parse a Context output into yml formatted file with the context path of each field.
For example:

{
    "id":12131,
    "description":"desc",
    "summary":"do-not-delete",
    "created":"2019-03-25T16:13:13.188+0200",
    "issuetype":{
        "id":10004,
        "name":"Bug"
    },
    "project":{
        "id":10001,
        "key":"SOC",
        "projectTypeKey":"software"
    },
    "status":{
        "id":10003,
            "StatusCategory":{
                "key":"new",
                "colorName":"blue-gray",
                "name":"To Do"
        }
    }
}

==>

arguments: []
name: integration-command
outputs:
- contextPath: Demisto.Id
  description: ''
  type: Number
- contextPath: Demisto.Description
  description: ''
  type: String
- contextPath: Demisto.Summary
  description: ''
  type: String
- contextPath: Demisto.Created
  description: ''
  type: String
- contextPath: Demisto.Issuetype.Id
  description: ''
  type: Number
- contextPath: Demisto.Issuetype.Name
  description: ''
  type: String
- contextPath: Demisto.Project.Id
  description: ''
  type: Number
- contextPath: Demisto.Project.Key
  description: ''
  type: String
- contextPath: Demisto.Project.ProjectTypeKey
  description: ''
  type: String
- contextPath: Demisto.Status.Id
  description: ''
  type: Number
- contextPath: Demisto.Status.StatusCategory.Key
  description: ''
  type: String
- contextPath: Demisto.Status.StatusCategory.Colorname
  description: ''
  type: String
- contextPath: Demisto.Status.StatusCategory.Name
  description: ''
  type: String
"""


def input_multiline():
    sentinel = ''  # ends when this string is seen
    return '\n'.join(iter(input, sentinel))


def flatten_json(nested_json, camelize=False):
    out = {}

    def flatten(x, name=''):
        # capitalize first letter in each key
        try:
            name = name[0].upper() + name[1:] if camelize else name
        except IndexError:
            name = name.title() if camelize else name

        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            for a in x:
                flatten(a, name[:-1] + '.')
        else:
            out[name.rstrip('.')] = x

    flatten(nested_json)
    return out


def jsonise(context_key, value, description=''):
    return {
        'contextPath': context_key,
        'description': description,
        'type': determine_type(value)
    }


def is_date(val):
    if isinstance(val, (int, float)) and val > 15737548065 and val < 2573754806500:
        return True
    if isinstance(val, str) and len(val) >= 10 and len(val) <= 30 and dateparser.parse(val):
        return True

    return False


def determine_type(val):
    if is_date(val):
        return True

    return 'Boolean' if isinstance(val, bool) else 'Number' if isinstance(
        val, (int, float)) else 'String' if isinstance(val, str) else 'Unknown'


def parse_json(data, command_name, prefix, verbose=False, interactive=False):
    if data == '':
        raise ValueError('Invalid input JSON - got empty string')

    try:
        data = json.loads(data)
    except ValueError as ex:
        if verbose:
            print_error(str(ex))

        raise ValueError('Invalid input JSON')
    flattened_data = flatten_json(data)
    if prefix:
        flattened_data = {f'{prefix}.{key}': value for key, value in flattened_data.items()}

    arg_json = []
    for key, value in flattened_data.items():
        description = ''
        if interactive:
            print(f'Enter description for: [{key}]')
            description = input_multiline()

        arg_json.append(jsonise(key, value, description))

    if verbose:
        print(f'JSON before converting to YAML: {arg_json}')

    yaml_output = yaml.safe_dump(
        {
            'name': command_name.lstrip('!'),
            'arguments': [],
            'outputs': arg_json
        },
        default_flow_style=False
    )
    return yaml_output


def json_to_outputs(command, infile, prefix, outfile=None, verbose=False, interactive=False):
    try:
        yaml_output = None
        if infile:
            with open(infile, 'r') as json_file:
                yaml_output = parse_json(json_file.read(), command, prefix, verbose, interactive)

        else:
            print("Dump your JSON here:")
            input_json = input_multiline()
            yaml_output = parse_json(input_json, command, prefix, verbose, interactive)

        if outfile:
            with open(outfile, 'w') as yf:
                yf.write(yaml_output)

                print_color(f'Outputs file was saved to :\n{outfile}', LOG_COLORS.GREEN)
        else:
            print_color("YAML Outputs\n\n", LOG_COLORS.GREEN)
            print(yaml_output)

    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            sys.exit(1)
