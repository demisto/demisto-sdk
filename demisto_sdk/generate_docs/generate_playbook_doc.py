from demisto_sdk.generate_docs.common import *


def generate_playbook_doc(input, output, commands, id_set, verbose=False):
    try:
        playbook = get_yaml(input)
        errors = []

        description = playbook.get('description', '')

        if not description:
            errors.append('Error! You are missing description for the playbook')

        doc = [description, '', '## Dependencies', 'This playbook uses the following sub-playbooks, integrations, and scripts.', '']

        playbooks, integrations, scripts, commands = get_playbook_dependencies(playbook)
        inputs, inputs_errors = get_inputs(playbook)
        outputs, outputs_errors = get_outputs(playbook)

        errors.extend(inputs_errors)
        errors.extend(outputs_errors)

        doc.extend(generate_list_section('Sub-playbooks', playbooks, 'This playbook does not use any sub-playbooks.'))

        doc.extend(generate_list_section('Integrations', integrations, 'This playbook does not use any integrations.'))

        doc.extend(generate_list_section('Scripts', scripts, 'This playbook does not use any scripts.'))

        doc.extend(generate_list_section('Commands', commands, 'This playbook does not use any commands.'))

        doc.extend(generate_table_section(inputs, 'Playbook Inputs', 'There are no inputs for this playbook.'))

        doc.extend(generate_table_section(outputs, 'Playbook Outputs', 'There are no outputs for this playbook.'))

        doc.append('<!-- Playbook PNG image comes here -->')

        doc_text = '\n'.join(doc)

        save_output(output, 'README.md', doc_text)

        if errors:
            print_error('Possible Errors:')
            for error in errors:
                print_error(error)

    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            return


def get_playbook_dependencies(playbook):
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

    # delete duplicates from list
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
            'Name': _input.get('key'),
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

