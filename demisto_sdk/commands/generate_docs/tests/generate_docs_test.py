import json
import os

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import get_json, get_yaml
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    append_or_replace_command_in_docs, generate_commands_section,
    generate_integration_doc, generate_setup_section,
    generate_single_command_section)
from demisto_sdk.commands.generate_docs.generate_script_doc import \
    generate_script_doc

FILES_PATH = os.path.normpath(os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files'))
FAKE_ID_SET = get_json(os.path.join(FILES_PATH, 'fake_id_set.json'))
TEST_PLAYBOOK_PATH = os.path.join(FILES_PATH, 'playbook-Test_playbook.yml')
TEST_SCRIPT_PATH = os.path.join(FILES_PATH, 'script-test_script.yml')
TEST_INTEGRATION_PATH = os.path.join(FILES_PATH, 'fake_integration/fake_integration.yml')


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
        assert open(fake_readme).read() == open(
            os.path.join(os.path.dirname(TEST_INTEGRATION_PATH), 'README.md')).read()

        assert "The type of the newly created user. Possible values are: Basic, Pro, Corporate. Default is Basic." \
               in open(fake_readme).read()
        assert "Number of users to return. Max 300. Default is 30." in open(fake_readme).read()


def test_generate_table_section_numbered_section():
    """
        Given
            - A table that should be part of a numbered section (like the setup section of integration README).
        When
            - Running the generate_table_section command.
        Then
            - Validate that the generated table has \t at the beginning of each line.
    """

    from demisto_sdk.commands.generate_docs.common import generate_table_section

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
