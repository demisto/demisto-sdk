from demisto_sdk.commands.run_cmd.runner import Runner
from demisto_sdk.commands.generate_docs.common import *

STRING_TYPES = (str, bytes)  # type: ignore


def generate_integration_doc(input, output, commands, id_set, verbose=False):
    try:
        yml_data = get_yaml(input)

        errors = []
        command_examples = get_command_examples(commands)
        example_dict, build_errors = build_example_dict(command_examples)
        errors.extend(build_errors)

        docs = []  # type: list
        docs.extend(add_lines(yml_data.get('description')))
        docs.append('This integration was integrated and tested with version xx of {}'.format(yml_data['name']))
        # Playbooks
        docs.extend(generate_section('{} Playbook'.format(yml_data['name']), None))
        # Use-cases
        docs.extend(generate_section('Use Cases', ''))
        # Setup integration to work with Demisto
        docs.extend(generate_section('Configure {} on Demisto'.format(yml_data['name']), ''))
        # Setup integration on Demisto
        docs.extend(generate_setup_section(yml_data))
        # Fetched incidents data
        docs.extend(generate_section('Fetched Incidents Data', ''))
        # Commands
        command_section, command_errors = generate_commands_section(yml_data, example_dict)
        docs.extend(command_section)
        errors.extend(command_errors)
        # Additional info
        docs.extend(generate_section('Additional Information', ''))
        # Known limitations
        docs.extend(generate_section('Known Limitations', ''))
        # Troubleshooting
        docs.extend(generate_section('Troubleshooting', ''))

        doc_text = '\n'.join(docs)

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


# Setup integration on Demisto
def generate_setup_section(yaml_data):
    section = [
        '1. Navigate to __Settings__ > __Integrations__ > __Servers & Services__.',
        '2. Search for {}.'.format(yaml_data['name']),
        '3. Click __Add instance__ to create and configure a new integration instance.',
        '    * __Name__: a textual name for the integration instance.',
    ]
    for conf in yaml_data['configuration']:
        if conf.get('display', ''):
            section.append('    * __{}__'.format(conf['display']))
        else:
            section.append('    * __{}__'.format(conf['name']))
    section.append('4. Click __Test__ to validate the URLs, token, and connection.')

    return section


# Commands
def generate_commands_section(yaml_data, example_dict):
    errors = []  # type: list
    section = [
        '## Commands',
        '---',
        'You can execute these commands from the Demisto CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.'
    ]
    commands = filter(lambda cmd: not cmd.get('deprecated', False), yaml_data['script']['commands'])

    command_list = []
    command_sections = []

    for i, cmd in enumerate(commands):
        command_list.append('{}. {}'.format(i + 1, cmd['name']))
        cmd_section, cmd_errors = generate_single_command_section(i, cmd, example_dict)
        command_sections.extend(cmd_section)
        errors.extend(cmd_errors)

    section.extend(command_list)
    section.extend(command_sections)
    return section, errors


def generate_single_command_section(index, cmd, example_dict):
    cmd_example = example_dict.get(cmd['name'])
    errors = []
    section = [
        '### {}. {}'.format(index + 1, cmd['name']),
        '---',
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
                                           output.get('description').encode('utf-8')))
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
        '### Human Readable Output',
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
        print('failed to open command file, tried parsing as free text')
        commands = commands_file_path.split('\n')

    print('found the following commands:\n{}'.format('\n '.join(commands)))
    return commands


def build_example_dict(command_examples):
    """
    gets an array of command examples, run them one by one and return a map of
        {base command -> (example command, markdown, outputs)}
    Note: if a command appears more then once, run all occurrences but stores only the first.
    """
    examples = {}  # type: dict
    errors = []  # type: list
    for example in command_examples:
        # ignore comment lines
        if example.startswith('#'):
            continue
        if not example.startswith('!'):
            example = f'!{example}'
        cmd, md_example, context_example, cmd_errors = run_command(example)
        errors.extend(cmd_errors)

        if cmd not in examples:
            examples[cmd] = (example, md_example, context_example)
    return examples, errors


def run_command(command_example):
    errors = []
    context_example = ''
    md_example = ''
    cmd = command_example
    try:
        runner = Runner('')
        res, raw_context = runner.execute_command(command_example)

        for entry in res:
            if is_error(entry):
                raise RuntimeError('something went wrong with your command: {}'.format(command_example))

            if raw_context:
                context = {k.split('(')[0]: v for k, v in raw_context.items()}
                context_example += json.dumps(context, indent=4)

            if entry.contents:
                content = entry.contents
                if isinstance(content, STRING_TYPES):
                    md_example += content
                else:
                    md_example += json.dumps(content)

    except RuntimeError:
        errors.append('The provided example for cmd {} has failed...'.format(cmd))

    except Exception as e:
        errors.append(
            'Error encountered in the processing of command {}, error was: {}. '.format(cmd, str(e)) +
            '. Please check your command inputs and outputs')

    cmd = cmd.split(' ')[0][1:]
    return cmd, md_example, context_example, errors


def is_error(execute_command_result):
    """
        Check if the given execute_command_result has an error entry

        :type execute_command_result: ``dict`` or ``list``
        :param execute_command_result: Demisto entry (required) or result of demisto.executeCommand()

        :return: True if the execute_command_result has an error entry, false otherwise
        :rtype: ``bool``
    """
    if not execute_command_result:
        return False

    if isinstance(execute_command_result, list):
        if len(execute_command_result) > 0:
            for entry in execute_command_result:
                if type(entry) == dict and entry['Type'] == entryTypes['error']:
                    return True

    return type(execute_command_result) == dict and execute_command_result['Type'] == entryTypes['error']


entryTypes = {
    'note': 1,
    'downloadAgent': 2,
    'file': 3,
    'error': 4,
    'pinned': 5,
    'userManagement': 6,
    'image': 7,
    'plagroundError': 8,
    'playgroundError': 8,
    'entryInfoFile': 9,
    'warning': 11,
    'map': 15,
    'widget': 17
}
