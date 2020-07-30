import os
from typing import Any, Dict, List, Optional, Tuple, Union

from demisto_sdk.commands.common.tools import (get_yaml, print_error,
                                               print_warning)
from demisto_sdk.commands.generate_docs.common import (
    HEADER_TYPE, generate_list_section, generate_numbered_section,
    generate_section, generate_table_section, save_output, string_escape_md)


def generate_playbook_doc(input, output: str = None, permissions: str = None, limitations: str = None,
                          verbose: bool = False):
    try:
        playbook = get_yaml(input)
        if not output:  # default output dir will be the dir of the input file
            output = os.path.dirname(os.path.realpath(input))
        errors = []

        description = playbook.get('description', '')
        _name = playbook.get('name', 'Unknown')
        if not description:
            errors.append('Error! You are missing description for the playbook')

        doc = [description, '', '## Dependencies',
               'This playbook uses the following sub-playbooks, integrations, and scripts.', '']

        playbooks, integrations, scripts, commands = get_playbook_dependencies(playbook, input)
        inputs, inputs_errors = get_inputs(playbook)
        outputs, outputs_errors = get_outputs(playbook)
        playbook_filename = os.path.basename(input).replace('.yml', '')

        errors.extend(inputs_errors)
        errors.extend(outputs_errors)

        # Playbooks general permissions
        if permissions == 'general':
            doc.extend(generate_section('Permissions', ''))

        doc.extend(generate_list_section('Sub-playbooks', playbooks, header_type=HEADER_TYPE.H3,
                                         empty_message='This playbook does not use any sub-playbooks.'))

        doc.extend(generate_list_section('Integrations', integrations, header_type=HEADER_TYPE.H3,
                                         empty_message='This playbook does not use any integrations.'))

        doc.extend(generate_list_section('Scripts', scripts, header_type=HEADER_TYPE.H3,
                                         empty_message='This playbook does not use any scripts.'))

        doc.extend(generate_list_section('Commands', commands, header_type=HEADER_TYPE.H3,
                                         empty_message='This playbook does not use any commands.'))

        doc.extend(generate_table_section(inputs, 'Playbook Inputs', 'There are no inputs for this playbook.'))

        doc.extend(generate_table_section(outputs, 'Playbook Outputs', 'There are no outputs for this playbook.'))

        # Known limitations
        if limitations:
            doc.extend(generate_numbered_section('Known Limitations', limitations))

        doc.append('## Playbook Image\n---')
        doc.append(f'![{_name}](Insert the link to your image here)')

        doc_text = '\n'.join(doc)

        save_output(output, f'{playbook_filename}_README.md', doc_text)

        if errors:
            print_warning('Possible Errors:')
            for error in errors:
                print_warning(error)

    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            return


def get_playbook_dependencies(playbook: dict, playbook_path: str) -> Tuple[list, List[Union[Union[bytes, str], Any]],
                                                                           list, list]:
    """
    Gets playbook dependencies(integrations, playbooks, scripts and commands) from playbook object.
    :param playbook: the playbook object.
    :param playbook_path: The path of the playbook
    :return: the method returns 4 lists - integrations, playbooks, scripts and commands.
    """
    integrations = set()
    scripts = set()
    commands = set()
    playbooks = set()

    playbook_tasks = playbook.get('tasks', {})
    playbook_path = os.path.relpath(playbook_path)
    pack_path = os.path.dirname(os.path.dirname(playbook_path))
    integration_dir_path = os.path.join(pack_path, 'Integrations')
    # Get all files in integrations directories
    pack_files = [os.path.join(r, file) for r, d, f in os.walk(integration_dir_path) for file in f]
    integrations_files = []
    for file in pack_files:
        if file.endswith('.yml'):
            # Get all yml files
            integrations_files.append(file)
    for task in playbook_tasks:
        task = playbook_tasks.get(task, {}).get('task')
        if task.get('iscommand'):
            integration = task.get('script')
            brand_integration = task.get('brand')
            integration_name, command_name = integration.split('|||')
            if command_name:
                commands.add(command_name)
            if integration_name:
                integrations.add(integration_name)
                if 'Builtin' in integrations:
                    integrations.remove('Builtin')

            elif brand_integration:
                integrations.add(brand_integration)

            elif 'Packs' in playbook_path:
                for file_ in integrations_files:
                    with open(file_) as f:
                        if command_name in f.read():
                            integration_dependency_path = os.path.dirname(file_)
                            integration_dependency = os.path.basename(integration_dependency_path)
                            # Case of old integrations without a package.
                            if integration_dependency == 'Integrations':
                                integrations.add(os.path.basename(file_).replace('.yml', ''))
                            else:
                                integrations.add(integration_dependency)
        else:
            script_name = task.get('scriptName')
            if script_name:
                scripts.add(script_name)
            elif task.get('type') == 'playbook':
                playbooks.add(task.get('name'))

    return list(playbooks), list(integrations), list(scripts), list(commands)


def get_inputs(playbook: Dict[str, List[Dict]]) -> Tuple[List[Dict], List[str]]:
    """Gets playbook inputs.

    Args:
        playbook (dict): the playbook object.

    Returns:
        (tuple): list of inputs and list of errors.
    """
    errors = []
    inputs = []

    if not playbook.get('inputs'):
        return [], []

    playbook_inputs: List = playbook.get('inputs', [])
    for _input in playbook_inputs:
        name = _input.get('key')
        description = string_escape_md(_input.get('description', ''))
        required_status = 'Required' if _input.get('required') else 'Optional'
        _value: Optional[str] = get_input_data(_input)

        playbook_input_query: Dict[str, str] = _input.get('playbookInputQuery')
        # a playbook input section whose 'key' key is empty and whose 'playbookInputQuery' key is a dict
        # is an Indicators Query input section
        if not name and isinstance(playbook_input_query, dict):
            name = 'Indicator Query'
            _value = playbook_input_query.get('query')
            default_description = 'Indicators matching the indicator query will be used as playbook input'
            description = description if description else default_description

        if not description:
            errors.append('Error! You are missing description in playbook input {}'.format(name))

        inputs.append({
            'Name': name,
            'Description': description,
            'Default Value': _value,
            'Required': required_status,
        })

    return inputs, errors


def get_outputs(playbook):
    """
    Gets playbook outputs.
    :param playbook: the playbook object.
    :return: list of outputs and list of errors.
    """
    errors = []
    outputs = []

    if not playbook.get('outputs'):
        return {}, []

    for output in playbook.get('outputs'):
        if not output.get('description'):
            errors.append(
                'Error! You are missing description in playbook output {}'.format(output.get('contextPath')))

        output_type = output.get('type')
        if not output_type:
            output_type = 'unknown'

        outputs.append({
            'Path': output.get('contextPath'),
            'Description': string_escape_md(output.get('description', '')),
            'Type': output_type
        })

    return outputs, errors


def get_input_data(input_section: Dict) -> str:
    """Gets playbook single input item - support simple and complex input.

    Args:
        input_section (dict): playbook input item.

    Returns:
        (str): The playbook input item's value.
    """
    default_value = input_section.get('value')
    if isinstance(default_value, str):
        return default_value

    if default_value:
        complex_field = default_value.get('complex')
        if complex_field:
            return f"{complex_field.get('root')}.{complex_field.get('accessor')}"
        return default_value.get('simple')

    return ''
