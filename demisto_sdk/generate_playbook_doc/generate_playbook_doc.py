import sys
import pyperclip
from demisto_sdk.common.tools import print_error
from ruamel.yaml import YAML


def generate_playbook_doc(path, verbose=False):
    try:
        playbook = get_content_from_yml_file(path)

        doc = ['## Dependencies', 'This playbook uses the following sub-playbooks, integrations, and scripts.']

        playbooks, integrations, scripts, commands = get_dependencies(playbook)

        doc.extend(generate_section('Sub-playbooks', playbooks, 'This playbook does not use any sub-playbooks.'))
        doc.extend(generate_section('Integrations', integrations, 'This playbook does not use any integrations.'))
        doc.extend(generate_section('Scripts', scripts, 'This playbook does not use any scripts.'))
        doc.extend(generate_section('Commands', commands, 'This playbook does not use any commands.'))

        errors = []
        inputs, inputs_errors = get_inputs(playbook)
        outputs, outputs_errors = get_outputs(playbook)

        errors.extend(inputs_errors)
        errors.extend(outputs_errors)

        doc.extend(generate_table_section(inputs, 'Playbook Inputs', 'There are no inputs for this playbook.'))
        doc.extend(generate_table_section(outputs, 'Playbook Outputs', 'There are no outputs for this playbook.'))

        doc.append('<!-- Playbook PNG image comes here -->')

        documentation_text = '\n'.join(doc)
        print(documentation_text)

        pyperclip.copy(documentation_text)

        for error in errors:
            print_error(error)

    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            sys.exit(1)


def get_content_from_yml_file(path):
    ryaml = YAML()
    ryaml.preserve_quotes = True
    try:
        with open(path, 'r') as yf:
            content = ryaml.load(yf)
    except Exception as e:
        print_error(f'Error - failed to parse: {path}.\n{e}')
        sys.exit(1)
    return content


def generate_section(title, data, empty_message):
    section = [f'## {title}']

    if not data:
        section.extend([empty_message, ''])
        return section

    for item in data:
        section.append(f'* {item}')
    section.append('')
    return section


def generate_table_section(data, header, empty_message):
    section = [f'## {header}']

    if not data:
        section.extend([empty_message, ''])
        return section

    section.extend(['|', '|'])
    for key in data[0]:
        section[1] += f' **{key}** |'
        section[2] += ' --- |'

    for item in data:
        tmp_item = '|'
        for key in item:
            tmp_item += f' {item.get(key)} |'
        section.append(tmp_item)

    section.append('')
    return section


def get_dependencies(playbook):
    integrations = []
    scripts = []
    commands = []
    playbooks = []
    playbook_tasks = playbook.get('tasks')
    for task in playbook_tasks:
        task = playbook_tasks[task]['task']
        if task['iscommand']:
            integration = task['script']
            integration = integration.split('|||')
            integrations.append(integration[0])
            commands.append(integration[1])
        else:
            script_name = task.get('scriptName')
            if script_name:
                scripts.append(script_name)
            elif task.get('type') == 'playbook':
                playbooks.append(task.get('name'))

    integrations = list(filter(None, dict.fromkeys(integrations)))
    playbooks = list(filter(None, dict.fromkeys(playbooks)))
    commands = list(filter(None, dict.fromkeys(commands)))
    scripts = list(filter(None, dict.fromkeys(scripts)))

    return playbooks, integrations, scripts, commands


def get_inputs(playbook):
    errors = []
    inputs = []

    if not playbook.get('inputs'):
        return {}, []

    for _input in playbook.get('inputs'):
        if not _input.get('description'):
            errors.append(
                'Error! You are missing description in playbook input {}'.format(_input.get('key')))

        required_status = 'Required' if _input.get('required') else 'Optional'
        _value, source = get_input_data(_input)

        inputs.append({
            'Name': _input['key'],
            'Description': stringEscapeMD(_input.get('description', '')),
            'Default Value': _value,
            'Source': source,
            'Required': required_status,
        })

    return inputs, errors


def get_outputs(playbook):
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
            'Description': stringEscapeMD(output.get('description', '')),
            'Type': output_type
        })

    return outputs, errors


def get_input_data(input_section):
    default_value = input_section.get('value')

    if default_value:
        complex = default_value.get('complex')
        if complex:
            return complex.get('accessor'), complex.get('root')
        return default_value.get('simple'), ''

    return '', ''


def stringEscapeMD(st, minimal_escaping=False, escape_multiline=False):
    """
       Escape any chars that might break a markdown string

       :type st: ``str``
       :param st: The string to be modified (required)

       :type minimal_escaping: ``bool``
       :param minimal_escaping: Whether replace all special characters or table format only (optional)

       :type escape_multiline: ``bool``
       :param escape_multiline: Whether convert line-ending characters (optional)

       :return: A modified string
       :rtype: ``str``
    """
    if escape_multiline:
        st = st.replace('\r\n', '<br>')  # Windows
        st = st.replace('\r', '<br>')  # old Mac
        st = st.replace('\n', '<br>')  # Unix

    if minimal_escaping:
        for c in '|':
            st = st.replace(c, '\\' + c)
    else:
        st = "".join(["\\" + str(c) if c in r"\`*_{}[]()#+-!" else str(c) for c in st])

    return st
