import os

from demisto_sdk.commands.common.tools import FileType, find_type, print_error
from demisto_sdk.commands.generate_outputs.generate_context.generate_integration_context import \
    generate_integration_context
from demisto_sdk.commands.generate_outputs.json_to_outputs.json_to_outputs import \
    json_to_outputs


def run_generate_outputs(**kwargs):
    if kwargs.get('json', False):
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
        return 0

    input_path: str = kwargs.get('input', '')
    examples: str = kwargs.get('examples', '')
    insecure: bool = kwargs.get('insecure', False)

    # validate inputs
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

    if file_type == FileType.INTEGRATION:
        generate_integration_context(input_path, examples, insecure)
        return 0
    else:
        print_error(f'File type {file_type.value} is not supported.')
        return 1
