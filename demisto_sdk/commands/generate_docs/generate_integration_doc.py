import os.path
from demisto_sdk.commands.common.tools import get_yaml, print_warning, print_error
from demisto_sdk.commands.generate_docs.common import build_example_dict, add_lines, generate_section,\
    save_output, generate_table_section, stringEscapeMD


def generate_integration_doc(input, output, examples, id_set, verbose=False):
    try:
        yml_data = get_yaml(input)

        errors = []
        example_dict = {}
        if examples and os.path.isfile(examples):
            command_examples = get_command_examples(examples)
            example_dict, build_errors = build_example_dict(command_examples)
            errors.extend(build_errors)
        else:
            errors.append(f'Command examples was not found {examples}.')

        docs = []  # type: list
        docs.extend(add_lines(yml_data.get('description')))
        docs.append('This integration was integrated and tested with version xx of {}'.format(yml_data['name']))
        # Setup integration to work with Demisto
        docs.extend(generate_section('Configure {} on Demisto'.format(yml_data['name']), ''))
        # Setup integration on Demisto
        docs.extend(generate_setup_section(yml_data))
        # Commands
        command_section, command_errors = generate_commands_section(yml_data, example_dict)
        docs.extend(command_section)
        errors.extend(command_errors)
        # Additional info
        docs.extend(generate_section('Additional Information', ''))
        # Known limitations
        docs.extend(generate_section('Known Limitations', ''))

        doc_text = '\n'.join(docs)

        save_output(output, 'README.md', doc_text)

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


# Setup integration on Demisto
def generate_setup_section(yaml_data):
    section = [
        '1. Navigate to **Settings** > **Integrations** > **Servers & Services**.',
        '2. Search for {}.'.format(yaml_data['name']),
        '3. Click **Add instance** to create and configure a new integration instance.'
    ]
    access_data = []

    for conf in yaml_data['configuration']:
        access_data.append(
            {'Parameter': conf.get('name', ''),
             'Description': conf.get('display', ''),
             'Required': conf.get('required', '')})

    section.extend(generate_table_section(access_data, '', horizontal_rule=False))
    section.append('4. Click **Test** to validate the URLs, token, and connection.')

    return section


# Commands
def generate_commands_section(yaml_data, example_dict):
    errors = []  # type: list
    section = [
        '## Commands',
        'You can execute these commands from the Demisto CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.'
    ]
    commands = filter(lambda cmd: not cmd.get('deprecated', False), yaml_data['script']['commands'])

    command_sections = []

    for i, cmd in enumerate(commands):
        cmd_section, cmd_errors = generate_single_command_section(i, cmd, example_dict)
        command_sections.extend(cmd_section)
        errors.extend(cmd_errors)

    section.extend(command_sections)
    return section, errors


def generate_single_command_section(index, cmd, example_dict):
    cmd_example = example_dict.get(cmd['name'])
    errors = []
    section = [
        '### {}'.format(cmd['name']),
        '***',
        cmd.get('description', ' '),
        '##### Required Permissions',
        '**FILL IN REQUIRED PERMISSIONS HERE**',
        '##### Base Command',
        '',
        '`{}`'.format(cmd['name']),
        '##### Input',
        '',
    ]

    # Inputs
    arguments = cmd.get('arguments')
    if arguments is None:
        section.append('There are no input arguments for this command.')
    else:
        section.extend([
            '| **Argument Name** | **Description** | **Required** |',
            '| --- | --- | --- |',
        ])
        for arg in arguments:
            if not arg.get('description'):
                errors.append(
                    'Error! You are missing description in input {} of command {}'.format(arg['name'], cmd['name']))
            required_status = 'Required' if arg.get('required') else 'Optional'
            section.append('| {} | {} | {} | '.format(arg['name'], stringEscapeMD(arg.get('description', ''),
                                                                                  True, True), required_status))
        section.append('')

    # Context output
    section.extend([
        '',
        '##### Context Output',
        '',
    ])
    outputs = cmd.get('outputs')
    if outputs is None:
        section.append('There is no context output for this command.')
    else:
        section.extend([
            '| **Path** | **Type** | **Description** |',
            '| --- | --- | --- |'
        ])
        for output in outputs:
            if not output.get('description'):
                errors.append(
                    'Error! You are missing description in output {} of command {}'.format(output['contextPath'],
                                                                                           cmd['name']))
            section.append(
                '| {} | {} | {} | '.format(output['contextPath'], output.get('type', 'unknown'),
                                           output.get('description')))
        section.append('')

    # Raw output:
    example_section, example_errors = generate_command_example(cmd, cmd_example)
    section.extend(example_section)
    errors.extend(example_errors)

    return section, errors


def generate_command_example(cmd, cmd_example=None):
    errors = []
    context_example = None
    md_example = ''
    if cmd_example is not None:
        cmd_example, md_example, context_example = cmd_example
    else:
        cmd_example = ' '
        errors.append('did not get any example for {}. please add it manually.'.format(cmd['name']))

    example = [
        '',
        '##### Command Example',
        '```{}```'.format(cmd_example),
        '',
    ]
    if context_example:
        example.extend([
            '##### Context Example',
            '```',
            '{}'.format(context_example),
            '```',
            '',
        ])
    example.extend([
        '##### Human Readable Output',
        '{}'.format(md_example),
        '',
    ])

    return example, errors


def get_command_examples(commands_file_path):
    """
    get command examples from command file

    @param commands_file_path: command file or the content of such file

    @return: a list of command examples
    """
    commands = []  # type: list

    if commands_file_path is None:
        return commands

    if os.path.isfile(commands_file_path):
        with open(commands_file_path, 'r') as examples_file:
            commands = examples_file.read().splitlines()
    else:
        print('failed to open command file')
        commands = commands_file_path.split('\n')

    commands = map(command_example_filter, commands)
    commands = list(filter(None, commands))

    print('found the following commands:\n{}'.format('\n '.join(commands)))
    return commands


def command_example_filter(command):
    if command.startswith('#'):
        return
    elif not command.startswith('!'):
        return f'!{command}'
    return command
