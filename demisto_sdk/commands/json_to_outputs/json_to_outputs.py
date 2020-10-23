"""
This script parses a raw response from an API(JSON) into yml formatted file with the context path of each field.
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
import json
import sys

import dateparser
import yaml
from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)


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
    """
    Determines if val is Date, if yes returns True otherwise False
    """
    if isinstance(val, (int, float)) and val > 15737548065 and val < 2573754806500:
        # 15737548065 is the lowest timestamp that exist year - 1970
        # 2573754806500 is the year 2050 - I believe no json will contain date time over this time
        # if number is between these two numbers it probably is timestamp=date
        return True

    if isinstance(val, str) and len(val) >= 10 and len(val) <= 30 and dateparser.parse(val):
        # the shortest date string is => len(2019-10-10) = 10
        # The longest date string I could think of wasn't of length over len=30 '2019-10-10T00:00:00.000 +0900'
        # To reduce in performance of using dateparser.parse,I
        return True

    return False


def determine_type(val):
    if is_date(val):
        return 'Date'

    if isinstance(val, str):
        return 'String'

    # bool is an sub class of int, so the we should first check isinstance of bool and only afterwards int
    if isinstance(val, bool):
        return 'Boolean'

    if isinstance(val, (int, float)):
        return 'Number'

    return 'Unknown'


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


def json_to_outputs(command, input, prefix, output=None, verbose=False, interactive=False):
    """
    This script parses JSON to Demisto Outputs YAML format

    Args:
        command: the name of the command that this output is belong like xdr-get-incidents
        input: full path to valid JSON file - the JSON file should contain API response from the service
        prefix: The prefix of the context, this prefix will appear for each output field - VirusTotal.IP,
            CortexXDR.Incident
        output: Full path to output file where to save the YAML
        verbose: This used for debugging purposes - more logs
        interactive: by default all the output descriptions are empty, but if user sets this to True then the script
            will ask user input for each description

    Returns:
    """
    try:
        if input:
            with open(input, 'r') as json_file:
                input_json = json_file.read()
        else:
            print("Enter the command's output in JSON format.\n As an example, If one of the command's output is `item_id`,\n enter {\"item_id\": 1234}")
            input_json = input_multiline()

        yaml_output = parse_json(input_json, command, prefix, verbose, interactive)

        if output:
            with open(output, 'w') as yf:
                yf.write(yaml_output)

                print_color(f'Outputs file was saved to :\n{output}', LOG_COLORS.GREEN)
        else:
            print_color("YAML Outputs\n\n", LOG_COLORS.GREEN)
            print(yaml_output)

    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            sys.exit(1)
