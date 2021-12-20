import os

from demisto_sdk.commands.common.tools import FileType, find_type, print_error
from demisto_sdk.commands.generate_outputs.generate_context.generate_integration_context import \
    generate_integration_context
from demisto_sdk.commands.generate_outputs.generate_descriptions.generate_descriptions import \
    generate_ai_descriptions
from demisto_sdk.commands.generate_outputs.json_to_outputs.json_to_outputs import \
    json_to_outputs


def json_to_outputs_flow(kwargs):
    if not kwargs.get('command'):
        print_error(
            'To use the json-to-outputs version of this command please include a `command` argument.')
        return 1

    if not kwargs.get('prefix'):
        print_error(
            'To use the json-to-outputs version of this command please include a `prefix` argument.')
        return 1

    args = [kwargs.get('command'), kwargs.get('json'), kwargs.get('prefix'),
            kwargs.get('output'),
            kwargs.get('verbose'), kwargs.get('interactive'),
            kwargs.get('descriptions')]
    json_to_outputs(*args)

    if not kwargs.get('input', False):
        kwargs['input'] = kwargs['output']
    generate_ai_descriptions_flow(kwargs)
    return 0


def generate_integration_context_from_examples_flow(kwargs):
    input_path: str = kwargs.get('input', '')
    examples: str = kwargs.get('examples', '')
    insecure: bool = kwargs.get('insecure', False)

    validate_inputs_examples(input_path)
    generate_integration_context(input_path, examples, insecure)

    generate_ai_descriptions_flow(kwargs)
    return 0


def generate_ai_descriptions_flow(kwargs):
    ai: bool = kwargs.get('ai', False)
    if not ai:
        return

    input_path: str = kwargs.get('input', '')
    output_path: str = kwargs.get('output', False)
    if not output_path:
        print("**AI Output set to out.yml**")
        output_path = "out.yml"
    insecure: bool = kwargs.get('insecure', False)
    verbose: bool = kwargs.get('verbose', False)
    generate_ai_descriptions(input_path, output_path, True, verbose, insecure)


def validate_inputs_examples(input_path):
    if not input_path:
        print_error(
            'To use the generate_integration_context version of this command please include an `input` argument')
        return 1

    if input_path and not os.path.isfile(input_path):
        print_error(F'Input file {input_path} was not found.')
        return 1

    if not input_path.lower().endswith('.yml'):
        print_error(F'Input {input_path} is not a valid yml file.')
        return 1

    file_type = find_type(input_path, ignore_sub_categories=True)
    if file_type is not FileType.INTEGRATION:
        print_error('File is not an Integration.')
        return 1


def run_generate_outputs(**kwargs):
    '''
        Generate outputs
        - JSON to Outputs: will take a json and generate outputs from it.
        - Examples: will generate outputs from an examples file that connects to
            XSOAR to run commands, sends results into the same functionality
            behind Json to Outputs.
        - AI - Experimental feature to generate descriptions automatically from
            AI (text transformers https://en.wikipedia.org/wiki/Transformer_(machine_learning_model))
            It will be called in conjunction with the previous commands too if
            enabled by --ai. Or run separately
    '''
    # JSON to outputs flow
    if kwargs.get('json', False):
        json_to_outputs_flow(kwargs)

    # Examples flow
    elif kwargs.get('examples', False):
        generate_integration_context_from_examples_flow(kwargs)

    # Only --ai flow
    elif kwargs.get('ai', False):
        generate_ai_descriptions_flow(kwargs)

    return 0
