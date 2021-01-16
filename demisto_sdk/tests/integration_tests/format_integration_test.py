import json
import os
import re
from pathlib import PosixPath
from typing import List

import pytest
import yaml
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import OLDEST_SUPPORTED_VERSION
from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.tools import (get_dict_from_file,
                                               is_test_config_match)
from demisto_sdk.commands.format import update_generic
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.commands.lint.commands_builder import excluded_files
from demisto_sdk.tests.constants_test import (
    DESTINATION_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY,
    INTEGRATION_WITH_TEST_PLAYBOOKS, PLAYBOOK_WITH_TEST_PLAYBOOKS,
    SOURCE_FORMAT_INTEGRATION_COPY, SOURCE_FORMAT_PLAYBOOK_COPY)
from TestSuite.test_tools import ChangeCWD

BASIC_YML_TEST_PACKS = [
    (SOURCE_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_INTEGRATION_COPY, IntegrationYMLFormat, 'New Integration_copy',
     'integration'),
    (SOURCE_FORMAT_PLAYBOOK_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY, PlaybookYMLFormat, 'File Enrichment-GenericV2_copy',
     'playbook')
]

YML_FILES_WITH_TEST_PLAYBOOKS = [
    (
        INTEGRATION_WITH_TEST_PLAYBOOKS,
        DESTINATION_FORMAT_INTEGRATION_COPY,
        IntegrationYMLFormat,
        'New Integration',
        'integration'),
    (
        PLAYBOOK_WITH_TEST_PLAYBOOKS,
        DESTINATION_FORMAT_PLAYBOOK_COPY,
        PlaybookYMLFormat,
        'File Enrichment-GenericV2_copy',
        'playbook'
    )
]
FORMAT_CMD = "format"
CONF_JSON_ORIGINAL_CONTENT = {
    "tests": [
        {
            "integrations": "PagerDuty v2",
            "playbookID": "PagerDuty Test"
        },
        {
            "integrations": "Account Enrichment",
            "playbookID": "PagerDuty Test"
        },
        {
            "integrations": "TestCreateDuplicates",
            "playbookID": "PagerDuty Test"
        }
    ]
}


@pytest.mark.parametrize('source_path,destination_path,formatter,yml_title,file_type', BASIC_YML_TEST_PACKS)
def test_integration_format_yml_with_no_test_positive(tmp_path: PosixPath,
                                                      source_path: str,
                                                      destination_path: str,
                                                      formatter: BaseUpdateYML,
                                                      yml_title: str,
                                                      file_type: str):
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
    saved_file_path = str(tmp_path / os.path.basename(destination_path))
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path], input='Y')
    prompt = f'The file {source_path} has no test playbooks configured. Do you want to configure it with "No tests"'
    assert not result.exception
    assert prompt in result.output
    yml_content = get_dict_from_file(saved_file_path)
    assert yml_content[0].get('tests') == ['No tests (auto formatted)']

    # Running format for the second time should raise no exception and should raise no prompt to the user
    result = runner.invoke(main, [FORMAT_CMD, '-i', saved_file_path], input='Y')
    assert not result.exception
    assert prompt not in result.output
    os.remove(saved_file_path)


@pytest.mark.parametrize('source_path,destination_path,formatter,yml_title,file_type', BASIC_YML_TEST_PACKS)
def test_integration_format_yml_with_no_test_negative(tmp_path: PosixPath,
                                                      source_path: str,
                                                      destination_path: str,
                                                      formatter: BaseUpdateYML,
                                                      yml_title: str,
                                                      file_type: str):
    """
        Given
        - A yml file (integration, playbook or script) with no 'tests' configured

        When
        - Entering 'N' into the prompt message about that asks the user if he wants to add 'No tests' to the file

        Then
        -  Ensure no exception is raised
        -  Ensure 'No tests' is not added
    """
    saved_file_path = str(tmp_path / os.path.basename(destination_path))
    runner = CliRunner()
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path], input='N')
    assert not result.exception
    prompt = f'The file {source_path} has no test playbooks configured. Do you want to configure it with "No tests"'
    assert prompt in result.output
    yml_content = get_dict_from_file(saved_file_path)
    assert not yml_content[0].get('tests')
    os.remove(saved_file_path)


