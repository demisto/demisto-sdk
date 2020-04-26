import os

import pytest
import yaml
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.tools import get_dict_from_file
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.tests.constants_test import (
    DESTINATION_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY,
    DESTINATION_FORMAT_SCRIPT_COPY, GIT_ROOT,
    SOURCE_FORMAT_INTEGRATION_COPY, SOURCE_FORMAT_PLAYBOOK_COPY,
    SOURCE_FORMAT_SCRIPT_COPY)

BASIC_YML_TEST_PACKS = [
    (SOURCE_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_INTEGRATION_COPY, IntegrationYMLFormat, 'New Integration_copy',
     'integration'),
    (SOURCE_FORMAT_SCRIPT_COPY, DESTINATION_FORMAT_SCRIPT_COPY, ScriptYMLFormat, 'New_script_copy', 'script'),
    (SOURCE_FORMAT_PLAYBOOK_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY, PlaybookYMLFormat, 'File Enrichment-GenericV2_copy',
     'playbook')
]
FORMAT_CMD = "format"


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', BASIC_YML_TEST_PACKS)
def test_formatting_yml_with_no_test_positive(source_path, destination_path, formatter, yml_title, file_type):
    # type: (str, str, BaseUpdateYML, str) -> None
    """
        Given
        - A yml file (integration, playbook or script) with no 'tests' configured

        When
        - Entering 'Y' into the prompt message about that asks the user if he wants to add 'No tests' to the file

        Then
        -  Ensure no exception is raised
        -  Ensure 'No tests' is added in the first time
        -  Ensure message is not prompt in the second time
    """
    saved_file_path = os.path.join(os.path.dirname(source_path), os.path.basename(destination_path))
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path], input='Y')
    prompt = f'The file {source_path} has no test playbooks configured. Do you want to configure it with No tests'
    assert not result.exception
    assert prompt in result.output
    yml_content = get_dict_from_file(saved_file_path)
    assert yml_content[0].get('tests') == ['No tests (auto formatted)']

    # Running format for the second time should raise no exception and should raise no prompt to the user
    runner = CliRunner()
    result = runner.invoke(main, [FORMAT_CMD, '-i', saved_file_path], input='Y')
    assert not result.exception
    assert prompt not in result.output
    os.remove(saved_file_path)


@pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', BASIC_YML_TEST_PACKS)
def test_formatting_yml_with_no_test_negative(source_path, destination_path, formatter, yml_title, file_type):
    # type: (str, str, BaseUpdateYML, str) -> None
    """
        Given
        - A yml file (integration, playbook or script) with no 'tests' configured

        When
        - Entering 'N' into the prompt message about that asks the user if he wants to add 'No tests' to the file

        Then
        -  Ensure no exception is raised
        -  Ensure 'No tests' is not added
    """
    saved_file_path = os.path.join(os.path.dirname(source_path), os.path.basename(destination_path))
    runner = CliRunner()
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path], input='N')
    assert not result.exception
    prompt = f'The file {source_path} has no test playbooks configured. Do you want to configure it with No tests'
    assert prompt in result.output
    yml_content = get_dict_from_file(saved_file_path)
    assert not yml_content[0].get('tests')
    os.remove(saved_file_path)


@pytest.mark.parametrize('yml_file', [
    'format_pwsh_script.yml',
    'format_pwsh_integration.yml'
])
def test_pwsh_format(tmpdir, yml_file):
    dest = str(tmpdir.join('pwsh_format_res.yml'))
    src_file = f'{GIT_ROOT}/demisto_sdk/tests/test_files/{yml_file}'
    runner = CliRunner()
    result = runner.invoke(main, [FORMAT_CMD, '-i', src_file, '-o', dest], input='Y')
    assert result.exit_code == 0
    with open(dest) as f:
        data = yaml.safe_load(f)
    assert data['fromversion'] == '5.5.0'
    assert data['commonfields']['version'] == -1
