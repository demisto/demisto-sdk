import os.path
import re
from typing import Any, Dict, List, Optional, Tuple

from demisto_sdk.commands.common.constants import (
    CONTEXT_OUTPUT_README_TABLE_HEADER, DOCS_COMMAND_SECTION_REGEX)
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_yaml,
                                               print_color, print_error,
                                               print_warning)
from demisto_sdk.commands.generate_docs.common import (
    add_lines, build_example_dict, generate_numbered_section, generate_section,
    generate_table_section, save_output, string_escape_md)
from demisto_sdk.commands.integration_diff.integration_diff_detector import \
    IntegrationDiffDetector

CREDENTIALS = 9


def append_or_replace_command_in_docs(old_docs: str, new_doc_section: str, command_name: str) -> Tuple[str, list]:
    """ Replacing a command in a README.md file with a new string.

    Args:
        old_docs: the old docs string
        new_doc_section: the new string to replace
        command_name: the command name itself

    Returns:
        str: The whole documentation.
    """
    regexp = DOCS_COMMAND_SECTION_REGEX.format(command_name)
    # Read doc content
    errs = list()
    if re.findall(regexp, old_docs, flags=re.DOTALL):
        new_docs = re.sub(regexp, new_doc_section, old_docs, flags=re.DOTALL)
        print_color('New command docs has been replaced in README.md.', LOG_COLORS.GREEN)
    else:
        if command_name in old_docs:
            errs.append(f'Could not replace the command `{command_name}` in the file although it'
                        f' is presented in the file.'
                        'Copy and paste it in the appropriate spot.')
        if old_docs.endswith('\n'):
            # Remove trailing '\n'
            old_docs = old_docs[:-1]
        new_docs = f'{old_docs}\n{new_doc_section}'
        print_color('New command docs has been added to the README.md.', LOG_COLORS.GREEN)
    return new_docs, errs


