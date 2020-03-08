import os
import pytest

from demisto_sdk.tests.constants_test import SOURCE_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_INTEGRATION_COPY, \
    SOURCE_FORMAT_SCRIPT_COPY, DESTINATION_FORMAT_SCRIPT_COPY, SOURCE_FORMAT_PLAYBOOK_COPY, \
    DESTINATION_FORMAT_PLAYBOOK_COPY

from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat

BASIC_YML_TEST_PACKS = [
    (SOURCE_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_INTEGRATION_COPY, IntegrationYMLFormat, 'New Integration_copy'),
    (SOURCE_FORMAT_SCRIPT_COPY, DESTINATION_FORMAT_SCRIPT_COPY, ScriptYMLFormat, 'New_script_copy'),
    (SOURCE_FORMAT_PLAYBOOK_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY, PlaybookYMLFormat, 'File Enrichment-GenericV2_copy')
]


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title', BASIC_YML_TEST_PACKS)
def test_basic_yml_updates(source_path, destination_path, formatter, yml_title):
    base_yml = formatter(source_path)
    base_yml.update_yml()
    assert yml_title not in str(base_yml.yml_data)
    assert -1 == base_yml.id_and_version_location['version']


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title', BASIC_YML_TEST_PACKS)
def test_save_output_file(source_path, destination_path, formatter, yml_title):
    base_yml = formatter(source_path, destination_path)
    base_yml.save_yml_to_destination_file()
    saved_file_path = os.path.join(os.path.dirname(source_path), os.path.basename(destination_path))
    assert os.path.isfile(saved_file_path)
    os.remove(saved_file_path)


INTEGRATION_PROXY_SSL_PACK = [
    (SOURCE_FORMAT_INTEGRATION_COPY, 'insecure', 'Trust any certificate (not secure)', 1),
    (SOURCE_FORMAT_INTEGRATION_COPY, 'unsecure', 'Trust any certificate (not secure)', 1),
    (SOURCE_FORMAT_INTEGRATION_COPY, 'proxy', 'Use system proxy settings', 1)
]


@pytest.mark.parametrize('source_path, argument_name, argument_description, appearances', INTEGRATION_PROXY_SSL_PACK)
def test_proxy_ssl_descriptions(source_path, argument_name, argument_description, appearances):
    base_yml = IntegrationYMLFormat(source_path)
    base_yml.update_proxy_insecure_param_to_default()

    argument_count = 0
    for argument in base_yml.yml_data['configuration']:
        if argument_name == argument['name']:
            assert argument_description == argument['display']
            argument_count += 1

    assert argument_count == appearances


INTEGRATION_BANG_COMMANDS_ARGUMENTS_PACK = [
    (SOURCE_FORMAT_INTEGRATION_COPY, 'url', [
        ('default', True),
        ('isArray', True),
        ('required', True)
    ]),
    (SOURCE_FORMAT_INTEGRATION_COPY, 'email', [
        ('default', True),
        ('isArray', True),
        ('required', True),
        ('description', '')
    ])
]


@pytest.mark.parametrize('source_path, bang_command, verifications', INTEGRATION_BANG_COMMANDS_ARGUMENTS_PACK)
def test_bang_commands_default_arguments(source_path, bang_command, verifications):
    base_yml = IntegrationYMLFormat(source_path)
    base_yml.set_reputation_commands_basic_argument_as_needed()

    for command in base_yml.yml_data['script']['commands']:
        if bang_command == command['name']:
            command_arguments = command['arguments']
            for argument in command_arguments:
                if argument.get('name', '') == bang_command:
                    for verification in verifications:
                        assert argument[verification[0]] == verification[1]


@pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
def test_playbook_task_description_name(source_path):
    base_yml = PlaybookYMLFormat(source_path)
    base_yml.add_description()
    base_yml.update_playbook_task_name()

    assert 'description' in base_yml.yml_data['tasks']['7']['task']
    assert base_yml.yml_data['tasks']['29']['task']['name'] == 'File Enrichment - Virus Total Private API'
    assert base_yml.yml_data['tasks']['25']['task']['description'] == 'Check if there is a SHA256 hash in context.'


@pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
def test_playbook_sourceplaybookid(source_path):
    base_yml = PlaybookYMLFormat(source_path)
    base_yml.delete_sourceplaybookid()

    assert 'sourceplaybookid' not in base_yml.yml_data
