import json
import os
from pathlib import PosixPath
from typing import List

import pytest
import yaml
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.tools import (get_dict_from_file,
                                               is_test_config_match)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.tests.constants_test import (
    DESTINATION_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY,
    INTEGRATION_WITH_TEST_PLAYBOOKS, PLAYBOOK_WITH_TEST_PLAYBOOKS,
    SOURCE_FORMAT_INTEGRATION_COPY, SOURCE_FORMAT_PLAYBOOK_COPY)

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
    assert '=======Starting updates for file: ' in result.stdout
    assert f'Format Status   on file: {source_playbook_path} - Success' in result.stdout
    with open(playbook_path, 'r') as f:
        content = f.read()
        yaml_content = yaml.load(content)
        assert 'sourceplaybookid' not in yaml_content

    assert not result.exception