def generate_integration_doc(
        input_path: str,
        examples: Optional[str] = None,
        output: Optional[str] = None,
        use_cases: Optional[str] = None,
        permissions: Optional[str] = None,
        command_permissions: Optional[str] = None,
        limitations: Optional[str] = None,
        insecure: bool = False,
        verbose: bool = False,
        command: Optional[str] = None,
        input_old_version: str = '',
        skip_breaking_changes: bool = False):
    """ Generate integration documentation.

    Args:
        input_path: path to the yaml integration
        examples: path to the command examples
        output: path to the output documentation
        use_cases: use cases string
        permissions: global permissions for the docs
        command_permissions: permissions per command
        limitations: limitations description
        insecure: should use insecure
        verbose: verbose (debug mode)
        command: specific command to generate docs for

    """
    try:
        yml_data = get_yaml(input_path)

        if not output:  # default output dir will be the dir of the input file
            output = os.path.dirname(os.path.realpath(input_path))
        errors: list = []
        example_dict = {}
        if examples and os.path.isfile(examples):
            specific_commands = command.split(',') if command else None
            command_examples = get_command_examples(examples, specific_commands)
            example_dict, build_errors = build_example_dict(command_examples, insecure)
            errors.extend(build_errors)
        else:
            errors.append(f'Command examples was not found {examples}.')

        if permissions == 'per-command':
            command_permissions_dict: Any = {}
            if command_permissions and os.path.isfile(command_permissions):
                permission_list = get_command_permissions(command_permissions)
                for command_permission in permission_list:
                    # get all the permissions after the command name
                    key, value = command_permission.split(" ", 1)
                    command_permissions_dict.update({key: value})
            else:
                errors.append(f'Command permissions was not found {command_permissions}.')
        else:  # permissions in ['none', 'general']
            command_permissions_dict = None
        if command:
            specific_commands = command.split(',')
            readme_path = os.path.join(output, 'README.md')
            with open(readme_path) as f:
                doc_text = f.read()
            for specific_command in specific_commands:
                print(f'Generating docs for command `{specific_command}`')
                command_section, command_errors = generate_commands_section(
                    yml_data, example_dict,
                    command_permissions_dict, command=specific_command
                )
                command_section_str = '\n'.join(command_section)
                doc_text, err = append_or_replace_command_in_docs(doc_text, command_section_str, specific_command)
                errors.extend(err)
        else:
            docs = []  # type: list
            docs.extend(add_lines(yml_data.get('description')))
            docs.extend(['This integration was integrated and tested with version xx of {}'.format(yml_data['name']), ''])
            # Checks if the integration is a new version
            integration_version = re.findall("[vV][2-9]$", yml_data.get("display", ""))
            if integration_version and not skip_breaking_changes:
                docs.extend(['Some changes have been made that might affect your existing content. '
                             '\nIf you are upgrading from a previous of this integration, see [Breaking Changes]'
                             '(#breaking-changes-from-the-previous-version-of-this-integration-'
                             f'{yml_data.get("display", "").replace(" ", "-").lower()}).', ''])
            # Integration use cases
            if use_cases:
                docs.extend(generate_numbered_section('Use Cases', use_cases))
            # Integration general permissions
            if permissions == 'general':
                docs.extend(generate_section('Permissions', ''))
            # Setup integration to work with Demisto
            docs.extend(generate_section('Configure {} on Cortex XSOAR'.format(yml_data['name']), ''))
            # Setup integration on Demisto
            docs.extend(generate_setup_section(yml_data))
            # Commands
            command_section, command_errors = generate_commands_section(yml_data, example_dict,
                                                                        command_permissions_dict, command=command)
            docs.extend(command_section)
            # breaking changes
            if integration_version and not skip_breaking_changes:
                docs.extend(generate_versions_differences_section(input_path, input_old_version,
                                                                  yml_data.get("display", "")))

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
    access_data: List[Dict] = []

    for conf in yaml_data['configuration']:
        if conf['type'] == CREDENTIALS:
            add_access_data_of_type_credentials(access_data, conf)
        else:
            access_data.append(
                {'Parameter': conf.get('display'),
                 'Description': string_escape_md(conf.get('additionalinfo', '')),
                 'Required': conf.get('required', '')})

    # Check if at least one parameter has additional info field.
    # If not, remove the description column from the access data table section.
    access_data_with_description = list(filter(lambda x: x.get('Description', '') != '', access_data))
    if len(access_data_with_description) == 0:
        list(map(lambda x: x.pop('Description'), access_data))

    section.extend(generate_table_section(access_data, '', horizontal_rule=False, numbered_section=True))
    section.append('4. Click **Test** to validate the URLs, token, and connection.')

    return section


# Commands
def generate_commands_section(
        yaml_data: dict,
        example_dict: dict,
        command_permissions_dict: dict,
        command: Optional[str] = None
) -> Tuple[list, list]:
    """Generate the commands section the the README.md file.

    Arguments:
        yaml_data (dict): The data of the .yml file (integration or script)
        example_dict (dict): Examples of running commands.
        command_permissions_dict (dict): Permission needed per command
        command (Optional[str]): A specific command to run on. will return the command itself without the section header.

    Returns:
        [str, str] -- [commands section, errors]
    """
    errors = []  # type: list
    section = [
        '## Commands',
        'You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.'
    ]
    commands = filter(lambda cmd: not cmd.get('deprecated', False), yaml_data['script']['commands'])
    command_sections: list = []
    if command:
        # for specific command, return it only.
        try:
            command_dict = list(filter(lambda cmd: cmd['name'] == command, commands))[0]
        except IndexError:
            err = f'Could not find the command `{command}` in the .yml file.'
            print_error(err)
            raise IndexError(err)
        return generate_single_command_section(command_dict, example_dict, command_permissions_dict)
    for cmd in commands:
        cmd_section, cmd_errors = generate_single_command_section(cmd, example_dict, command_permissions_dict)
        command_sections.extend(cmd_section)
        errors.extend(cmd_errors)

    section.extend(command_sections)
    return section, errors