@pytest.mark.parametrize('source_path,destination_path,formatter,yml_title,file_type', BASIC_YML_TEST_PACKS)
def test_integration_format_yml_with_no_test_no_interactive_positive(tmp_path: PosixPath,
                                                                     source_path: str,
                                                                     destination_path: str,
                                                                     formatter: BaseUpdateYML,
                                                                     yml_title: str,
                                                                     file_type: str):
    """
        Given
        - A yml file (integration, playbook or script) with no 'tests' configured

        When
        - using the '-y' option

        Then
        -  Ensure no exception is raised
        -  Ensure 'No tests' is added in the first time
    """
    saved_file_path = str(tmp_path / os.path.basename(destination_path))
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path, '-y'])
    assert not result.exception
    yml_content = get_dict_from_file(saved_file_path)
    assert yml_content[0].get('tests') == ['No tests (auto formatted)']


@pytest.mark.parametrize('source_path,destination_path,formatter,yml_title,file_type', YML_FILES_WITH_TEST_PLAYBOOKS)
def test_integration_format_configuring_conf_json_no_interactive_positive(tmp_path: PosixPath,
                                                                          source_path: str,
                                                                          destination_path: str,
                                                                          formatter: BaseUpdateYML,
                                                                          yml_title: str,
                                                                          file_type: str):
    """
        Given
        - A yml file (integration, playbook or script) with no tests playbooks configured that are not configured
            in conf.json

        When
        - using the -y option

        Then
        -  Ensure no exception is raised
        -  If file_type is playbook or a script: Ensure {"playbookID": <content item ID>} is added to conf.json
            for each test playbook configured in the yml under 'tests' key
        -  If file_type is integration: Ensure {"playbookID": <content item ID>, "integrations": yml_title} is
            added to conf.json for each test playbook configured in the yml under 'tests' key
    """
    # Setting up conf.json
    conf_json_path = str(tmp_path / 'conf.json')
    with open(conf_json_path, 'w') as file:
        json.dump(CONF_JSON_ORIGINAL_CONTENT, file, indent=4)
    BaseUpdateYML.CONF_PATH = conf_json_path

    test_playbooks = ['test1', 'test2']
    saved_file_path = str(tmp_path / os.path.basename(destination_path))
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path, '-y'])
    assert not result.exception
    if file_type == 'playbook':
        _verify_conf_json_modified(test_playbooks, '', conf_json_path)
    else:
        _verify_conf_json_modified(test_playbooks, yml_title, conf_json_path)


@pytest.mark.parametrize('source_path,destination_path,formatter,yml_title,file_type', YML_FILES_WITH_TEST_PLAYBOOKS)
def test_integration_format_configuring_conf_json_positive(tmp_path: PosixPath,
                                                           source_path: str,
                                                           destination_path: str,
                                                           formatter: BaseUpdateYML,
                                                           yml_title: str,
                                                           file_type: str):
    """
        Given
        - A yml file (integration, playbook or script) with no tests playbooks configured that are not configured
            in conf.json

        When
        - Entering 'Y' into the prompt message that asks the user if he wants to configure those test playbooks into
            conf.json

        Then
        -  Ensure no exception is raised
        -  If file_type is playbook or a script: Ensure {"playbookID": <content item ID>} is added to conf.json
            for each test playbook configured in the yml under 'tests' key
        -  If file_type is integration: Ensure {"playbookID": <content item ID>, "integrations": yml_title} is
            added to conf.json for each test playbook configured in the yml under 'tests' key
        -  Ensure message is not prompt in the second time
    """
    # Setting up conf.json
    conf_json_path = str(tmp_path / 'conf.json')
    with open(conf_json_path, 'w') as file:
        json.dump(CONF_JSON_ORIGINAL_CONTENT, file, indent=4)
    BaseUpdateYML.CONF_PATH = conf_json_path

    test_playbooks = ['test1', 'test2']
    saved_file_path = str(tmp_path / os.path.basename(destination_path))
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path], input='Y')
    prompt = 'The following test playbooks are not configured in conf.json file'
    assert not result.exception
    assert prompt in result.output
    if file_type == 'playbook':
        _verify_conf_json_modified(test_playbooks, '', conf_json_path)
    else:
        _verify_conf_json_modified(test_playbooks, yml_title, conf_json_path)
    # Running format for the second time should raise no exception and should raise no prompt to the user
    result = runner.invoke(main, [FORMAT_CMD, '-i', saved_file_path], input='Y')
    assert not result.exception
    assert prompt not in result.output


