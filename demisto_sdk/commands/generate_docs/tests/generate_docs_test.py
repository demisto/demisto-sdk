import json
import os
from typing import Dict, List

import pytest

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_json, get_yaml
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    append_or_replace_command_in_docs, disable_md_autolinks,
    generate_commands_section, generate_integration_doc,
    generate_setup_section, generate_single_command_section,
    get_command_examples)
from demisto_sdk.commands.generate_docs.generate_script_doc import \
    generate_script_doc

FILES_PATH = os.path.normpath(os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files'))
FAKE_ID_SET = get_json(os.path.join(FILES_PATH, 'fake_id_set.json'))
TEST_PLAYBOOK_PATH = os.path.join(FILES_PATH, 'playbook-Test_playbook.yml')
TEST_SCRIPT_PATH = os.path.join(FILES_PATH, 'script-test_script.yml')
TEST_INTEGRATION_PATH = os.path.join(FILES_PATH, 'fake_integration/fake_integration.yml')
TEST_INTEGRATION_2_PATH = os.path.join(FILES_PATH, 'integration-display-credentials-none/integration-display'
                                                   '-credentials-none.yml')


# common tests


def test_format_md():
    """
        Given
            - A string representing a markdown returned from server with <br> tag

        When
            - generating docs

        Then
            - Ensure all <br> <BR> tags in markdown replaced with <br/> tags
        """
    from demisto_sdk.commands.generate_docs.common import format_md
    md_returned_from_server = """
    ### Domain List
    |Malicious|Name|
    |---|---|
    | Vendor: HelloWorld<br>Description: Hello World returned reputation 88 | google.com |
    | Vendor: HelloWorld<BR>Description: Hello World returned reputation 88 | google.com |
    """
    res = format_md(md_returned_from_server)
    expected_res = """
    ### Domain List
    |Malicious|Name|
    |---|---|
    | Vendor: HelloWorld<br/>Description: Hello World returned reputation 88 | google.com |
    | Vendor: HelloWorld<br/>Description: Hello World returned reputation 88 | google.com |
    """
    assert expected_res == res
    # mixed case test
    assert '<bR>' not in format_md('test<bR>')
    assert '<HR>' not in format_md('test<HR>')
    # these are a valid but we replace for completeness
    assert format_md('test<br></br>\nthis<br>again').count('<br/>') == 2
    assert format_md('test<hr></hr>\nthis<hr>again').count('<hr/>') == 2
    # test removing style
    assert 'style=' not in format_md(
        '<div style="background:#eeeeee; border:1px solid #cccccc; padding:5px 10px">"this is a test"</div>')


def test_string_escape_md():
    from demisto_sdk.commands.generate_docs.common import string_escape_md

    res = string_escape_md('First fetch timestamp (<number> <time unit>, e.g., 12 hours, 7 days)',
                           minimal_escaping=True, escape_multiline=True, escape_less_greater_signs=True)
    assert res == 'First fetch timestamp (`<number>` `<time unit>`, e.g., 12 hours, 7 days)'

    res = string_escape_md("format: <number> <time unit>, e.g., 12 hours, 7 days.",
                           minimal_escaping=True, escape_multiline=True, escape_less_greater_signs=True)
    assert res == "format: `<number>` `<time unit>`, e.g., 12 hours, 7 days."

    res = string_escape_md("new line test \n", escape_multiline=True)
    assert '\n' not in res
    assert '<br/>' in res

    res = string_escape_md('Here are "Double Quotation" marks')
    assert '"' in res

    res = string_escape_md("Here are 'Single Quotation' marks")
    assert "'" in res

    res = string_escape_md('- This _sentence_ has _wrapped_with_underscore_ and _another_ words.')
    assert '\\_wrapped_with_underscore\\_' in res
    assert '\\_sentence\\_' in res
    assert '\\_another\\_' in res
    assert res.startswith('\\-')


def test_generate_list_section_empty():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section('Inputs', [], empty_message='No inputs found.')

    expected_section = [
        '## Inputs', 'No inputs found.', '']

    assert section == expected_section


def test_generate_numbered_section():
    from demisto_sdk.commands.generate_docs.common import \
        generate_numbered_section

    section = generate_numbered_section('Use Cases', '* Drink coffee. * Write code.')

    expected_section = [
        '## Use Cases', '1. Drink coffee.', '2. Write code.']

    assert section == expected_section


def test_generate_list_section():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section('Inputs', ['item1', 'item2'], False, 'No inputs found.')

    expected_section = [
        '## Inputs', '* item1', '* item2', '']

    assert section == expected_section


def test_generate_list_with_text_section():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section('Inputs', ['item1', 'item2'], True, 'No inputs found.', 'some text')

    expected_section = [
        '## Inputs', '---', 'some text', '* item1', '* item2', '']

    assert section == expected_section


def test_generate_table_section_empty():
    """Unit test
    Given
    - generate_table_section command
    - script empty metadata
    When
    - running the command on the inputs
    Then
    - Validate That the script metadata was created correctly.
    """
    from demisto_sdk.commands.generate_docs.common import \
        generate_table_section

    section = generate_table_section([], 'Script Data', 'No data found.', 'This is the metadata of the script.')

    expected_section = [
        '## Script Data', '---', 'No data found.', '']

    assert section == expected_section


def test_generate_table_section():
    """Unit test
    Given
    - generate_table_section command
    - script metadata as a list of dicts
    When
    - running the command on the inputs including a docker image
    Then
    - Validate That the script metadata was created correctly.
    """
    from demisto_sdk.commands.generate_docs.common import \
        generate_table_section

    section = generate_table_section([{'Type': 'python2', 'Docker Image': 'demisto/python2'}],
                                     'Script Data', 'No data found.', 'This is the metadata of the script.')

    expected_section = [
        '## Script Data', '---', 'This is the metadata of the script.',
        '| **Type** | **Docker Image** |', '| --- | --- |', '| python2 | demisto/python2 |', '']

    assert section == expected_section


def test_generate_table_section_with_newlines():
    """Unit test
    Given
    - generate_table_section command
    - inputs as a list of dicts
    When
    - running the command on an input including \n (PcapFilter)
    Then
    - Validate That the \n is escaped correctly in a markdown format.
    """
    from demisto_sdk.commands.generate_docs.common import \
        generate_table_section

    section = generate_table_section([{
        'Name': 'RsaDecryptKeyEntryID',
        'Description': 'This input specifies the file entry id for the RSA decrypt key if the user provided the key'
                       ' in the incident.', 'Default Value': 'File.EntryID', 'Required': 'Optional'},
        {'Name': 'PcapFileEntryID',
         'Description': 'This input specifies the file entry id for the PCAP file if the user provided the file in the'
                        ' incident. One PCAP file can run per incident.',
         'Default Value': 'File.EntryID', 'Required': 'Optional'},
        {'Name': 'WpaPassword',
         'Description': 'This input value is used to provide a WPA \\(Wi\\-Fi Protected Access\\) password to decrypt'
                        ' encrypted 802.11 Wi\\-FI traffic.', 'Default Value': '', 'Required': 'Optional'},
        {'Name': 'PcapFilter',
         'Description': 'This input specifies a search filter to be used on the PCAP file. Filters can be used to'
                        ' search only for a specific IP, protocols and other examples. The syntax is the same as in'
                        ' Wireshark which can be found here:'
                        ' https://www.wireshark.org/docs/man-pages/wireshark-filter.html \nFor this playbook, using'
                        ' a PCAP filter will generate a new smaller PCAP file based on the provided filter therefor'
                        ' thus reducing the extraction of non relevant files.',
         'Default Value': '', 'Required': 'Optional'},
        {'Name': 'ExtractedFilesLimit',
         'Description': 'This input limits the number of files to be extracted from the PCAP file.'
                        ' Default value is 5.', 'Default Value': '5', 'Required': 'Optional'}
    ], 'Playbook Inputs', 'There are no inputs for this playbook.')

    expected_section = [
        '## Playbook Inputs',
        '---',
        '',
        '| **Name** | **Description** | **Default Value** | **Required** |',
        '| --- | --- | --- | --- |',
        '| RsaDecryptKeyEntryID | This input specifies the file entry id for the RSA decrypt key if the user provided'
        ' the key in the incident. | File.EntryID | Optional |',
        '| PcapFileEntryID | This input specifies the file entry id for the PCAP file if the user provided the file in'
        ' the incident. One PCAP file can run per incident. | File.EntryID | Optional |',
        '| WpaPassword | This input value is used to provide a WPA \\(Wi\\-Fi Protected Access\\) password'
        ' to decrypt encrypted 802.11 Wi\\-FI traffic. |  | Optional |',
        '| PcapFilter | This input specifies a search filter to be used on the PCAP file. Filters can be used to'
        ' search only for a specific IP, protocols and other examples. The syntax is the same as in Wireshark which'
        ' can be found here: https://www.wireshark.org/docs/man-pages/wireshark-filter.html <br/>For this'
        ' playbook, using a PCAP filter will generate a new smaller PCAP file based on the provided filter therefor'
        ' thus reducing the extraction of non relevant files. |  | Optional |',
        '| ExtractedFilesLimit | This input limits the number of files to be extracted from the PCAP file. '
        'Default value is 5. | 5 | Optional |',
        ''
    ]

    assert section == expected_section


# playbook tests


def test_get_inputs():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
        get_inputs
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    inputs, errors = get_inputs(playbook)

    expected_query = '(type:ip or type:file or type:Domain or type:URL) -tags:pending_review ' \
                     'and (tags:approved_black or tags:approved_white or tags:approved_watchlist)'
    expected_inputs = [
        {
            'Name': 'InputA', 'Description': '', 'Default Value': 'File.Name', 'Required': 'Optional'
        },
        {
            'Name': 'InputB', 'Description': 'This is input b',
            'Default Value': 'johnnydepp@gmail.com', 'Required': 'Required'
        },
        {
            'Name': 'Indicator Query',
            'Description': 'Indicators matching the indicator query will be used as playbook input',
            'Default Value': expected_query, 'Required': 'Optional'
        }
    ]

    assert inputs == expected_inputs
    assert errors[0] == 'Error! You are missing description in playbook input InputA'


def test_get_outputs():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
        get_outputs
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    outputs, errors = get_outputs(playbook)

    expected_outputs = [{'Path': 'Email.To', 'Description': 'The recipient of the email.', 'Type': 'string'},
                        {'Path': 'FileData', 'Description': '', 'Type': 'string'}]

    assert outputs == expected_outputs
    assert errors[0] == 'Error! You are missing description in playbook output FileData'


def test_get_playbook_dependencies():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
        get_playbook_dependencies
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    playbooks, integrations, scripts, commands = get_playbook_dependencies(playbook, playbook_path=TEST_PLAYBOOK_PATH)

    assert playbooks == ['Get Original Email - Gmail']
    assert integrations == ['Gmail']
    assert scripts == ['ReadFile']
    assert commands == ['gmail-search']


def test_get_input_data_simple():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
        get_input_data
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    sample_input = playbook.get('inputs')[1]

    _value = get_input_data(sample_input)

    assert _value == 'johnnydepp@gmail.com'


def test_get_input_data_complex():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
        get_input_data
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    sample_input = playbook.get('inputs')[0]

    _value = get_input_data(sample_input)

    assert _value == 'File.Name'


# script tests


def test_get_script_info():
    from demisto_sdk.commands.generate_docs.generate_script_doc import \
        get_script_info
    info = get_script_info(TEST_SCRIPT_PATH)

    assert info[0]['Description'] == 'python3'
    assert info[1]['Description'] == 'Algosec'
    assert info[2]['Description'] == '5.0.0'


def test_get_script_inputs():
    from demisto_sdk.commands.generate_docs.generate_script_doc import \
        get_inputs
    script = get_yaml(TEST_SCRIPT_PATH)
    inputs, errors = get_inputs(script)

    expected_inputs = [{'Argument Name': 'InputA', 'Description': ''},
                       {'Argument Name': 'InputB', 'Description': 'This is input b'}]

    assert inputs == expected_inputs
    assert errors[0] == 'Error! You are missing description in script input InputA'


def test_get_script_outputs():
    from demisto_sdk.commands.generate_docs.generate_script_doc import \
        get_outputs
    script = get_yaml(TEST_SCRIPT_PATH)
    outputs, errors = get_outputs(script)

    expected_outputs = [{'Path': 'outputA', 'Description': 'This is output a', 'Type': 'boolean'},
                        {'Path': 'outputB', 'Description': '', 'Type': 'Unknown'}]

    assert outputs == expected_outputs
    assert errors[0] == 'Error! You are missing description in script output outputB'


def test_get_used_in():
    from demisto_sdk.commands.generate_docs.generate_script_doc import \
        get_used_in
    script = get_yaml(TEST_SCRIPT_PATH)
    script_id = script.get('commonfields')['id']
    used_in = get_used_in(FAKE_ID_SET, script_id)
    assert used_in == ['Fake playbook', 'Fake script']


# integration tests


def test_generate_commands_section():
    yml_data = {
        'script': {
            'commands': [
                {'deprecated': True,
                 'name': 'deprecated-cmd'},
                {'deprecated': False,
                 'name': 'non-deprecated-cmd'}
            ]
        }
    }

    section, errors = generate_commands_section(yml_data, example_dict={}, command_permissions_dict={})

    expected_section = [
        '## Commands',
        'You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.',
        '### non-deprecated-cmd', '***', ' ', '#### Required Permissions',
        '**FILL IN REQUIRED PERMISSIONS HERE**', '#### Base Command', '', '`non-deprecated-cmd`', '#### Input', '',
        'There are no input arguments for this command.', '', '#### Context Output', '',
        'There is no context output for this command.', '', '#### Command Example', '``` ```', '',
        '#### Human Readable Output', '\n', '']

    assert '\n'.join(section) == '\n'.join(expected_section)


def test_generate_command_section_with_empty_cotext_example():
    """
    When an string represents an empty dict '{}' is the context output
    the 'Context Example' sections should be empty
    """
    example_dict = {
        'test1': (None, None, '{}')
    }
    command = {'deprecated': False, 'name': 'test1'}

    section, errors = generate_single_command_section(command, example_dict=example_dict, command_permissions_dict={})

    expected_section = ['### test1', '***', ' ', '#### Required Permissions', '**FILL IN REQUIRED PERMISSIONS HERE**',
                        '#### Base Command', '', '`test1`', '#### Input', '',
                        'There are no input arguments for this command.', '', '#### Context Output', '',
                        'There is no context output for this command.', '', '#### Command Example', '```None```', '',
                        '#### Human Readable Output', '\n>None', '']

    assert '\n'.join(section) == '\n'.join(expected_section)


def test_generate_command_section_with_empty_cotext_list():
    """
    When given an empty outputs list,
    the 'Context Outputs' sections should indicate they are empty without empty tables.

    Given
    - An empty command context (as an empty list)

    When
    - Running generate_single_command_section

    Then
    -  Ensure that there is no blank table but a proper error that there is no output
    """
    command = {'deprecated': False, 'name': 'test1', 'outputs': []}

    section, errors = generate_single_command_section(command,
                                                      example_dict={},
                                                      command_permissions_dict={})

    expected_section = ['### test1', '***', ' ', '#### Required Permissions',
                        '**FILL IN REQUIRED PERMISSIONS HERE**',
                        '#### Base Command', '', '`test1`', '#### Input', '',
                        'There are no input arguments for this command.', '',
                        '#### Context Output', '',
                        'There is no context output for this command.', '',
                        '#### Command Example', '``` ```', '',
                        '#### Human Readable Output', '\n', '']

    assert '\n'.join(section) == '\n'.join(expected_section)


def test_generate_commands_section_human_readable():
    yml_data = {
        'script': {
            'commands': [
                {'deprecated': True,
                 'name': 'deprecated-cmd'},
                {'deprecated': False,
                 'name': 'non-deprecated-cmd'}
            ]
        }
    }

    example_dict = {
        'non-deprecated-cmd': [
            '!non-deprecated-cmd', '## this is human readable\nThis is a line\nAnother line', '{}'
        ]
    }

    section, errors = generate_commands_section(yml_data, example_dict, command_permissions_dict={})

    hr_section: str = section[section.index('#### Human Readable Output') + 1]
    # get lines except first one which is a \n
    lines = hr_section.splitlines()[1:]
    for line in lines:
        assert line.startswith('>')
    assert lines[0] == '>## this is human readable'
    assert lines[1] == '>This is a line'


def test_generate_commands_with_permissions_section():
    yml_data = {
        'script': {
            'commands': [
                {'deprecated': True,
                 'name': 'deprecated-cmd'},
                {'deprecated': False,
                 'name': 'non-deprecated-cmd'}
            ]
        }
    }

    section, errors = generate_commands_section(yml_data, example_dict={}, command_permissions_dict={
        'non-deprecated-cmd': 'SUPERUSER'})

    expected_section = [
        '## Commands',
        'You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.',
        '### non-deprecated-cmd', '***', ' ', '#### Required Permissions',
        'SUPERUSER', '#### Base Command', '', '`non-deprecated-cmd`', '#### Input', '',
        'There are no input arguments for this command.', '', '#### Context Output', '',
        'There is no context output for this command.', '', '#### Command Example', '``` ```', '',
        '#### Human Readable Output', '\n', '']

    assert '\n'.join(section) == '\n'.join(expected_section)


def test_generate_commands_with_permissions_section_command_doesnt_exist():
    """
        Given
            - Integration commands from yml file with command permission flag on.
            - The commands from yml file do not exist in the given command permissions dict.
        When
            - Running the generate_table_section command.
        Then
            - Validate that in the #### Required Permissions section empty string is returned
            - Validate that an error is returned in error list which indicated that for this command no permission were found.
    """
    yml_data = {
        'script': {
            'commands': [
                {'deprecated': True,
                 'name': 'deprecated-cmd'},
                {'deprecated': False,
                 'name': 'non-deprecated-cmd'}]}}
    section, errors = generate_commands_section(yml_data, example_dict={}, command_permissions_dict={
        '!non-deprecated-cmd': 'SUPERUSER'})

    expected_section = [
        '## Commands',
        'You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.',
        '### non-deprecated-cmd', '***', ' ', '#### Required Permissions',
        '', '#### Base Command', '', '`non-deprecated-cmd`', '#### Input', '',
        'There are no input arguments for this command.', '', '#### Context Output', '',
        'There is no context output for this command.', '', '#### Command Example', '``` ```', '',
        '#### Human Readable Output', '\n', '']

    assert 'Error! Command Permissions were not found for command non-deprecated-cmd' in errors
    assert '\n'.join(section) == '\n'.join(expected_section)


def test_generate_script_doc(tmp_path, mocker):
    d = tmp_path / "script_doc_out"
    d.mkdir()
    in_script = os.path.join(FILES_PATH, 'docs_test', 'script-Set.yml')
    id_set_file = os.path.join(FILES_PATH, 'docs_test', 'id_set.json')
    with open(id_set_file, 'r') as f:
        id_set = json.load(f)
    patched = mocker.patch.object(IDSetCreator, 'create_id_set', return_value=id_set)
    generate_script_doc(in_script, '', str(d), verbose=True)
    patched.assert_called()
    readme = d / "README.md"
    with open(readme) as f:
        text = f.read()
        assert 'Sample usage of this script can be found in the following playbooks and scripts' in text


class TestAppendOrReplaceCommandInDocs:
    positive_test_data_file = os.path.join(FILES_PATH, 'docs_test', 'positive_docs_section_end_with_eof.md')
    command = 'dxl-send-event'
    old_doc = open(positive_test_data_file).read()
    new_docs = "\n<NEW DOCS>\n"
    positive_inputs = [
        (old_doc, new_docs),
        (old_doc + "\n## Known Limitation", new_docs + "\n## Known Limitation"),
        (old_doc + "\n### new-command", new_docs + "\n### new-command"),
        ("no docs (empty)\n", "no docs (empty)\n" + new_docs),
        (f"Command in file, but cant replace. {command}", f"Command in file, but cant replace. {command}\n" + new_docs)
    ]

    @pytest.mark.parametrize('doc_file, output_docs', positive_inputs)
    def test_append_or_replace_command_in_docs_positive(self, doc_file, output_docs):
        docs, _ = append_or_replace_command_in_docs(doc_file, self.new_docs, self.command)
        assert docs == output_docs


class TestGenerateIntegrationDoc:
    @classmethod
    def rm_readme(cls):
        test_integration_readme = os.path.join(os.path.dirname(TEST_INTEGRATION_PATH), 'README.md')
        if os.path.isfile(test_integration_readme):
            os.remove(test_integration_readme)

    @classmethod
    def setup_class(cls):
        cls.rm_readme()

    @classmethod
    def teardown_class(cls):
        cls.rm_readme()

    def test_generate_integration_doc(self):
        """
        Given
            - YML file representing an integration.
        When
            - Running generate_integration_doc command on the integration.
        Then
            - Validate that the integration README was created correctly, specifically that line numbers are not being reset after a table.
            - Test that the predefined values and default values are added to the README.
    """
        fake_readme = os.path.join(os.path.dirname(TEST_INTEGRATION_PATH), 'fake_README.md')
        # Generate doc
        generate_integration_doc(TEST_INTEGRATION_PATH)
        with open(fake_readme) as fake_file:
            with open(os.path.join(os.path.dirname(TEST_INTEGRATION_PATH), 'README.md')) as real_file:
                fake_data = fake_file.read()
                assert fake_data == real_file.read()

                assert "The type of the newly created user. Possible values are: Basic, Pro, " \
                       "Corporate. Default is Basic." in fake_data
                assert "Number of users to return. Max 300. Default is 30." in fake_data

    def test_integration_doc_credentials_display_missing(self):
        """
        Given
            - YML file representing an integration, containing display None for credentials parameter.
        When
            - Running generate_integration_doc command on the integration.
        Then
            - Validate that the integration README was created correctly, specifically that line numbers are not being
              reset after a table.
            - Test that the predefined values and default values are added to the README.
            - Test that credentials parameter name shown in README is using display password field.
    """
        readme = os.path.join(os.path.dirname(TEST_INTEGRATION_2_PATH), 'README.md')
        # Generate doc
        generate_integration_doc(TEST_INTEGRATION_2_PATH, skip_breaking_changes=True)
        with open(readme) as readme_file:
            with open(os.path.join(os.path.dirname(TEST_INTEGRATION_2_PATH), 'README.md')) as new_readme:
                readme_data = readme_file.read()
                assert readme_data == new_readme.read()
                assert '| None | The API key to use for the connection. | False |' not in readme_data
                assert '| API Token | The API key to use for the connection. | False |' in readme_data


def test_get_command_examples_with_exclamation_mark(tmp_path):
    """
        Given
            - command_examples file with exclamation mark.
            - list of specific commands
        When
            - Running get_command_examples with the given command examples and specific commands.
        Then
            - Verify that the returned commands from the examples are only the specific sommands
    """
    command_examples = tmp_path / "command_examples"

    with open(command_examples, 'w+') as ce:
        ce.write('!zoom-create-user\n!zoom-create-meeting\n!zoom-fetch-recording\n!zoom-list-users\n!zoom-delete-user')

    command_example_a = 'zoom-create-user'
    command_example_b = 'zoom-list-users'

    specific_commands = [command_example_a, command_example_b]

    commands = get_command_examples(commands_file_path=command_examples, specific_commands=specific_commands)

    assert commands == [f'!{command_example_a}', f'!{command_example_b}']


def test_get_command_examples_without_exclamation_mark(tmp_path):
    """
        Given
            - command_examples file without exclamation mark.
            - list of specific commands
        When
            - Running get_command_examples with the given command examples and specific commands.
        Then
            - Verify that the returned commands from the examples are only the specific sommands
    """
    command_examples = tmp_path / "command_examples"

    with open(command_examples, 'w+') as ce:
        ce.write('zoom-create-user\nzoom-create-meeting\nzoom-fetch-recording\nzoom-list-users\nzoom-delete-user')

    command_example_a = 'zoom-create-user'
    command_example_b = 'zoom-list-users'

    specific_commands = [command_example_a, command_example_b]

    commands = get_command_examples(commands_file_path=command_examples, specific_commands=specific_commands)

    assert commands == [f'!{command_example_a}', f'!{command_example_b}']


def test_generate_table_section_numbered_section():
    """
        Given
            - A table that should be part of a numbered section (like the setup section of integration README).
        When
            - Running the generate_table_section command.
        Then
            - Validate that the generated table has \t at the beginning of each line.
    """

    from demisto_sdk.commands.generate_docs.common import \
        generate_table_section

    expected_section = ['', '    | **Type** | **Docker Image** |', '    | --- | --- |',
                        '    | python2 | demisto/python2 |', '']

    section = generate_table_section(data=[{'Type': 'python2', 'Docker Image': 'demisto/python2'}],
                                     title='', horizontal_rule=False, numbered_section=True)
    assert section == expected_section


yml_data_cases = [(
    {"name": "test", "configuration": [
        {'defaultvalue': '', 'display': 'test1', 'name': 'test1', 'required': True, 'type': 8},
        {'defaultvalue': '', 'display': 'test2', 'name': 'test2', 'required': True, 'type': 8}
    ]},  # case no param with additional info field
    ['1. Navigate to **Settings** > **Integrations** > **Servers & Services**.',
     '2. Search for test.', '3. Click **Add instance** to create and configure a new integration instance.',
     '', '    | **Parameter** | **Required** |', '    | --- | --- |', '    | test1 | True |', '    | test2 | True |',
     '', '4. Click **Test** to validate the URLs, token, and connection.']  # expected
),
    (
        {"name": "test", "configuration": [
            {'display': 'test1', 'name': 'test1', 'additionalinfo': 'More info', 'required': True, 'type': 8},
            {'display': 'test2', 'name': 'test2', 'required': True, 'type': 8}
        ]},  # case some params with additional info field
        ['1. Navigate to **Settings** > **Integrations** > **Servers & Services**.',
         '2. Search for test.', '3. Click **Add instance** to create and configure a new integration instance.',
         '', '    | **Parameter** | **Description** | **Required** |', '    | --- | --- | --- |',
         '    | test1 | More info | True |', '    | test2 |  | True |', '',
         '4. Click **Test** to validate the URLs, token, and connection.']  # expected
),
    (
        {"name": "test", "configuration": [
            {'display': 'test1', 'name': 'test1', 'additionalinfo': 'More info', 'required': True, 'type': 8},
            {'display': 'test2', 'name': 'test2', 'additionalinfo': 'Some more data', 'required': True, 'type': 8}
        ]},  # case all params with additional info field
        ['1. Navigate to **Settings** > **Integrations** > **Servers & Services**.',
         '2. Search for test.', '3. Click **Add instance** to create and configure a new integration instance.',
         '', '    | **Parameter** | **Description** | **Required** |', '    | --- | --- | --- |',
         '    | test1 | More info | True |', '    | test2 | Some more data | True |', '',
         '4. Click **Test** to validate the URLs, token, and connection.']  # expected
),
    (
        {"name": "test", "configuration": [
            {'display': 'userName', 'displaypassword': 'password', 'name': 'userName', 'additionalinfo': 'Credentials',
             'required': True, 'type': 9},
        ]},  # case credentials parameter have displaypassword
        ['1. Navigate to **Settings** > **Integrations** > **Servers & Services**.',
         '2. Search for test.', '3. Click **Add instance** to create and configure a new integration instance.',
         '', '    | **Parameter** | **Description** | **Required** |', '    | --- | --- | --- |',
         '    | userName | Credentials | True |', '    | password |  | True |', '',
         '4. Click **Test** to validate the URLs, token, and connection.']  # expected
),
    (
        {"name": "test", "configuration": [
            {'display': 'userName', 'name': 'userName', 'additionalinfo': 'Credentials',
             'required': True, 'type': 9},
        ]},  # case credentials parameter have no displaypassword
        ['1. Navigate to **Settings** > **Integrations** > **Servers & Services**.',
         '2. Search for test.', '3. Click **Add instance** to create and configure a new integration instance.',
         '', '    | **Parameter** | **Description** | **Required** |', '    | --- | --- | --- |',
         '    | userName | Credentials | True |', '    | Password |  | True |', '',
         '4. Click **Test** to validate the URLs, token, and connection.']  # expected
)

]


@pytest.mark.parametrize("yml_input, expected_results", yml_data_cases)
def test_generate_setup_section_with_additional_info(yml_input, expected_results):
    """
        Given
            - A yml file with parameters in configuration section
        When
            - Running the generate_setup_section command.
        Then
            - Validate that the generated table has the 'Description' column if
            at least one parameter has the additionalinfo field.
    """
    section = generate_setup_section(yml_input)
    assert section == expected_results


def test_scripts_in_playbook(repo):
    """
        Given
            - A test playbook file
        When
            - Run get_playbook_dependencies command
        Then
            - Ensure that the scripts we get are from both the script and scriptName fields.
    """
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
        get_playbook_dependencies
    pack = repo.create_pack('pack')
    playbook = pack.create_playbook('LargePlaybook')
    test_task_1 = {
        "id": "1",
        "ignoreworker": False,
        "isautoswitchedtoquietmode": False,
        "isoversize": False,
        "nexttasks": {
            '#none#': ["2"]
        },
        "note": False,
        "quietmode": 0,
        "separatecontext": True,
        "skipunavailable": False,
        "task": {
            "brand": "",
            "id": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
            "iscommand": False,
            "name": "test_script",
            "scriptName": "test_1",
            "type": "regular",
            "version": -1
        },
        "scriptarguments": {
            "encoding": {},
            "entryID": {
                "simple": "entryId"
            },
            "maxFileSize": {}
        },
        "taskid": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
        "timertriggers": [],
        "type": "playbook"
    }
    test_task_2 = {
        "id": "2",
        "ignoreworker": False,
        "isautoswitchedtoquietmode": False,
        "isoversize": False,
        "nexttasks": {
            '#none#': ["3"]
        },
        "note": False,
        "quietmode": 0,
        "separatecontext": True,
        "skipunavailable": False,
        "task": {
            "brand": "",
            "id": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
            "iscommand": False,
            "name": "test_script",
            "script": "test_2",
            "type": "regular",
            "version": -1
        },
        "scriptarguments": {
            "encoding": {},
            "entryID": {
                "simple": "entryId"
            },
            "maxFileSize": {}
        },
        "taskid": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
        "timertriggers": [],
        "type": "playbook"
    }
    playbook.create_default_playbook()
    playbook_data = playbook.yml.read_dict()
    playbook_data['tasks']['1'] = test_task_1
    playbook_data['tasks']['2'] = test_task_2
    playbook.yml.write_dict(playbook_data)

    playbooks, integrations, scripts, commands = get_playbook_dependencies(playbook_data,
                                                                           playbook_path=playbook.yml.rel_path)

    assert "test_1" in scripts
    assert "test_2" in scripts


TEST_ADD_ACCESS_DATA_OF_TYPE_CREDENTIALS_INPUTS = [
    ([], {'display': 'username', 'additionalinfo': 'Username', 'required': True},
     [{'Parameter': 'username', 'Description': 'Username', 'Required': True},
      {'Description': '', 'Parameter': 'Password', 'Required': True}]),
    ([], {'displaypassword': 'specialPassword', 'additionalinfo': 'Enter your password', 'required': False},
     [{'Description': 'Enter your password', 'Parameter': 'specialPassword', 'Required': False}]),
    ([], {'display': 'username', 'additionalinfo': 'Username', 'required': True, 'displaypassword': 'specialPassword'},
     [{'Parameter': 'username', 'Description': 'Username', 'Required': True},
      {'Description': '', 'Parameter': 'specialPassword', 'Required': True}])
]


@pytest.mark.parametrize('access_data, credentials_conf, expected', TEST_ADD_ACCESS_DATA_OF_TYPE_CREDENTIALS_INPUTS)
def test_add_access_data_of_type_credentials(access_data: List[Dict], credentials_conf: Dict, expected: List[Dict]):
    """
    Given:
    - 'access_data': Containing parameter data to be added to README file.
    - 'credentials_conf': Credentials configuration data represented as a dict.

    When:
    - Adding to README the parameter credential conf configuration details.
    Case a: Only display name exists, display password does not.
    Case b: Only display password name exists, display not.
    Case c: Both display name and display password name exists.

    Then:
    - Ensure the expected credentials data is added to 'access_data'.
    Case a: Display name is added, also 'Password' is added as default for display password name missing.
    Case b: 'Password' is added as default for display password name missing.
    Case c: Both display name and display password name are added.
    """
    from demisto_sdk.commands.generate_docs.generate_integration_doc import \
        add_access_data_of_type_credentials
    add_access_data_of_type_credentials(access_data, credentials_conf)
    assert access_data == expected


def test_generate_versions_differences_section(monkeypatch):
    """
        Given
            - A new version of an integration.
        When
            - Running the generate_versions_differences_section command.
        Then
            - Add a section of differences between versions in README.
    """

    from demisto_sdk.commands.generate_docs.generate_integration_doc import \
        generate_versions_differences_section
    monkeypatch.setattr(
        'builtins.input',
        lambda _: ''
    )
    section = generate_versions_differences_section('', '', 'Integration_Display_Name')

    expected_section = [
        '## Breaking changes from the previous version of this integration - Integration_Display_Name',
        '%%FILL HERE%%',
        'The following sections list the changes in this version.',
        '',
        '### Commands',
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
        '',
        '## Additional Considerations for this version',
        '%%FILL HERE%%',
        '* Insert any API changes, any behavioral changes, limitations, or '
        'restrictions that would be new to this version.',
        ''
    ]

    assert section == expected_section


def test_disable_md_autolinks():
    """
        Given
            - Markdown with http link.
        When
            - Run disable_md_autolinks.
        Then
            - Make sure non-md links are escaped. MD links should remain in place.
    """
    assert disable_md_autolinks('http://test.com') == 'http:<span>//</span>test.com'
    no_replace_str = '(link)[http://test.com]'
    assert disable_md_autolinks(no_replace_str) == no_replace_str
    no_replace_str = 'nohttp://test.com'
    assert disable_md_autolinks(no_replace_str) == no_replace_str
    # taken from here: https://github.com/demisto/content/pull/13423/files
    big_str = """{'language': 'python', 'status': 'success', 'status-message': '11 fixed alerts', 'new': 0, 'fixed': 11, 'alerts': [{'query': {'id': 9980089, 'pack': 'com.lgtm/python-queries', 'name': 'Statement has no effect', 'language': 'python', 'properties': {'id': 'py/ineffectual-statement', 'name': 'Statement has no effect', 'severity': 'recommendation', 'tags': ['maintainability', 'useless-code', 'external/cwe/cwe-561']}, 'url': 'https://lgtm.com/rules/9980089'}, 'new': 0, 'fixed': 0}, {'query': {'id': 1510006386081, 'pack': 'com.lgtm/python-queries', 'name': 'Clear-text storage of sensitive information', 'language': 'python', 'properties': {'id': 'py/clear-text-storage-sensitive-data', 'name': 'Clear-text storage of sensitive information', 'severity': 'error', 'tags': ['security', 'external/cwe/cwe-312', 'external/cwe/cwe-315', 'external/cwe/cwe-359']}, 'url': 'https://lgtm.com/rules/1510006386081'}, 'new': 0, 'fixed': 1}, {'query': {'id': 6780086, 'pack': 'com.lgtm/python-queries', 'name': 'Unused local variable', 'language': 'python', 'properties': {'id': 'py/unused-local-variable', 'name': 'Unused local variable', 'severity': 'recommendation', 'tags': ['maintainability', 'useless-code', 'external/cwe/cwe-563']}, 'url': 'https://lgtm.com/rules/6780086'}, 'new': 0, 'fixed': 4}, {'query': {'id': 1800095, 'pack': 'com.lgtm/python-queries', 'name': 'Variable defined multiple times', 'language': 'python', 'properties': {'id': 'py/multiple-definition', 'name': 'Variable defined multiple times', 'severity': 'warning', 'tags': ['maintainability', 'useless-code', 'external/cwe/cwe-563']}, 'url': 'https://lgtm.com/rules/1800095'}, 'new': 0, 'fixed': 4}, {'query': {'id': 3960089, 'pack': 'com.lgtm/python-queries', 'name': 'Explicit returns mixed with implicit (fall through) returns', 'language': 'python', 'properties': {'id': 'py/mixed-returns', 'name': 'Explicit returns mixed with implicit (fall through) returns', 'severity': 'recommendation', 'tags': ['reliability', 'maintainability']}, 'url': 'https://lgtm.com/rules/3960089'}, 'new': 0, 'fixed': 0}, {'query': {'id': 1780094, 'pack': 'com.lgtm/python-queries', 'name': 'Wrong number of arguments in a call', 'language': 'python', 'properties': {'id': 'py/call/wrong-arguments', 'name': 'Wrong number of arguments in a call', 'severity': 'error', 'tags': ['reliability', 'correctness', 'external/cwe/cwe-685']}, 'url': 'https://lgtm.com/rules/1780094'}, 'new': 0, 'fixed': 2}, {'query': {'id': 10030095, 'pack': 'com.lgtm/python-queries', 'name': 'File is not always closed', 'language': 'python', 'properties': {'id': 'py/file-not-closed', 'name': 'File is not always closed', 'severity': 'warning', 'tags': ['efficiency', 'correctness', 'resources', 'external/cwe/cwe-772']}, 'url': 'https://lgtm.com/rules/10030095'}, 'new': 0, 'fixed': 0}]} | https://lgtm.com/projects/g/my-devsecops/moon/rev/pr- """  # noqa
    res = disable_md_autolinks(big_str)
    assert 'http://' not in res
    assert res.count('https:<span>//</span>') == 8