def generate_single_command_section(cmd: dict, example_dict: dict, command_permissions_dict):
    errors = []
    cmd_example = example_dict.get(cmd['name'])
    if command_permissions_dict:
        if command_permissions_dict.get(cmd['name']):
            cmd_permission_example = ['#### Required Permissions', command_permissions_dict.get(cmd['name'])]
        else:
            errors.append(f"Error! Command Permissions were not found for command {cmd['name']}")
            cmd_permission_example = ['#### Required Permissions', '']
    elif isinstance(command_permissions_dict, dict) and not command_permissions_dict:
        cmd_permission_example = ['#### Required Permissions', '**FILL IN REQUIRED PERMISSIONS HERE**']
    else:  # no permissions for this command
        cmd_permission_example = ['', '']

    section = [
        '### {}'.format(cmd['name']),
        '***',
        cmd.get('description', ' '),
        cmd_permission_example[0],
        cmd_permission_example[1],
        '#### Base Command',
        '', '`{}`'.format(cmd['name']),
        '#### Input',
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
            description = arg.get('description')
            if not description:
                errors.append(
                    'Error! You are missing description in input {} of command {}'.format(arg['name'], cmd['name']))
            if not description.endswith('.'):
                description = f'{description}.'

            argument_description = f'{description} Possible values are: {", ".join(arg.get("predefined"))}.' \
                if arg.get('predefined') else description
            if arg.get('defaultValue'):
                argument_description = f'{argument_description} Default is {arg.get("defaultValue")}.'

            required_status = 'Required' if arg.get('required') else 'Optional'
            section.append('| {} | {} | {} | '.format(arg['name'], string_escape_md(argument_description,
                                                                                    True, True), required_status))
        section.append('')

    # Context output
    section.extend([
        '',
        '#### Context Output',
        '',
    ])
    outputs = cmd.get('outputs')
    if outputs is None:
        section.append('There is no context output for this command.')
    else:
        section.extend([
            CONTEXT_OUTPUT_README_TABLE_HEADER,
            '| --- | --- | --- |'
        ])
        for output in outputs:
            if not output.get('description'):
                errors.append(
                    'Error! You are missing description in output {} of command {}'.format(output['contextPath'],
                                                                                           cmd['name']))
            section.append(
                '| {} | {} | {} | '.format(output['contextPath'], output.get('type', 'unknown'),
                                           string_escape_md(output.get('description', ''))))
        section.append('')

    # Raw output:
    example_section, example_errors = generate_command_example(cmd, cmd_example)
    section.extend(example_section)
    errors.extend(example_errors)

    return section, errors


def generate_versions_differences_section(input_path, input_old_version, display_name) -> list:
    """
    Generate the version differences section to the README.md file.

    Arguments:
        input_path : The integration file path.

    Returns:
        List of the section lines.
    """

    differences_section = [
        f'## Breaking changes from the previous version of this integration - {display_name}',
        '%%FILL HERE%%',
        'The following sections list the changes in this version.',
        ''
    ]

    if not input_old_version:
        user_response = str(input('Enter the path of the previous integration version file if any. Press Enter to skip.\n'))

        if user_response:
            input_old_version = user_response

    if input_old_version:
        differences = get_previous_version_differences(input_path, input_old_version)

        if differences[0] != '':
            differences_section.extend(differences)

        else:
            # If there are no differences, remove the headers.
            differences_section = []

    else:

        differences_section.extend(['### Commands',
                                    '#### The following commands were removed in this version:',
                                    '* *commandName* - this command was replaced by XXX.',
                                    '* *commandName* - this command was replaced by XXX.',
                                    '',
                                    '### Arguments',
                                    '#### The following arguments were removed in this version:',
                                    '',
                                    'In the *commandName* command:',
                                    '* *argumentName* - this argument was replaced by XXX.',
                                    '* *argumentName* - this argument was replaced by XXX.',
                                    '',
                                    '#### The behavior of the following arguments was changed:',
                                    '',
                                    'In the *commandName* command:',
                                    '* *argumentName* - is now required.',
                                    '* *argumentName* - supports now comma separated values.',
                                    '',
                                    '### Outputs',
                                    '#### The following outputs were removed in this version:',
                                    '',
                                    'In the *commandName* command:',
                                    '* *outputPath* - this output was replaced by XXX.',
                                    '* *outputPath* - this output was replaced by XXX.',
                                    '',
                                    'In the *commandName* command:',
                                    '* *outputPath* - this output was replaced by XXX.',
                                    '* *outputPath* - this output was replaced by XXX.',
                                    ''])

    differences_section.extend(['## Additional Considerations for this version', '%%FILL HERE%%',
                                '* Insert any API changes, any behavioral changes, limitations, or restrictions '
                                'that would be new to this version.', ''])

    return differences_section


def get_previous_version_differences(new_integration_path, previous_integration_path) -> list:
    """
    Gets the section of the previous integration version differences.

    Args:
        new_integration_path: The new integration path.
        previous_integration_path: The old integration path.

    Return:
        List of the differences section lines.
    """

    differences_detector = IntegrationDiffDetector(new=new_integration_path, old=previous_integration_path)
    differences_detector.missing_items_report = differences_detector.get_differences()

    differences_section = [differences_detector.print_items_in_docs_format(secho_result=False)]

    return differences_section


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
        '#### Command Example',
        '```{}```'.format(cmd_example),
        '',
    ]
    if context_example and context_example != '{}':
        example.extend([
            '#### Context Example',
            '```json',
            '{}'.format(context_example),
            '```',
            '',
        ])
    example.extend([
        '#### Human Readable Output',
        '{}'.format('>'.join(f'\n{md_example}'.splitlines(True))),  # prefix human readable with quote
        '',
    ])

    return example, errors