@pytest.mark.parametrize('source_path,destination_path,formatter,yml_title,file_type', YML_FILES_WITH_TEST_PLAYBOOKS)
def test_integration_format_configuring_conf_json_negative(tmp_path: PosixPath,
                                                           source_path: str,
                                                           destination_path: str,
                                                           formatter: BaseUpdateYML,
                                                           yml_title: str,
                                                           file_type: str):
    """
        Given
        - A yml file (integration, playbook or script) with no tests playbooks configured that are not configured
            in conf.json

        When
        - Entering 'N' into the prompt message that asks the user if he wants to configure those test playbooks into
            conf.json

        Then
        -  Ensure no exception is raised
        -  Ensure conf.json is not modified
    """
    # Setting up conf.json
    conf_json_path = str(tmp_path / 'conf.json')
    with open(conf_json_path, 'w') as file:
        json.dump(CONF_JSON_ORIGINAL_CONTENT, file, indent=4)
    BaseUpdateYML.CONF_PATH = conf_json_path

    saved_file_path = str(tmp_path / os.path.basename(destination_path))
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_path, '-o', saved_file_path], input='N')
    prompt = 'The following test playbooks are not configured in conf.json file'
    assert not result.exception
    assert prompt in result.output
    with open(conf_json_path) as data_file:
        conf_json_content = json.load(data_file)
        assert conf_json_content == CONF_JSON_ORIGINAL_CONTENT
    assert 'Skipping test playbooks configuration' in result.output


def _verify_conf_json_modified(test_playbooks: List, yml_title: str, conf_json_path: str):
    """
    Verifying all test playbooks are configured in conf.json file
    """
    try:
        with open(conf_json_path) as data_file:
            conf_json_content = json.load(data_file)
            for test_playbook in test_playbooks:
                assert any(
                    test_config for test_config in conf_json_content['tests'] if
                    is_test_config_match(test_config,
                                         test_playbook_id=test_playbook,
                                         integration_id=yml_title,
                                         )
                )
    except Exception:
        raise


def test_integration_format_remove_playbook_sourceplaybookid(tmp_path):
    """
    Given
    - Playbook with field  `sourceplaybookid`.
    - destination_path to write the formatted playbook to.

    When
    - Running the format command.

    Then
    - Ensure 'sourceplaybookid' was deleted from the yml file.
    """
    source_playbook_path = SOURCE_FORMAT_PLAYBOOK_COPY
    playbook_path = str(tmp_path / 'format_new_playbook_copy.yml')
    runner = CliRunner()
    result = runner.invoke(main, [FORMAT_CMD, '-i', source_playbook_path, '-o', playbook_path], input='N')
    prompt = f'The file {source_playbook_path} has no test playbooks configured. Do you want to configure it with "No tests"'
    assert result.exit_code == 0
    assert prompt in result.output
    assert '======= Updating file: ' in result.stdout
    assert f'Format Status   on file: {source_playbook_path} - Success' in result.stdout
    with open(playbook_path) as f:
        yaml_content = yaml.safe_load(f)
        assert 'sourceplaybookid' not in yaml_content

    assert not result.exception


def test_format_on_valid_py(mocker, repo):
    """
    Given
    - A valid python file.

    When
    - Running format

    Then
    - Ensure format passes.
    """
    mocker.patch.object(update_generic, 'is_file_from_content_repo', return_value=(False, ''))
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration')
    valid_py = 'test\n'
    integration.code.write(valid_py)

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FORMAT_CMD, '-nv', '-i', integration.code.path, '-v'], catch_exceptions=True)
    assert '======= Updating file:' in result.stdout
    assert 'Running autopep8 on file' in result.stdout
    assert 'Success' in result.stdout
    assert valid_py == integration.code.read()


def test_format_on_invalid_py_empty_lines(mocker, repo):
    """
    Given
    - Invalid python file - empty lines at the end of file.

    When
    - Running format

    Then
    - Ensure format passes.
    """
    mocker.patch.object(update_generic, 'is_file_from_content_repo', return_value=(False, ''))
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration')
    invalid_py = 'test\n\n\n\n'
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FORMAT_CMD, '-nv', '-i', integration.code.path, '-v'], catch_exceptions=False)

    assert '======= Updating file:' in result.stdout
    assert 'Running autopep8 on file' in result.stdout
    assert 'Success' in result.stdout
    assert invalid_py != integration.code.read()


