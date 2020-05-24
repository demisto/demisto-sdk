import os
import shutil
import sys

import pytest
import yaml
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.tests.constants_test import (
    DESTINATION_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_PLAYBOOK,
    DESTINATION_FORMAT_PLAYBOOK_COPY, DESTINATION_FORMAT_SCRIPT_COPY,
    EQUAL_VAL_FORMAT_PLAYBOOK_DESTINATION, EQUAL_VAL_FORMAT_PLAYBOOK_SOURCE,
    EQUAL_VAL_PATH, GIT_ROOT, PLAYBOOK_PATH, SOURCE_FORMAT_INTEGRATION_COPY,
    SOURCE_FORMAT_PLAYBOOK, SOURCE_FORMAT_PLAYBOOK_COPY,
    SOURCE_FORMAT_SCRIPT_COPY)
from ruamel.yaml import YAML

ryaml = YAML()
ryaml.preserve_quotes = True
ryaml.allow_duplicate_keys = True

BASIC_YML_TEST_PACKS = [
    (SOURCE_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_INTEGRATION_COPY, IntegrationYMLFormat, 'New Integration_copy',
     'integration'),
    (SOURCE_FORMAT_SCRIPT_COPY, DESTINATION_FORMAT_SCRIPT_COPY, ScriptYMLFormat, 'New_script_copy', 'script'),
    (SOURCE_FORMAT_PLAYBOOK_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY, PlaybookYMLFormat, 'File Enrichment-GenericV2_copy',
     'playbook')
]


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', BASIC_YML_TEST_PACKS)
def test_yml_preserve_comment(source_path, destination_path, formatter, yml_title, file_type, capsys):
    """
    Given
        - A Integration/Script/Playbook that contains comments in their YAML file

    When
        - Formatting the Integration/Script/Playbook

    Then
        - Ensure comments are being preserved
    """
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
    base_yml = formatter(source_path, path=schema_path)
    ryaml.dump(base_yml.data, sys.stdout)
    stdout, _ = capsys.readouterr()
    assert '# comment' in stdout


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', BASIC_YML_TEST_PACKS)
def test_basic_yml_updates(source_path, destination_path, formatter, yml_title, file_type):
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
    base_yml = formatter(source_path, path=schema_path)
    base_yml.update_yml()
    assert yml_title not in str(base_yml.data)
    assert -1 == base_yml.id_and_version_location['version']


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', BASIC_YML_TEST_PACKS)
def test_save_output_file(source_path, destination_path, formatter, yml_title, file_type):
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
    saved_file_path = os.path.join(os.path.dirname(source_path), os.path.basename(destination_path))
    base_yml = formatter(input=source_path, output=saved_file_path, path=schema_path)
    base_yml.save_yml_to_destination_file()
    assert os.path.isfile(saved_file_path)
    os.remove(saved_file_path)


INTEGRATION_PROXY_SSL_PACK = [
    (SOURCE_FORMAT_INTEGRATION_COPY, 'insecure', 'Trust any certificate (not secure)', 'integration', 1),
    (SOURCE_FORMAT_INTEGRATION_COPY, 'unsecure', 'Trust any certificate (not secure)', 'integration', 1),
    (SOURCE_FORMAT_INTEGRATION_COPY, 'proxy', 'Use system proxy settings', 'integration', 1)
]


@pytest.mark.parametrize('source_path, argument_name, argument_description, file_type, appearances',
                         INTEGRATION_PROXY_SSL_PACK)
def test_proxy_ssl_descriptions(source_path, argument_name, argument_description, file_type, appearances):
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
    base_yml = IntegrationYMLFormat(source_path, path=schema_path)
    base_yml.update_proxy_insecure_param_to_default()

    argument_count = 0
    for argument in base_yml.data['configuration']:
        if argument_name == argument['name']:
            assert argument_description == argument['display']
            argument_count += 1

    assert argument_count == appearances


INTEGRATION_BANG_COMMANDS_ARGUMENTS_PACK = [
    (SOURCE_FORMAT_INTEGRATION_COPY, 'integration', 'url', [
        ('default', True),
        ('isArray', True),
        ('required', True)
    ]),
    (SOURCE_FORMAT_INTEGRATION_COPY, 'integration', 'email', [
        ('default', True),
        ('isArray', True),
        ('required', True),
        ('description', '')
    ])
]


@pytest.mark.parametrize('source_path, file_type, bang_command, verifications',
                         INTEGRATION_BANG_COMMANDS_ARGUMENTS_PACK)
def test_bang_commands_default_arguments(source_path, file_type, bang_command, verifications):
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
    base_yml = IntegrationYMLFormat(source_path, path=schema_path)
    base_yml.set_reputation_commands_basic_argument_as_needed()

    for command in base_yml.data['script']['commands']:
        if bang_command == command['name']:
            command_arguments = command['arguments']
            for argument in command_arguments:
                if argument.get('name', '') == bang_command:
                    for verification in verifications:
                        assert argument[verification[0]] == verification[1]


@pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
def test_playbook_task_description_name(source_path):
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
    base_yml = PlaybookYMLFormat(source_path, path=schema_path)
    base_yml.add_description()
    base_yml.update_playbook_task_name()

    assert 'description' in base_yml.data['tasks']['7']['task']
    assert base_yml.data['tasks']['29']['task']['name'] == 'File Enrichment - Virus Total Private API'
    assert base_yml.data['tasks']['25']['task']['description'] == 'Check if there is a SHA256 hash in context.'


@pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
def test_playbook_sourceplaybookid(source_path):
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
    base_yml = PlaybookYMLFormat(source_path, path=schema_path)
    base_yml.delete_sourceplaybookid()

    assert 'sourceplaybookid' not in base_yml.data


EQUAL_TEST = [
    (EQUAL_VAL_FORMAT_PLAYBOOK_SOURCE, EQUAL_VAL_FORMAT_PLAYBOOK_DESTINATION, EQUAL_VAL_PATH),
]


@pytest.mark.parametrize('input, output, path', EQUAL_TEST)
def test_eqaul_value_in_file(input, output, path):
    os.mkdir(path)
    shutil.copyfile(input, output)
    format = format_manager(input=output)
    check = True
    with open(output, 'r') as f:
        if 'simple: =' in f:
            check = False
    os.remove(output)
    os.rmdir(path)
    assert check
    assert not format


@pytest.mark.parametrize('yml_file, yml_type', [
    ('format_pwsh_script.yml', 'script'),
    ('format_pwsh_integration.yml', 'integration')
])
def test_pwsh_format(tmpdir, yml_file, yml_type):
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(yml_type)))
    dest = str(tmpdir.join('pwsh_format_res.yml'))
    src_file = f'{GIT_ROOT}/demisto_sdk/tests/test_files/{yml_file}'
    if yml_type == 'script':
        format_obj = ScriptYMLFormat(src_file, output=dest, path=schema_path)
    else:
        format_obj = IntegrationYMLFormat(src_file, output=dest, path=schema_path)
    assert format_obj.run_format() == 0
    with open(dest) as f:
        data = yaml.safe_load(f)
    assert data['fromversion'] == '5.5.0'
    assert data['commonfields']['version'] == -1


PLAYBOOK_TEST = [
    (SOURCE_FORMAT_PLAYBOOK_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY, PlaybookYMLFormat, 'File Enrichment-GenericV2_copy',
     'playbook')
]


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', PLAYBOOK_TEST)
def test_string_condition_in_playbook(source_path, destination_path, formatter, yml_title, file_type):
    """
    Given
    - Playbook with condition labeled as `yes`.
    - destination_path to write the formatted playbook to.

    When
    - Running the format command.

    Then
    - Ensure the file was created.
    - Ensure 'yes' string in the playbook condition remains string and do not change to boolean.
    """
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
    saved_file_path = os.path.join(os.path.dirname(source_path), os.path.basename(destination_path))
    base_yml = formatter(input=source_path, output=saved_file_path, path=schema_path)
    base_yml.save_yml_to_destination_file()
    assert os.path.isfile(saved_file_path)

    with open(saved_file_path, 'r') as f:
        content = f.read()
        yaml_content = yaml.load(content)
        assert 'yes' in yaml_content['tasks']['27']['nexttasks']
    os.remove(saved_file_path)


FORMAT_FILES = [
    (SOURCE_FORMAT_PLAYBOOK, DESTINATION_FORMAT_PLAYBOOK, PLAYBOOK_PATH, 0)
]


@pytest.mark.parametrize('source, target, path, answer', FORMAT_FILES)
def test_format_file(source, target, path, answer):
    os.makedirs(path)
    shutil.copyfile(source, target)
    res = format_manager(input=target, output=target)
    os.remove(target)
    os.rmdir(path)

    assert res is answer


def test_add_playbooks_description():
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
    base_yml = PlaybookYMLFormat(SOURCE_FORMAT_PLAYBOOK_COPY, path=schema_path)
    base_yml.data = {
        "tasks": {
            "1": {
                "type": "playbook",
                "task": {
                }
            },
            "2": {
                "type": "something",
                "task": {
                    "description": "else"
                }
            },
            "3": {
                "type": "something",
                "task": {
                }
            },
            "4": {
                "type": "playbook",
                "task": {
                }
            },
            "5": {
                "type": "start",
                "task": {
                }
            },
            "6": {
                "type": "title",
                "task": {
                }
            },
        }
    }
    base_yml.add_description()
    assert 'description' not in base_yml.data
    assert base_yml.data['tasks']['1']['task']['description'] == ''
    assert base_yml.data['tasks']['2']['task']['description'] == 'else'
    assert 'description' not in base_yml.data['tasks']['3']['task']
    assert base_yml.data['tasks']['4']['task']['description'] == ''
    assert base_yml.data['tasks']['5']['task']['description'] == ''
    assert base_yml.data['tasks']['6']['task']['description'] == ''
