import os.path
import io
import re
import json
from typing import Any, Dict, List, Optional, Tuple

from demisto_sdk.commands.json_to_outputs.json_to_outputs import parse_json
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_yaml, write_yml,
                                               print_color, print_error,
                                               print_warning)
from demisto_sdk.commands.generate_docs.common import (build_example_dict)
from demisto_sdk.commands.generate_docs.generate_integration_doc import \
    get_command_examples


def dict_from_outputs_str(command: str, outputs: str, verbose=False):
    """ Create a pythonic dict from the yml outputs string.

    Args:
        command: the command to parse.
        outputs: the json outputs to parse into a dict.
        verbose: whether to run in verbose mode or not.
    """
    dict_output = parse_json(outputs.replace("'", '"'), command, "", verbose,
                             return_object=True)
    return dict_output


def generate_example_dict(examples_file: str, insecure=False):
    """ Generate the example dict via an XSOAR server and return dict results.

    Args:
        examples_file: yaml as python dict.
        insecure: wether to run the examples without checking ssl.
    """
    example_dict = {}
    if examples_file and os.path.isfile(examples_file):
        command_examples = get_command_examples(examples_file,
                                                None)
        example_dict, build_errors = build_example_dict(command_examples,
                                                        insecure)
        if len(build_errors) > 0:
            raise Exception(
                f'Command examples had errors: {build_errors}')
    else:
        raise Exception(
            f'Command examples file was not found {examples_file}.')
    return example_dict


def insert_outputs(yml_data: Dict, command: str, output_with_contexts: List):
    """ Insert new ouputs for a command in the yml_data and return it.

    Args:
        yml_data: yaml as python dict.
        commnad: the command we want to change the outputs of.
        output_with_contexts: the new outputs.
    """
    commands = yml_data['script']['commands']
    found = False
    for i, v in enumerate(commands):
        if v.get('name') == command:
            commands[i]['outputs'] = output_with_contexts
            found = True
            break

    if not found:
        raise Exception(
            f'Input YML doesn\'t have the "{command}" command that exists in the examples file.')

    yml_data['script']['commands'] = commands
    return yml_data


def generate_integration_context(
        input_path: str,
        examples: Optional[str] = None,
        insecure: bool = False,
        verbose: bool = False,
):
    """ Generate integration command contexts in-place.

    Args:
        input_path: path to the yaml integration.
        examples: path to the command examples.
        insecure: should use insecure.
        verbose: verbose (debug mode).
    """

    try:
        yml_data = get_yaml(input_path)

        # Parse examples file
        example_dict = generate_example_dict(examples, insecure)

        for command in example_dict:
            print(f'Building context for the {command} command...')
            _, _, outputs = example_dict.get(command)

            # Generate the examples with a local server
            output_with_contexts = dict_from_outputs_str(command, outputs,
                                                         verbose=verbose)
            output_contexts = output_with_contexts.get('outputs')
            yml_data = insert_outputs(yml_data, command, output_contexts)

        # Make the changes in place the input yml
        print(f'Writing outputs to input file "{input_path}"...')
        write_yml(input_path, yml_data)
    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            return