def test_format_on_invalid_py_dict(mocker, repo):
    """
    Given
    - Invalid python file - missing spaces in dict.

    When
    - Running format

    Then
    - Ensure format passes.
    """
    mocker.patch.object(update_generic, 'is_file_from_content_repo', return_value=(False, ''))
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration')
    invalid_py = "{'test':'testing','test1':'testing1'}"
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FORMAT_CMD, '-nv', '-i', integration.code.path, '-v'], catch_exceptions=False)

    assert '======= Updating file:' in result.stdout
    assert 'Running autopep8 on file' in result.stdout
    assert 'Success' in result.stdout
    assert invalid_py != integration.code.read()


def test_format_on_invalid_py_long_dict(mocker, repo):
    """
    Given
    - Invalid python file - long dict.

    When
    - Running format

    Then
    - Ensure format passes.
    """
    mocker.patch.object(update_generic, 'is_file_from_content_repo', return_value=(False, ''))
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration')
    invalid_py = "{'test':'testing','test1':'testing1','test2':'testing2','test3':'testing3'," \
                 "'test4':'testing4','test5':'testing5','test6':'testing6'}"
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FORMAT_CMD, '-nv', '-i', integration.code.path, '-v'], catch_exceptions=False)

    assert '======= Updating file:' in result.stdout
    assert 'Running autopep8 on file' in result.stdout
    assert 'Success' in result.stdout
    assert invalid_py != integration.code.read()


def test_format_on_invalid_py_long_dict_no_verbose(mocker, repo):
    """
    (This is the same test as the previous one only not using the '-v' argument)
    Given
    - Invalid python file - long dict.

    When
    - Running format

    Then
    - Ensure format passes and that the verbose is off
    """
    mocker.patch.object(update_generic, 'is_file_from_content_repo', return_value=(False, ''))
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration')
    invalid_py = "{'test':'testing','test1':'testing1','test2':'testing2','test3':'testing3'," \
                 "'test4':'testing4','test5':'testing5','test6':'testing6'}"
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FORMAT_CMD, '-nv', '-i', integration.code.path], catch_exceptions=False)

    assert '======= Updating file:' in result.stdout
    assert 'Running autopep8 on file' not in result.stdout
    assert 'Success' in result.stdout
    assert invalid_py != integration.code.read()


def test_format_on_relative_path_playbook(mocker, repo):
    """
    Given
    - playbook to validate on with a relative path

    When
    - Running format
    - Running validate

    Then
    - Ensure format passes.
    - Ensure validate passes.
    """
    pack = repo.create_pack('PackName')
    playbook = pack.create_playbook('playbook')
    playbook.create_default_playbook()
    mocker.patch.object(update_generic, 'is_file_from_content_repo',
                        return_value=(True, f'{playbook.path}/playbook.yml'))
    mocker.patch.object(PlaybookValidator, 'is_script_id_valid', return_value=True)
    mocker.patch.object(tools, 'is_external_repository', return_value=True)
    success_reg = re.compile("Format Status .+?- Success\n")
    with ChangeCWD(playbook.path):
        runner = CliRunner(mix_stderr=False)
        result_format = runner.invoke(main, [FORMAT_CMD, '-i', 'playbook.yml', '-v'], catch_exceptions=False)
        result_validate = runner.invoke(main, ['validate', '-i', 'playbook.yml', '--no-docker-checks'],
                                        catch_exceptions=False)

    assert '======= Updating file:' in result_format.stdout
    assert success_reg.search(result_format.stdout)
    assert 'The files are valid' in result_validate.stdout


def test_format_integration_skipped_files(repo):
    """
    Given:
        - Content pack with integration and doc files
        - Integration dir includes file artifacts from running lint (e.g. conftest.py)

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format does not run files to be skipped
    """
    pack = repo.create_pack('PackName')
    pack.create_integration('integration')
    pack.create_doc_file()

    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(pack.path), '-v'], catch_exceptions=False)

    assert '======= Updating file:' in format_result.stdout
    assert 'Success' in format_result.stdout
    for excluded_file in excluded_files + ['pack_metadata.json']:
        assert excluded_file not in format_result.stdout


