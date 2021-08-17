import os.path
import io
import re
import json
from typing import Any, Dict, List, Optional, Tuple

from demisto_sdk.commands.json_to_outputs.json_to_outputs import parse_json


def generate_context_from_outputs(command: str, outputs: str):
    yaml_output = parse_json(outputs.replace("'", '"'), command, "", True, return_object=True)
    print(1)
    return yaml_output


def generate_integration_context(
        input_path: str,
        examples: Optional[str] = None,
        insecure: bool = False,
        verbose: bool = False,
        command: Optional[str] = None
):
    """ Generate integration command contexts.

    Args:
        input_path: path to the yaml integration
        examples: path to the command examples
        limitations: limitations description
        insecure: should use insecure
        verbose: verbose (debug mode)
    """
    import pprint

    try:
        yml_data = get_yaml(input_path)

        errors: list = []
        example_dict = {}
        if examples and os.path.isfile(examples):
            specific_commands = command.split(',') if command else None
            command_examples = get_command_examples(examples, specific_commands)
            example_dict, build_errors = build_example_dict(command_examples,
                                                            insecure)
            errors.extend(build_errors)
        else:
            errors.append(f'Command examples was not found {examples}.')

        outputs = example_dict.get('guardicore-search-asset')[2]
        outputs = json.loads(outputs)
        pprint.pprint(outputs)
    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            return