def get_command_examples(commands_file_path, specific_commands):
    """
    get command examples from command file

    @param commands_file_path: command file or the content of such file
    @param specific_commands: commands specified by the user

    @return: a list of command examples
    """
    command_examples = []  # type: list

    if commands_file_path is None:
        return command_examples

    if os.path.isfile(commands_file_path):
        with open(commands_file_path, 'r') as examples_file:
            command_examples = examples_file.read().splitlines()
    else:
        print('failed to open command file')
        command_examples = commands_file_path.split('\n')

    # Filter from the examples only the commands specified by the user
    commands = []
    if specific_commands:
        for command_ex in command_examples:
            if command_ex.split(' ')[0].strip('!') in specific_commands:
                commands.append(command_ex)
    else:
        commands = command_examples

    commands: list = list(filter(None, map(command_example_filter, commands)))

    print('found the following commands:\n{}'.format('\n'.join(commands)))
    return commands


def command_example_filter(command):
    if command.startswith('#'):
        return
    elif not command.startswith('!'):
        return f'!{command}'
    return command


def get_command_permissions(commands_permissions_file_path) -> list:
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

    permissions_map = map(command_permissions_filter, permissions)
    permissions_list: List = list(filter(None, permissions_map))

    print('found the following commands permissions:\n{}'.format('\n '.join(permissions_list)))
    return permissions_list


def command_permissions_filter(permission):
    if permission.startswith('#'):
        return
    elif permission.startswith('!'):
        return f'{permission}'
    return permission


def add_access_data_of_type_credentials(access_data: List[Dict], credentials_conf: Dict) -> None:
    """
    Adds to 'access_data' the parameter data of credentials configuration parameter.
    Args:
        access_data (List[Dict]): Access data to add the credentials conf data to.
        credentials_conf (Dict): Credentials conf data.

    Returns:
        (None): Adds the data to 'access_data'.
    """
    display_name = credentials_conf.get('display')
    if display_name:
        access_data.append(
            {'Parameter': display_name,
             'Description': string_escape_md(credentials_conf.get('additionalinfo', '')),
             'Required': credentials_conf.get('required', '')})
    access_data.append(
        {'Parameter': credentials_conf.get('displaypassword', 'Password'),
         'Description': '' if display_name else string_escape_md(credentials_conf.get('additionalinfo', '')),
         'Required': credentials_conf.get('required', '')})
