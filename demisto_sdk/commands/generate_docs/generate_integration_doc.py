import os.path
from demisto_sdk.commands.common.tools import get_yaml, print_warning, print_error
from demisto_sdk.commands.generate_docs.common import build_example_dict, add_lines, generate_section, \
    save_output, generate_table_section, stringEscapeMD, generate_numbered_section


def generate_integration_doc(input, examples, output: str = None, use_cases: str = None,
                             permissions: str = None, command_permissions: str = None,
                             limitations: str = None, insecure: bool = False, verbose: bool = False):
    try:
        yml_data = get_yaml(input)

        if not output:  # default output dir will be the dir of the input file
            output = os.path.dirname(os.path.realpath(input))

        errors = []
        example_dict = {}
        if examples and os.path.isfile(examples):
            command_examples = get_command_examples(examples)
            example_dict, build_errors = build_example_dict(command_examples, insecure)
            errors.extend(build_errors)
        else:
            errors.append(f'Command examples was not found {examples}.')

        if permissions == 'per-command':
            command_permissions_dict = {}
            if command_permissions and os.path.isfile(command_permissions):
                command_permissions = get_command_permissions(command_permissions)
                for command_permission in command_permissions:
                    # get all the permissions after the command name
                    key, value = command_permission.split(" ", 1)
                    command_permissions_dict.update({key: value})
            else:
                errors.append(f'Command permissions was not found {command_permissions}.')
        else:  # permissions in ['none', 'general']
            command_permissions_dict = None

        docs = []  # type: list
        docs.extend(add_lines(yml_data.get('description')))
        docs.extend('This integration was integrated and tested with version xx of {}'.format(yml_data['name']))

        # Integration use cases
        if use_cases:
            docs.extend(generate_numbered_section('Use Cases', use_cases))
        # Integration general permissions
        if permissions == 'general':
            docs.extend(generate_section('Permissions', ''))
        # Setup integration to work with Demisto
        docs.extend(generate_section('Configure {} on Demisto'.format(yml_data['name']), ''))
        # Setup integration on Demisto
        docs.extend(generate_setup_section(yml_data))
        # Commands
        command_section, command_errors = generate_commands_section(yml_data, example_dict, command_permissions_dict)
        docs.extend(command_section)
        errors.extend(command_errors)
        # Known limitations
        if limitations:
            docs.extend(generate_numbered_section('Known Limitations', limitations))

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
def generate_setup_section(yaml_data: dict):
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
def generate_commands_section(yaml_data: dict, example_dict: dict, command_permissions_dict):
    errors = []  # type: list
    section = [
        '## Commands',
        'You can execute these commands from the Demisto CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.'
    ]
    commands = filter(lambda cmd: not cmd.get('deprecated', False), yaml_data['script']['commands'])
    command_sections = []

    for i, cmd in enumerate(commands):
        cmd_section, cmd_errors = generate_single_command_section(cmd, example_dict, command_permissions_dict)
        command_sections.extend(cmd_section)
        errors.extend(cmd_errors)

    section.extend(command_sections)
    return section, errors


def generate_single_command_section(cmd: dict, example_dict: dict, command_permissions_dict):
    cmd_example = example_dict.get(cmd['name'])
    if command_permissions_dict:
        cmd_permission_example = ['##### Required Permissions', command_permissions_dict.get(cmd['name'])]
    elif isinstance(command_permissions_dict, dict) and not command_permissions_dict:
        cmd_permission_example = ['##### Required Permissions', '**FILL IN REQUIRED PERMISSIONS HERE**']
    else:  # no permissions for this command
        cmd_permission_example = ['', '']

    errors = []
    section = [
        '### {}'.format(cmd['name']),
        '***',
        cmd.get('description', ' '),
        cmd_permission_example[0],
        cmd_permission_example[1],
        '##### Base Command',
        '', '`{}`'.format(cmd['name']),
        '##### Input',
        ''
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


def get_command_permissions(commands_permissions_file_path):
    """
    get command permissions from file

    @param commands_permissions_file_path: command permissions file or the content of such file

    @return: a list of command permissions
    """
    commands_permissions = []  # type: list

    if commands_permissions_file_path is None:
        return commands_permissions

    if os.path.isfile(commands_permissions_file_path):
        with open(commands_permissions_file_path, 'r') as permissions_file:
            permissions = permissions_file.read().splitlines()
    else:
        print('failed to open permissions file')
        permissions = commands_permissions_file_path.split('\n')

    permissions = map(command_permissions_filter, permissions)
    permissions = list(filter(None, permissions))

    print('found the following commands permissions:\n{}'.format('\n '.join(permissions)))
    return permissions


def command_permissions_filter(permission):
    if permission.startswith('#'):
        return
    elif permission.startswith('!'):
        return f'{permission}'
    return permission
