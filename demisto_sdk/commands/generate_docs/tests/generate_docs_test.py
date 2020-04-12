import os

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import get_json, get_yaml
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    append_or_replace_command_in_docs, generate_integration_doc)

FILES_PATH = os.path.normpath(os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files'))
FAKE_ID_SET = get_json(os.path.join(FILES_PATH, 'fake_id_set.json'))
TEST_PLAYBOOK_PATH = os.path.join(FILES_PATH, 'playbook-Test_playbook.yml')
TEST_SCRIPT_PATH = os.path.join(FILES_PATH, 'script-test_script.yml')
TEST_INTEGRATION_PATH = os.path.join(FILES_PATH, 'fake_integration/fake_integration.yml')


# common tests


def test_stringEscapeMD():
    from demisto_sdk.commands.generate_docs.common import stringEscapeMD
    res = stringEscapeMD('First fetch timestamp (<number> <time unit>, e.g., 12 hours, 7 days)')
    assert '<' not in res
    assert '>' not in res
    res = stringEscapeMD("new line test \n", escape_multiline=True)
    assert '\n' not in res
    assert '<br/>' in res


def test_generate_list_section_empty():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section('Inputs', [], empty_message='No inputs found.')

    expected_section = [
        '## Inputs', 'No inputs found.', '']

    assert section == expected_section


def test_generate_numbered_section():
    from demisto_sdk.commands.generate_docs.common import generate_numbered_section

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

    section, errors = generate_commands_section(yml_data, example_dict={}, command_permissions_dict={})

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


def test_generate_commands_with_permissions_section():
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

    section, errors = generate_commands_section(yml_data, example_dict={}, command_permissions_dict={
        'non-deprecated-cmd': 'SUPERUSER'})

    expected_section = [
        '## Commands',
        'You can execute these commands from the Demisto CLI, as part of an automation, or in a playbook.',
        'After you successfully execute a command, a DBot message appears in the War Room with the command details.',
        '### non-deprecated-cmd', '***', ' ', '##### Required Permissions',
        'SUPERUSER', '##### Base Command', '', '`non-deprecated-cmd`', '##### Input', '',
        'There are no input arguments for this command.', '', '##### Context Output', '',
        'There is no context output for this command.', '', '##### Command Example', '``` ```', '',
        '##### Human Readable Output', '', '']

    assert '\n'.join(section) == '\n'.join(expected_section)


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
        fake_readme = os.path.join(os.path.dirname(TEST_INTEGRATION_PATH), 'fake_README.md')
        # Generate doc
        generate_integration_doc(TEST_INTEGRATION_PATH)
        assert open(fake_readme).read() == open(os.path.join(os.path.dirname(TEST_INTEGRATION_PATH), 'README.md')).read()