def test_format_commonserver_skipped_files(repo):
    """
    Given:
        - Base content pack with CommonServerPython script

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format does not run files to be skipped
    """
    pack = repo.create_pack('Base')
    pack.create_script('CommonServerPython')

    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(pack.path), '-v'], catch_exceptions=False)

    assert 'Success' in format_result.stdout
    assert 'CommonServerPython.py' in format_result.stdout
    commonserver_excluded_files = excluded_files[:]
    commonserver_excluded_files.remove('CommonServerPython.py')
    for excluded_file in commonserver_excluded_files:
        assert excluded_file not in format_result.stdout


def test_format_playbook_without_fromversion_no_preset_flag(repo):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack with assume-yes flag without from-version flag

    Then:
        - Ensure format runs successfully
        - Ensure format adds fromversion with the oldest supported version to the playbook.
    """
    pack = repo.create_pack('Temp')
    playbook = pack.create_playbook('my_temp_playbook')
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if 'fromversion' in playbook_content:
        del playbook_content['fromversion']

    assert 'fromversion' not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(playbook.yml.path), '--assume-yes', '-v'])
    assert 'Success' in format_result.stdout
    assert playbook.yml.read_dict().get('fromversion') == OLDEST_SUPPORTED_VERSION


def test_format_playbook_without_fromversion_with_preset_flag(repo):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack with assume-yes flag with from-version flag

    Then:
        - Ensure format runs successfully
        - Ensure format adds fromversion with the given from-version.
    """
    pack = repo.create_pack('Temp')
    playbook = pack.create_playbook('my_temp_playbook')
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if 'fromversion' in playbook_content:
        del playbook_content['fromversion']

    assert 'fromversion' not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(playbook.yml.path), '--assume-yes', '--from-version',
                                         '6.0.0', '-v'])
    assert 'Success' in format_result.stdout
    assert playbook.yml.read_dict().get('fromversion') == '6.0.0'


def test_format_playbook_without_fromversion_with_preset_flag_manual(repo):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack with from-version flag

    Then:
        - Ensure format runs successfully
        - Ensure format adds fromversion with the given from-version.
    """
    pack = repo.create_pack('Temp')
    playbook = pack.create_playbook('my_temp_playbook')
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if 'fromversion' in playbook_content:
        del playbook_content['fromversion']

    assert 'fromversion' not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(playbook.yml.path), '--from-version',
                                         '6.0.0', '-v'], input='y')
    assert 'Success' in format_result.stdout
    assert playbook.yml.read_dict().get('fromversion') == '6.0.0'


def test_format_playbook_without_fromversion_without_preset_flag_manual(repo):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format adds fromversion with the inputted version.
    """
    pack = repo.create_pack('Temp')
    playbook = pack.create_playbook('my_temp_playbook')
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if 'fromversion' in playbook_content:
        del playbook_content['fromversion']

    assert 'fromversion' not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(playbook.yml.path), '-v'], input='y\n5.5.0')
    assert 'Success' in format_result.stdout
    assert playbook.yml.read_dict().get('fromversion') == '5.5.0'


def test_format_playbook_without_fromversion_without_preset_flag_manual_two_tries(repo):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure the format does not except wrong version format.
        - Ensure format adds fromversion with the inputted version.
    """
    pack = repo.create_pack('Temp')
    playbook = pack.create_playbook('my_temp_playbook')
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if 'fromversion' in playbook_content:
        del playbook_content['fromversion']

    assert 'fromversion' not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(playbook.yml.path), '-v'], input='y\n5.5\n5.5.0')
    assert 'Version format is not valid' in format_result.stdout
    assert 'Success' in format_result.stdout
    assert playbook.yml.read_dict().get('fromversion') == '5.5.0'


def test_format_playbook_copy_removed_from_name_and_id(repo):
    """
    Given:
        - A playbook with name and id ending in `_copy`

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format removes `_copy` from both name and id.
    """
    pack = repo.create_pack('Temp')
    playbook = pack.create_playbook('my_temp_playbook')
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    playbook_id = playbook_content['id']
    playbook_name = playbook_content['name']
    playbook_content['id'] = playbook_id + '_copy'
    playbook_content['name'] = playbook_name + '_copy'

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    format_result = runner.invoke(main, [FORMAT_CMD, '-i', str(playbook.yml.path), '-v'], input='y\n5.5.0')
    assert 'Success' in format_result.stdout
    assert playbook.yml.read_dict().get('id') == playbook_id
    assert playbook.yml.read_dict().get('name') == playbook_name
