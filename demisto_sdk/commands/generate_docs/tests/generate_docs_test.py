import os
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.common.git_tools import git_path

FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
FAKE_ID_SET = os.path.join(FILES_PATH, 'fake_id_set.json')
TEST_PLAYBOOK_PATH = os.path.join(FILES_PATH, 'playbook-Test_playbook.yml')
TEST_SCRIPT_PATH = os.path.join(FILES_PATH, 'script-test_script.yml')


# common tests


def test_generate_list_section_empty():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section('Inputs', [], empty_message='No inputs found.')

    expected_section = [
        '## Inputs', 'No inputs found.', '']

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
    from demisto_sdk.commands.generate_docs.common import generate_table_section

    section = generate_table_section([], 'Script Data', 'No data found.', 'This is the metadata of the script.')

    expected_section = [
        '## Script Data', '---', 'No data found.', '']

    assert section == expected_section


def test_generate_table_section():
    from demisto_sdk.commands.generate_docs.common import generate_table_section

    section = generate_table_section([{'Type': 'python2', 'Docker Image': 'demisto/python2'}],
                                     'Script Data', 'No data found.', 'This is the metadata of the script.')

    expected_section = [
        '## Script Data', '---', 'This is the metadata of the script.',
        '| **Type** | **Docker Image** |', '| --- | --- |', '| python2 | demisto/python2 |', '']

    assert section == expected_section


# playbook tests


def test_get_inputs():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_inputs
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    inputs, errors = get_inputs(playbook)

    expected_inputs = [{'Name': 'InputA', 'Description': '', 'Default Value': 'Name',
                        'Source': 'File', 'Required': 'Optional'},
                       {'Name': 'InputB', 'Description': 'This is input b', 'Default Value': 'johnnydepp@gmail.com',
                        'Source': '', 'Required': 'Required'}]

    assert inputs == expected_inputs
    assert errors[0] == 'Error! You are missing description in playbook input InputA'


def test_get_outputs():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_outputs
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    outputs, errors = get_outputs(playbook)

    expected_outputs = [{'Path': 'Email.To', 'Description': 'The recipient of the email.', 'Type': 'string'},
                        {'Path': 'FileData', 'Description': '', 'Type': 'string'}]

    assert outputs == expected_outputs
    assert errors[0] == 'Error! You are missing description in playbook output FileData'


def test_get_playbook_dependencies():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_playbook_dependencies
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    playbooks, integrations, scripts, commands = get_playbook_dependencies(playbook)

    assert playbooks == ['Get Original Email - Gmail']
    assert integrations == ['Gmail']
    assert scripts == ['ReadFile']
    assert commands == ['gmail-search']


def test_get_input_data_simple():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_input_data
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    input = playbook.get('inputs')[1]

    _value, source = get_input_data(input)

    assert _value == 'johnnydepp@gmail.com'
    assert source == ''


def test_get_input_data_complex():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_input_data
    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    input = playbook.get('inputs')[0]

    _value, source = get_input_data(input)

    assert _value == 'Name'
    assert source == 'File'


# script tests


def test_get_script_info():
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_script_info
    info = get_script_info(TEST_SCRIPT_PATH)

    assert info[0]['Description'] == 'python3'
    assert info[1]['Description'] == 'Algosec'
    assert info[2]['Description'] == '5.0.0'


def test_get_script_inputs():
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_inputs
    script = get_yaml(TEST_SCRIPT_PATH)
    inputs, errors = get_inputs(script)

    expected_inputs = [{'Argument Name': 'InputA', 'Description': ''},
                       {'Argument Name': 'InputB', 'Description': 'This is input b'}]

    assert inputs == expected_inputs
    assert errors[0] == 'Error! You are missing description in script input InputA'


def test_get_script_outputs():
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_outputs
    script = get_yaml(TEST_SCRIPT_PATH)
    outputs, errors = get_outputs(script)

    expected_outputs = [{'Path': 'outputA', 'Description': 'This is output a', 'Type': 'boolean'},
                        {'Path': 'outputB', 'Description': '', 'Type': 'Unknown'}]

    assert outputs == expected_outputs
    assert errors[0] == 'Error! You are missing description in script output outputB'


def test_get_used_in():
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_used_in
    script = get_yaml(TEST_SCRIPT_PATH)
    script_id = script.get('commonfields')['id']
    used_in = get_used_in(FAKE_ID_SET, script_id)
    assert used_in == ['Fake playbook', 'Fake script']


# integration tests


def test_generate_commands_section():
    from demisto_sdk.commands.generate_docs.generate_integration_doc import generate_commands_section

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

    section, errors = generate_commands_section(yml_data, {})

    expected_section = [
        '## Commands',
        'You can execute these commands from the Demisto CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.',
        '### non-deprecated-cmd', '***', ' ', '##### Required Permissions',
        '**FILL IN REQUIRED PERMISSIONS HERE**', '##### Base Command', '', '`non-deprecated-cmd`', '##### Input', '',
        'There are no input arguments for this command.', '', '##### Context Output', '',
        'There is no context output for this command.', '', '##### Command Example', '``` ```', '',
        '##### Human Readable Output', '', '']

    assert '\n'.join(section) == '\n'.join(expected_section)
