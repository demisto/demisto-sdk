import os
import shutil
import sys
import uuid
from collections import OrderedDict

import click
import pytest
import yaml
from mock import Mock, patch
from ruamel.yaml import YAML

from demisto_sdk.commands.common.constants import (FEED_REQUIRED_PARAMS,
                                                   FETCH_REQUIRED_PARAMS,
                                                   INTEGRATION)
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import LOG_COLORS, is_string_uuid
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.format.update_generic import BaseUpdate
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_playbook import (PlaybookYMLFormat,
                                                         TestPlaybookYMLFormat)
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.tests.constants_test import (
    DESTINATION_FORMAT_INTEGRATION, DESTINATION_FORMAT_INTEGRATION_COPY,
    DESTINATION_FORMAT_PLAYBOOK, DESTINATION_FORMAT_PLAYBOOK_COPY,
    DESTINATION_FORMAT_SCRIPT_COPY, DESTINATION_FORMAT_TEST_PLAYBOOK,
    FEED_INTEGRATION_EMPTY_VALID, FEED_INTEGRATION_INVALID,
    FEED_INTEGRATION_VALID, GIT_ROOT, INTEGRATION_PATH, PLAYBOOK_PATH,
    PLAYBOOK_WITH_INCIDENT_INDICATOR_SCRIPTS, SOURCE_FORMAT_INTEGRATION_COPY,
    SOURCE_FORMAT_INTEGRATION_INVALID, SOURCE_FORMAT_INTEGRATION_VALID,
    SOURCE_FORMAT_PLAYBOOK, SOURCE_FORMAT_PLAYBOOK_COPY,
    SOURCE_FORMAT_SCRIPT_COPY, SOURCE_FORMAT_TEST_PLAYBOOK, TEST_PLAYBOOK_PATH)
from TestSuite.test_tools import ChangeCWD

ryaml = YAML()
ryaml.preserve_quotes = True
ryaml.allow_duplicate_keys = True

INTEGRATION_TEST_ARGS = (SOURCE_FORMAT_INTEGRATION_COPY, DESTINATION_FORMAT_INTEGRATION_COPY, IntegrationYMLFormat,
                         'New Integration_copy', 'integration')
SCRIPT_TEST_ARGS = (SOURCE_FORMAT_SCRIPT_COPY, DESTINATION_FORMAT_SCRIPT_COPY, ScriptYMLFormat,
                    'New_script_copy', 'script')
PLAYBOOK_TEST_ARGS = (SOURCE_FORMAT_PLAYBOOK_COPY, DESTINATION_FORMAT_PLAYBOOK_COPY, PlaybookYMLFormat,
                      'File Enrichment-GenericV2_copy', 'playbook')

BASIC_YML_TEST_PACKS = [INTEGRATION_TEST_ARGS, SCRIPT_TEST_ARGS, PLAYBOOK_TEST_ARGS]


class TestFormatting:
    @pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', BASIC_YML_TEST_PACKS)
    def test_yml_preserve_comment(self, source_path, destination_path, formatter, yml_title, file_type, capsys):
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
    def test_basic_yml_updates(self, source_path, destination_path, formatter, yml_title, file_type):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
        base_yml = formatter(source_path, path=schema_path)
        base_yml.update_yml(file_type=file_type)
        assert yml_title not in str(base_yml.data)
        assert -1 == base_yml.id_and_version_location['version']

    @pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', [INTEGRATION_TEST_ARGS])
    def test_default_additional_info_filled(self, source_path, destination_path, formatter, yml_title, file_type):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", f'{file_type}.yml'))
        base_yml = IntegrationYMLFormat(source_path, path=schema_path)
        base_yml.set_params_default_additional_info()

        from demisto_sdk.commands.common.default_additional_info_loader import \
            load_default_additional_info_dict
        default_additional_info = load_default_additional_info_dict()

        api_key_param = base_yml.data['configuration'][4]

        tested_api_key_name = 'API key'
        assert api_key_param['name'] == tested_api_key_name
        assert api_key_param.get('additionalinfo') == default_additional_info[tested_api_key_name]

    @pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', BASIC_YML_TEST_PACKS)
    def test_save_output_file(self, source_path, destination_path, formatter, yml_title, file_type):
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
    def test_proxy_ssl_descriptions(self, source_path, argument_name, argument_description, file_type, appearances):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
        base_yml = IntegrationYMLFormat(source_path, path=schema_path, verbose=True)
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
            ('isArray', False),
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
    def test_bang_commands_default_arguments(self, source_path, file_type, bang_command, verifications):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(file_type)))
        base_yml = IntegrationYMLFormat(source_path, path=schema_path, verbose=True)
        base_yml.set_reputation_commands_basic_argument_as_needed()

        for command in base_yml.data['script']['commands']:
            if bang_command == command['name']:
                command_arguments = command['arguments']
                for argument in command_arguments:
                    if argument.get('name', '') == bang_command:
                        for verification in verifications:
                            assert argument[verification[0]] == verification[1]

    def test_isarray_false(self, integration, capsys):
        """
        Given:
        - An integration with IP command and ip argument when isArray is False

        When:
        - Running validate on IP command

        Then:
        - Check a warning printed to the user.
        - Validate isArray hasn't changed.

        """
        yml_contents = integration.yml.read_dict()
        yml_contents['script']['commands'] = [
            {
                'name': 'ip',
                'arguments': [{
                    'isArray': False,
                    'name': 'ip'
                }]
            }
        ]
        integration.yml.write_dict(yml_contents)
        base_yml = IntegrationYMLFormat(integration.yml.path)
        base_yml.set_reputation_commands_basic_argument_as_needed()
        captured = capsys.readouterr()
        assert 'Array field in ip command is set to False.' in captured.out
        assert integration.yml.read_dict()['script']['commands'][0]['arguments'][0]['isArray'] is False

    @pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
    def test_playbook_task_description_name(self, source_path):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
        base_yml = PlaybookYMLFormat(source_path, path=schema_path, verbose=True)
        base_yml.add_description()
        base_yml.update_playbook_task_name()
        base_yml.remove_copy_and_dev_suffixes_from_subplaybook()

        assert 'description' in base_yml.data['tasks']['7']['task']
        assert base_yml.data['tasks']['29']['task']['name'] == 'File Enrichment - Virus Total Private API'
        assert base_yml.data['tasks']['25']['task']['description'] == 'Check if there is a SHA256 hash in context.'

    @pytest.mark.parametrize('source_path', [PLAYBOOK_WITH_INCIDENT_INDICATOR_SCRIPTS])
    def test_remove_empty_scripts_keys_from_playbook(self, source_path):
        """
            Given:
                - Playbook file to format, with empty keys in tasks that uses the
                 [setIncident, SetIndicator, CreateNewIncident, CreateNewIndicator] script
            When:
                - Running the remove_empty_fields_from_scripts function
            Then:
                - Validate that the empty keys were removed successfully
        """
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", "{}.yml".format("playbook")))
        base_yml = PlaybookYMLFormat(source_path, path=schema_path, verbose=True)
        create_new_incident_script_task_args = base_yml.data.get('tasks', {}).get('0').get('scriptarguments')
        different_script_task_args = base_yml.data.get('tasks', {}).get('1').get('scriptarguments')
        create_new_indicator_script_task_args = base_yml.data.get('tasks', {}).get('2').get('scriptarguments')
        set_incident_script_task_args = base_yml.data.get('tasks', {}).get('3').get('scriptarguments')
        set_indicator_script_task_args = base_yml.data.get('tasks', {}).get('4').get('scriptarguments')

        # Assert that empty keys exists in the scripts arguments
        assert 'commandline' in create_new_incident_script_task_args
        assert not create_new_incident_script_task_args['commandline']
        assert 'malicious_description' in different_script_task_args
        assert not different_script_task_args['malicious_description']
        assert 'assigneduser' in create_new_indicator_script_task_args
        assert not create_new_indicator_script_task_args['assigneduser']
        assert 'occurred' in set_incident_script_task_args
        assert not set_incident_script_task_args['occurred']
        assert 'sla' in set_indicator_script_task_args
        assert not set_indicator_script_task_args['sla']

        base_yml.remove_empty_fields_from_scripts()

        # Assert the empty keys were removed from SetIncident, SetIndicator, CreateNewIncident, CreateNewIndicator
        # scripts
        assert 'commandline' not in create_new_incident_script_task_args
        assert 'assigneduser' not in create_new_indicator_script_task_args
        assert 'occurred' not in set_incident_script_task_args
        assert 'sla' not in set_indicator_script_task_args

        # Assert the empty keys are still in the other script arguments
        assert 'malicious_description' in different_script_task_args
        assert not different_script_task_args['malicious_description']

    @pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
    def test_playbook_sourceplaybookid(self, source_path):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
        base_yml = PlaybookYMLFormat(source_path, path=schema_path)
        base_yml.delete_sourceplaybookid()

        assert 'sourceplaybookid' not in base_yml.data

    @pytest.mark.parametrize('yml_file, yml_type', [
        ('format_pwsh_script.yml', 'script'),
        ('format_pwsh_integration.yml', 'integration')
    ])
    def test_pwsh_format(self, tmpdir, yml_file, yml_type):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format(yml_type)))
        dest = str(tmpdir.join('pwsh_format_res.yml'))
        src_file = f'{GIT_ROOT}/demisto_sdk/tests/test_files/{yml_file}'
        if yml_type == 'script':
            format_obj = ScriptYMLFormat(src_file, output=dest, path=schema_path, verbose=True)
        else:
            format_obj = IntegrationYMLFormat(src_file, output=dest, path=schema_path, verbose=True)
        assert format_obj.run_format() == 0
        with open(dest) as f:
            data = yaml.safe_load(f)
        assert data['fromversion'] == '5.5.0'
        assert data['commonfields']['version'] == -1

    PLAYBOOK_TEST = [PLAYBOOK_TEST_ARGS]

    @pytest.mark.parametrize('source_path, destination_path, formatter, yml_title, file_type', PLAYBOOK_TEST)
    def test_string_condition_in_playbook(self, source_path, destination_path, formatter, yml_title, file_type):
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
            yaml_content = yaml.safe_load(f)
            assert 'yes' in yaml_content['tasks']['27']['nexttasks']
        os.remove(saved_file_path)

    FORMAT_FILES = [
        (SOURCE_FORMAT_PLAYBOOK, DESTINATION_FORMAT_PLAYBOOK, PLAYBOOK_PATH, 0)
    ]

    @pytest.mark.parametrize('source, target, path, answer', FORMAT_FILES)
    @patch('builtins.input')
    def test_format_file(self, user_input, source, target, path, answer):
        user_responses = [Mock(), Mock(), Mock()]
        user_responses[0] = 'y'  # answer to update fromVersion choice
        user_responses[1] = '5.0.0'  # version that should be added
        user_responses[2] = 'n'  # answer to adding description question
        user_input.side_effect = user_responses
        os.makedirs(path, exist_ok=True)
        shutil.copyfile(source, target)
        res = format_manager(input=target, output=target, verbose=True)
        os.remove(target)
        os.rmdir(path)

        assert res is answer

    @pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
    def test_remove_unnecessary_keys_from_playbook(self, source_path):
        """
        Given:
            - Playbook file to format, with excessive keys in it
        When:
            - Running the remove_unnecessary_keys function
        Then:
            - Validate that the excessive keys were removed successfully
        """
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
        base_yml = PlaybookYMLFormat(source_path, path=schema_path, verbose=True)

        # Assert the unnecessary keys are indeed in the playbook file
        assert 'excessiveKey' in base_yml.data.keys()
        assert 'itemVersion' in base_yml.data.get('contentitemexportablefields').get('contentitemfields').keys()

        base_yml.remove_unnecessary_keys()

        # Assert the unnecessary keys were successfully removed
        assert 'excessiveKey' not in base_yml.data.keys()
        assert 'itemVersion' not in base_yml.data.get('contentitemexportablefields').get('contentitemfields').keys()

        # One of the inputs has unsupported key 'some_key_to_remove', the inputs schema is a sub-schema and this
        # assertion validates sub-schemas are enforced in format command too.
        for input_ in base_yml.data.get('inputs'):
            assert 'some_key_to_remove' not in input_

    @patch('builtins.input', lambda *args: 'n')
    def test_add_tasks_description_and_empty_playbook_description(self):
        """
        Given:
            - A playbook file with missing playbook description and missing tasks descriptions.

        When:
            - Running the add_description function of update_playbook.py.
            - User's choice not to update the description of the playbook.

        Then:
            - Validate that an empty description was added to the file.
            - Validate that empty descriptions were added only to the desired tasks.
        """
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
        base_yml = PlaybookYMLFormat(SOURCE_FORMAT_PLAYBOOK_COPY, path=schema_path, verbose=True)
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
        assert base_yml.data.get('description') == ''
        assert base_yml.data['tasks']['1']['task']['description'] == ''
        assert base_yml.data['tasks']['2']['task']['description'] == 'else'
        assert 'description' not in base_yml.data['tasks']['3']['task']
        assert base_yml.data['tasks']['4']['task']['description'] == ''
        assert base_yml.data['tasks']['5']['task']['description'] == ''
        assert base_yml.data['tasks']['6']['task']['description'] == ''

    @patch('builtins.input')
    def test_add_playbook_description(self, user_input):
        """
        Given:
            - A playbook file with missing playbook description and missing tasks descriptions.

        When:
            - Running the add_description function of update_playbook.py.
            - User's choice to update the description of the playbook with the description: 'User-entered description'.

        Then:
            - Validate that a description field with the given description message was added to the file.
            - Validate that empty descriptions were added only to the desired tasks.
        """
        user_responses = [Mock(), Mock(), Mock()]
        user_responses[0] = 'err'  # test invalid input by user
        user_responses[1] = 'y'
        user_responses[2] = 'User-entered description'
        user_input.side_effect = user_responses

        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
        base_yml = PlaybookYMLFormat(SOURCE_FORMAT_PLAYBOOK_COPY, path=schema_path, verbose=True)
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
            }
        }
        base_yml.add_description()
        assert base_yml.data.get('description') == 'User-entered description'
        assert base_yml.data['tasks']['1']['task']['description'] == ''
        assert base_yml.data['tasks']['2']['task']['description'] == 'else'
        assert 'description' not in base_yml.data['tasks']['3']['task']

    FORMAT_FILES_FETCH = [
        (SOURCE_FORMAT_INTEGRATION_VALID, DESTINATION_FORMAT_INTEGRATION, INTEGRATION_PATH, 0),
        (SOURCE_FORMAT_INTEGRATION_INVALID, DESTINATION_FORMAT_INTEGRATION, INTEGRATION_PATH, 0)]

    @pytest.mark.parametrize('source, target, path, answer', FORMAT_FILES_FETCH)
    def test_set_fetch_params_in_config(self, mocker, source, target, path, answer, monkeypatch):
        """
        Given
        - Integration yml with isfetch field labeled as true and correct fetch params.
        - Integration yml with isfetch field labeled as true and without the fetch params.
        - destination_path to write the formatted integration to.
        When
        - Running the format command.

        Then
        - Ensure the file was created.
        - Ensure that the isfetch and incidenttype params were added to the yml of the integration.
        """
        mocker.patch.object(IntegrationValidator, 'has_no_fromlicense_key_in_contributions_integration', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_api_token_in_credential_type', return_value=True)

        os.makedirs(path, exist_ok=True)
        shutil.copyfile(source, target)
        monkeypatch.setattr(
            'builtins.input',
            lambda _: 'N'
        )
        res = format_manager(input=target, verbose=True)
        with open(target, 'r') as f:
            yaml_content = yaml.safe_load(f)
            params = yaml_content['configuration']
            for param in params:
                if 'defaultvalue' in param and param['name'] != 'feed':
                    param.pop('defaultvalue')
            for param in FETCH_REQUIRED_PARAMS:
                assert param in yaml_content['configuration']
        os.remove(target)
        os.rmdir(path)
        assert res is answer

    FORMAT_FILES_FEED = [
        (FEED_INTEGRATION_VALID, DESTINATION_FORMAT_INTEGRATION, INTEGRATION_PATH, 0),
        (FEED_INTEGRATION_INVALID, DESTINATION_FORMAT_INTEGRATION, INTEGRATION_PATH, 0)]

    @pytest.mark.parametrize('source, target, path, answer', FORMAT_FILES_FEED)
    def test_set_feed_params_in_config(self, mocker, source, target, path, answer):
        """
        Given
        - Integration yml with feed field labeled as true and all necessary params exist.
        - Integration yml with feed field labeled as true and without the necessary feed params.
        - destination_path to write the formatted integration to.
        When
        - Running the format command.

        Then
        - Ensure the file was created.
        - Ensure that the feedBypassExclusionList, Fetch indicators , feedReputation, feedReliability ,
         feedExpirationPolicy, feedExpirationInterval ,feedFetchInterval params were added to the yml of the integration.
        """
        mocker.patch.object(IntegrationValidator, 'has_no_fromlicense_key_in_contributions_integration', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_api_token_in_credential_type', return_value=True)

        os.makedirs(path, exist_ok=True)
        shutil.copyfile(source, target)
        res = format_manager(input=target, verbose=True)
        with open(target, 'r') as f:
            yaml_content = yaml.safe_load(f)
            params = yaml_content['configuration']
            for counter, param in enumerate(params):
                if 'defaultvalue' in param and param['name'] != 'feed':
                    params[counter].pop('defaultvalue')
                if 'hidden' in param:
                    param.pop('hidden')
            for param_details in FEED_REQUIRED_PARAMS:
                param = {'name': param_details.get('name')}
                param.update(param_details.get('must_equal', dict()))
                param.update(param_details.get('must_contain', dict()))
                assert param in params
        os.remove(target)
        os.rmdir(path)
        assert res is answer

    def test_set_feed_params_in_config_with_default_value(self):
        """
        Given
        - Integration yml with feed field labeled as true and all necessary params exist including defaultvalue fields.

        When
        - Running the format command.

        Then
        - Ensures the defaultvalue fields remain after the execution.
        """
        base_yml = IntegrationYMLFormat(FEED_INTEGRATION_VALID, path="schema_path", verbose=True)
        base_yml.set_feed_params_in_config()
        configuration_params = base_yml.data.get('configuration', [])
        assert 'defaultvalue' in configuration_params[0]

    def test_format_on_feed_integration_adds_feed_parameters(self):
        """
        Given
        - Feed integration yml without feed parameters configured.

        When
        - Running the format command.

        Then
        - Ensures the feed parameters are added.
        """
        base_yml = IntegrationYMLFormat(FEED_INTEGRATION_EMPTY_VALID, path="schema_path", verbose=True)
        base_yml.set_feed_params_in_config()
        configuration_params = base_yml.data.get('configuration', [])
        for param_details in FEED_REQUIRED_PARAMS:
            param = {'name': param_details.get('name')}
            param.update(param_details.get('must_equal', dict()))
            param.update(param_details.get('must_contain', dict()))
            assert param in configuration_params

    def test_set_fetch_params_in_config_with_default_value(self):
        """
        Given
        - Integration yml with isfetch field labeled as true and all necessary params exist including defaultvalue fields.

        When
        - Running the format command.

        Then
        - Ensure the defaultvalue fields remain after the execution.
        - Ensure that the config param with the defaultvalue key is not getting duplicated without the defaultvalue key.
        """
        base_yml = IntegrationYMLFormat(SOURCE_FORMAT_INTEGRATION_VALID, path="schema_path", verbose=True)
        base_yml.set_fetch_params_in_config()
        configuration_params = base_yml.data.get('configuration', [])
        assert 'defaultvalue' in configuration_params[5]
        assert {'display': 'Incident type', 'name': 'incidentType', 'required': False,
                'type': 13} not in configuration_params
        assert {'display': 'Incident type', 'name': 'incidentType', 'required': False, 'type': 13,
                'defaultvalue': ''} in configuration_params

    @pytest.mark.parametrize('source_path', [SOURCE_FORMAT_PLAYBOOK_COPY])
    def test_playbook_task_name(self, source_path):
        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
        base_yml = PlaybookYMLFormat(source_path, path=schema_path)

        assert base_yml.data['tasks']['29']['task'][
            'playbookName'] == 'File Enrichment - Virus Total Private API_dev_copy'
        base_yml.remove_copy_and_dev_suffixes_from_subplaybook()

        assert base_yml.data['tasks']['29']['task']['name'] == 'Fake name'
        assert base_yml.data['tasks']['29']['task']['playbookName'] == 'File Enrichment - Virus Total Private API'

    @patch('builtins.input', lambda *args: 'no')
    def test_run_format_on_tpb(self):
        """
        Given
            - A Test Playbook file, that does not have fromversion key
        When
            - Run format on TPB file
        Then
            - Ensure run_format return value is 0
            - Ensure `fromversion` field set to 5.5.0
        """
        os.makedirs(TEST_PLAYBOOK_PATH, exist_ok=True)
        formatter = TestPlaybookYMLFormat(input=SOURCE_FORMAT_TEST_PLAYBOOK, output=DESTINATION_FORMAT_TEST_PLAYBOOK)
        res = formatter.run_format()
        assert res == 0
        assert formatter.data.get('fromversion') == '5.5.0'
        os.remove(DESTINATION_FORMAT_TEST_PLAYBOOK)
        os.rmdir(TEST_PLAYBOOK_PATH)

    @patch('builtins.input', lambda *args: 'no')
    def test_update_tests_on_integration_with_test_playbook(self):
        """
        Given
            - An integration file.
        When
            - Run format on the integration
        Then
            - Ensure run_format return value is 0
            - Ensure `tests` field gets the Test Playbook ID
        """
        test_files_path = os.path.join(git_path(), 'demisto_sdk', 'tests')
        vmware_integration_yml_path = os.path.join(test_files_path, 'test_files', 'content_repo_example', 'Packs',
                                                   'VMware',
                                                   'Integrations', 'integration-VMware.yml')
        formatter = IntegrationYMLFormat(input=vmware_integration_yml_path, output='')
        res = formatter.update_tests()
        assert res is None
        assert formatter.data.get('tests') == ['VMWare Test']

    @patch('builtins.input', lambda *args: 'no')
    def test_update_tests_on_playbook_with_test_playbook(self):
        """
        Given
            - An integration file.
        When
            - Run format on the integration
        Then
            - Ensure run_format return value is 0
            - Ensure `tests` field gets the Test Playbook ID
        """
        test_files_path = os.path.join(git_path(), 'demisto_sdk', 'tests')
        phishing_playbook_yml_path = os.path.join(test_files_path, 'test_files', 'Packs',
                                                  'Phishing',
                                                  'Playbooks', 'Phishing_Investigation_-_Generic_v2_-_6_0.yml')
        formatter = PlaybookYMLFormat(input=phishing_playbook_yml_path, output='')
        formatter.update_tests()
        assert formatter.data.get('tests') == ['playbook-checkEmailAuthenticity-test']

    @patch('builtins.input', lambda *args: 'no')
    def test_update_tests_on_script_with_test_playbook(self):
        """
        Given
            - An integration file.
        When
            - Run format on the integration
        Then
            - Ensure run_format return value is 0
            - Ensure `tests` field gets the Test Playbook ID
        """
        test_files_path = os.path.join(git_path(), 'demisto_sdk', 'tests')
        email_auth_script_yml_path = os.path.join(test_files_path, 'test_files', 'Packs',
                                                  'Phishing', 'Scripts',
                                                  'CheckEmailAuthenticity.yml')
        formatter = ScriptYMLFormat(input=email_auth_script_yml_path, output='')
        formatter.update_tests()
        assert formatter.data.get('tests') == ['playbook-checkEmailAuthenticity-test']

    def test_update_docker_format(self, tmpdir, mocker, monkeypatch):
        """Test that script and integration formatter update docker image tag
        """
        test_tag = '1.0.0-test-tag'
        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value=test_tag)
        schema_dir = f'{GIT_ROOT}/demisto_sdk/commands/common/schemas'
        test_files_dir = f'{GIT_ROOT}/demisto_sdk/tests/test_files/update-docker'
        dest = str(tmpdir.join('docker-res.yml'))

        # test example script file with version before 5.0.0
        src_file = f'{test_files_dir}/SlackAsk.yml'
        with open(src_file) as f:
            data = yaml.safe_load(f)
        org_docker = data['dockerimage']
        assert data['fromversion'] < '5.0.0'
        assert not data.get(
            'dockerimage45')  # make sure for the test that dockerimage45 is not set (so we can verify that we set it in format)
        format_obj = ScriptYMLFormat(src_file, output=dest, path=f'{schema_dir}/script.yml', no_validate=True,
                                     update_docker=True)
        monkeypatch.setattr(
            'builtins.input',
            lambda _: 'N'
        )

        assert format_obj.run_format() == 0
        with open(dest) as f:
            data = yaml.safe_load(f)
        assert data['dockerimage'].endswith(f':{test_tag}')
        assert data['dockerimage45'] == org_docker

        # test integration file
        src_file = f'{test_files_dir}/Slack.yml'
        format_obj = IntegrationYMLFormat(src_file, output=dest, path=f'{schema_dir}/integration.yml', no_validate=True,
                                          update_docker=True)
        assert format_obj.run_format() == 0
        with open(dest) as f:
            data = yaml.safe_load(f)
        assert data['script']['dockerimage'].endswith(f':{test_tag}')
        assert not data['script'].get('dockerimage45')

    @pytest.mark.parametrize(argnames='docker_image', argvalues=['error:1.0.0.1', 'demisto/error:1.0.0.1'])
    def test_update_docker_format_with_invalid_dockerimage(self, requests_mock, mocker, tmp_path, docker_image, ):
        """
            Given
                - An integration yml file.
            When
                - Run format on the integration
            Then
                - Ensure format runs successfully
                - Verify the docker image is not modified
            """

        auth_token = 'token'
        mocker.patch.object(DockerImageValidator, 'docker_auth', return_value=auth_token)

        requests_mock.get('https://hub.docker.com/v2/repositories/error/tags', json={"detail": "Object not found"},
                          status_code=404)
        requests_mock.get('https://registry-1.docker.io/v2/error/tags/list', json={'error': 'not found'},
                          status_code=401)
        requests_mock.get('https://hub.docker.com/v2/repositories/demisto/error/tags', json={"count": 0,
                                                                                             "next": 'null',
                                                                                             "previous": 'null',
                                                                                             "results": []},
                          status_code=200)
        integration_yml_file_1 = tmp_path / 'Integration1.yml'
        integration_obj = {'dockerimage': docker_image,
                           'fromversion': '5.0.0'}
        ryaml.dump(integration_obj, integration_yml_file_1.open('w'))

        format_obj = ScriptYMLFormat(str(integration_yml_file_1), update_docker=True)
        format_obj.update_docker_image()
        with open(str(integration_yml_file_1)) as f:
            data = yaml.safe_load(f)
        assert data.get('dockerimage') == docker_image

    def test_recursive_extend_schema(self):
        """
            Given
                - A dict that represents a schema with sub-playbooks
            When
                - Run recursive_extend_schema on that schema
            Then
                - Ensure The reference is gone from the modified schema
                - Ensure the 'include' syntax has been replaced by the sub playbook itself
            """
        schema = {
            'mapping': {
                'inputs': {
                    'sequence': [{'include': 'input_schema'}],
                    'type': 'seq'}
            },
            'some-other-key': 'some-other-value'
        }
        sub_schema = {
            'mapping': {
                'required': {'type': 'bool'},
                'value': {'type': 'any'}
            },
            'type': 'map'}
        schema.update({'schema;input_schema': sub_schema})
        modified_schema = BaseUpdate.recursive_extend_schema(schema, schema)
        # Asserting the reference to the sub-playbook no longer exist in the modified schema
        assert 'schema;input_schema' not in modified_schema
        # Asserting the sub-playbook has replaced the reference
        assert modified_schema['mapping']['inputs']['sequence'][0] == sub_schema
        # Asserting some non related keys are not being deleted
        assert 'some-other-key' in modified_schema

    def test_recursive_extend_schema_prints_warning(self, mocker):
        """
            Given
                - A dict that represents a schema with sub-schema reference that has no actual sub-schema
            When
                - Run recursive_extend_schema on that schema
            Then
                - Ensure a warning about the missing sub-schema is printed
            """
        schema = {
            'mapping': {
                'inputs': {
                    'sequence': [{'include': 'input_schema'}],
                    'type': 'seq'}
            },
        }
        mocker.patch('click.echo')
        BaseUpdate.recursive_extend_schema(schema, schema)
        click.echo.assert_called_once_with('Could not find sub-schema for input_schema', LOG_COLORS.YELLOW)

    @staticmethod
    def exception_raise(file_type=''):
        raise ValueError("MY ERROR")

    FORMAT_OBJECT = [
        PlaybookYMLFormat,
        IntegrationYMLFormat,
        TestPlaybookYMLFormat,
        ScriptYMLFormat
    ]

    @pytest.mark.parametrize(argnames='format_object', argvalues=FORMAT_OBJECT)
    def test_yml_run_format_exception_handling(self, format_object, mocker, capsys):
        """
        Given
            - A YML object formatter
        When
            - Run run_format command and and exception is raised.
        Then
            - Ensure the error is printed.
        """
        formatter = format_object(verbose=True, input="my_file_path")
        mocker.patch.object(BaseUpdateYML, 'update_yml', side_effect=self.exception_raise)
        mocker.patch.object(PlaybookYMLFormat, 'update_tests', side_effect=self.exception_raise)
        mocker.patch.object(TestPlaybookYMLFormat, 'update_fromversion_by_user', side_effect=self.exception_raise)

        formatter.run_format()
        stdout, _ = capsys.readouterr()
        assert 'Failed to update file my_file_path. Error: MY ERROR' in stdout

    TEST_UUID_FORMAT_OBJECT = [
        PlaybookYMLFormat,
        TestPlaybookYMLFormat
    ]

    @pytest.mark.parametrize('format_object', TEST_UUID_FORMAT_OBJECT)
    def test_update_task_uuid_(self, format_object):
        """
        Given
            - A test playbook file
        When
            - Run update_task_uuid command
        Then
            - Ensure that all the relevant fields under a task- id and taskid- are from uuid format and for each task
            those fields have the same value
        """

        schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "..", "common", "schemas", '{}.yml'.format('playbook')))
        playbook_yml = format_object(SOURCE_FORMAT_PLAYBOOK_COPY, path=schema_path, verbose=True)
        playbook_yml.data = {
            "tasks": {
                "1": {
                    "taskid": '1',
                    "task": {
                        'id': '1'
                    }
                },
                "2": {
                    "taskid": '2',
                    "task": {
                        'id': 'some_name'
                    }
                }
            }
        }

        playbook_yml.update_task_uuid()
        assert is_string_uuid(playbook_yml.data['tasks']['1']['task']['id']) and \
            is_string_uuid(playbook_yml.data['tasks']['1']['taskid'])
        assert playbook_yml.data['tasks']['1']['task']['id'] == playbook_yml.data['tasks']['1']['taskid']
        assert is_string_uuid(playbook_yml.data['tasks']['2']['task']['id']) and \
            is_string_uuid(playbook_yml.data['tasks']['2']['taskid'])
        assert playbook_yml.data['tasks']['2']['task']['id'] == playbook_yml.data['tasks']['2']['taskid']

    def test_check_for_subplaybook_usages(self, repo):
        """
        Given
            - A test playbook file
        When
            - Run check_for_subplaybook_usages command
        Then
            - Ensure that the subplaybook id is replaced from the uuid to the playbook name.
        """
        pack = repo.create_pack('pack')
        playbook = pack.create_playbook('LargePlaybook')
        test_task = {
            "id": "1",
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
                "name": "my-sub-playbook",
                "playbookId": "03d4f06c-ad13-47dd-8955-c8f7ccd5cba1",
                "type": "playbook",
                "version": -1
            },
            "taskid": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
            "timertriggers": [],
            "type": "playbook"
        }
        playbook.create_default_playbook()
        playbook_data = playbook.yml.read_dict()
        playbook_data['tasks']['1'] = test_task
        playbook.yml.write_dict(playbook_data)
        playbook_yml = PlaybookYMLFormat(SOURCE_FORMAT_PLAYBOOK_COPY, path='', verbose=True)

        with ChangeCWD(repo.path):
            playbook_yml.check_for_subplaybook_usages(file_path=playbook.yml.rel_path,
                                                      current_playbook_id="03d4f06c-ad13-47dd-8955-c8f7ccd5cba1",
                                                      new_playbook_id="my-sub-playbook")

        playbook_data = playbook.yml.read_dict()
        assert playbook_data['tasks']['1']['task']['playbookId'] == "my-sub-playbook"

    def test_set_fromversion_six_new_contributor_pack_no_fromversion(self, pack):
        """
        Given
            - An integration from new contributed pack, with no fromversion key at yml
        When
            - Run format command
        Then
            - Ensure that the integration fromversion is set to 6.0.0
        """
        pack.pack_metadata.update({'support': 'partner', 'currentVersion': '1.0.0'})
        integration = pack.create_integration()
        bs = BaseUpdate(input=integration.yml.path)
        bs.set_fromVersion()
        assert bs.data['fromversion'] == '6.0.0'

    def test_set_fromversion_six_new_contributor_pack(self, pack):
        """
        Given
            - A script, playbook and integration from new contributed pack with fromversion key at the yml
        When
            - Run format command
        Then
            - Ensure that the integration fromversion is set to 6.0.0
        """
        pack.pack_metadata.update({'support': 'partner', 'currentVersion': '1.0.0'})
        script = pack.create_script(yml={'fromversion': '5.0.0'})
        playbook = pack.create_playbook(yml={'fromversion': '5.0.0'})
        integration = pack.create_integration(yml={'fromversion': '5.0.0'})
        for path in [script.yml.path, playbook.yml.path, integration.yml.path]:
            bs = BaseUpdate(input=path)
            bs.set_fromVersion()
            assert bs.data['fromversion'] == '6.0.0', path

    def test_set_fromversion_not_changed_new_contributor_pack(self, pack):
        """
        Given
            - An integration from new contributed pack with fromversion key at yml,
        When
            - Run format command
        Then
            - Ensure that the integration fromversion is not set to 6.0.0
            if it is new contributed pack, this is integration, and its version is 5.5.0 do not change it
        """
        pack.pack_metadata.update({'support': 'partner', 'currentVersion': '1.0.0'})
        integration = pack.create_integration(yml={'fromversion': '5.5.0'})
        bs = BaseUpdate(input=integration.yml.path)
        bs.set_fromVersion(file_type=INTEGRATION)
        assert bs.data['fromversion'] == '5.5.0', integration.yml.path

    @pytest.mark.parametrize('user_input,result_fromversion', [('Y', '5.5.0'), ('N', '5.0.0')])
    def test_set_fromversion_new_pack(self, monkeypatch, pack, user_input, result_fromversion):
        """
        Args: monkeypatch (MagicMock): Patch of the user input

        Given
            - An integration from new pack with fromversion: 5.0.0 at yml,
            - User answer - update fromversion or not
        When
            - Run format command
        Then
            - Ensure that the integration fromversion is set to 5.5.0 if user answers Y,
            and the integration fromversion is reminds 5.0.0 if user answers N
        """
        monkeypatch.setattr(
            'builtins.input',
            lambda _: user_input
        )
        integration = pack.create_integration(yml={'fromversion': '5.0.0'})
        bs = BaseUpdate(input=integration.yml.path)
        bs.set_fromVersion(file_type=INTEGRATION)
        assert bs.data['fromversion'] == result_fromversion

    @pytest.mark.parametrize('user_input, description_result',
                             [('', 'Deprecated. No available replacement.'),
                              ('Replacement entity', 'Deprecated. Use Replacement entity instead.')])
    def test_update_deprecate_in_integration(self, pack, mocker, monkeypatch, user_input, description_result):
        """
        Given
            - An integration yml to deprecate.
        When
            - Running update_deprecate.
        Then
            - Ensure that the yaml fields that need to be changed are changed.
        """
        integration = pack.create_integration('my_integration')
        monkeypatch.setattr(
            'builtins.input',
            lambda _: user_input
        )
        mocker.patch.object(BaseUpdateYML, 'get_id_and_version_path_object', return_value={})
        base_update_yml = BaseUpdateYML(input=integration.yml.path, deprecate=True)
        base_update_yml.update_deprecate(file_type='integration')

        assert base_update_yml.data['deprecated']
        assert base_update_yml.data['tests'] == 'No test'
        assert base_update_yml.data['description'] == description_result

    @pytest.mark.parametrize('user_input, description_result',
                             [('', 'Deprecated. No available replacement.'),
                              ('Replacement entity', 'Deprecated. Use Replacement entity instead.')])
    def test_update_deprecate_in_script(self, pack, mocker, monkeypatch, user_input, description_result):
        """
        Given
            - An script yml to deprecate.
        When
            - Running update_deprecate.
        Then
            - Ensure that the yaml fields that need to be changed are changed.
        """
        script = pack.create_integration('my_script')
        monkeypatch.setattr(
            'builtins.input',
            lambda _: user_input
        )
        mocker.patch.object(BaseUpdateYML, 'get_id_and_version_path_object', return_value={})
        base_update_yml = BaseUpdateYML(input=script.yml.path, deprecate=True)
        base_update_yml.update_deprecate(file_type='script')

        assert base_update_yml.data['deprecated']
        assert base_update_yml.data['tests'] == 'No test'
        assert base_update_yml.data['comment'] == description_result

    @pytest.mark.parametrize('user_input, description_result',
                             [('', 'Deprecated. No available replacement.'),
                              ('Replacement entity', 'Deprecated. Use Replacement entity instead.')])
    def test_update_deprecate_in_playbook(self, pack, mocker, monkeypatch, user_input, description_result):
        """
        Given
            - An playbook yml to deprecate.
        When
            - Running update_deprecate.
        Then
            - Ensure that the yaml fields that need to be changed are changed.
        """
        playbook = pack.create_playbook('my_playbook')
        monkeypatch.setattr(
            'builtins.input',
            lambda _: user_input
        )
        mocker.patch.object(BaseUpdateYML, 'get_id_and_version_path_object', return_value={})
        base_update_yml = BaseUpdateYML(input=playbook.yml.path, deprecate=True)
        base_update_yml.update_deprecate(file_type='playbook')

        assert base_update_yml.data['deprecated']
        assert base_update_yml.data['tests'] == 'No test'
        assert base_update_yml.data['description'] == description_result

    @pytest.mark.parametrize('name', ['MyIntegration', 'MyIntegration ', ' MyIntegration '])
    def test_remove_spaces_end_of_id_and_name(self, pack, mocker, name):
        """
        Given
            - An integration which id doesn't ends with whitespaces.
            - An integration which id ends with spaces.
        When
            - Running format.
        Then
            - Ensure that the yaml fields (name, id) that need to be changed are changed.
        """
        integration = pack.create_integration(name)
        integration.yml.write_dict({'commonfields': {'id': name}, 'name': name})
        mocker.patch.object(BaseUpdateYML, 'get_id_and_version_path_object', return_value={'id': name})
        base_update_yml = BaseUpdateYML(input=integration.yml.path)
        base_update_yml.remove_spaces_end_of_id_and_name()
        assert base_update_yml.data['name'] == 'MyIntegration'

    def test_sync_to_master_no_change(self, mocker, tmp_path):
        """
        Given
            A yml which is sorted in a different order than master, but same content.
        When
            - Running format with sync_to_master enabled
        Then
            - Ensure that the result is in the same order as master
        """
        import demisto_sdk.commands.format.update_generic as update_generic

        test_files_path = os.path.join(git_path(), 'demisto_sdk', 'tests')
        vmware_integration_yml_path = os.path.join(test_files_path, 'test_files', 'content_repo_example', 'Packs',
                                                   'VMware',
                                                   'Integrations', 'integration-VMware.yml')
        with open(vmware_integration_yml_path) as f:
            yml_example = yaml.safe_load(f)
        sorted_yml_file = tmp_path / 'test.yml'
        with sorted_yml_file.open('w') as f:
            yaml.dump(yml_example, f, sort_keys=True)  # sorting the keys to have different order
        mocker.patch.object(BaseUpdateYML, 'get_id_and_version_path_object', return_value={'id': "vmware"})
        mocker.patch.object(update_generic, 'get_remote_file', return_value=yml_example)
        base_update_yml = BaseUpdateYML(input=str(sorted_yml_file))
        base_update_yml.sync_data_to_master()
        assert OrderedDict(base_update_yml.data) == OrderedDict(yml_example)

    def test_sync_to_master_with_change(self, mocker, tmp_path):
        """
        Given
            A yml which is sorted in a different order than master, and the content is changed
        When
            - Running format with sync_to_master enabled
        Then
            - Ensure that the result is the changed result to make sure that the patching works
        """
        import demisto_sdk.commands.format.update_generic as update_generic
        test_files_path = os.path.join(git_path(), 'demisto_sdk', 'tests')
        vmware_integration_yml_path = os.path.join(test_files_path, 'test_files', 'content_repo_example', 'Packs',
                                                   'VMware',
                                                   'Integrations', 'integration-VMware.yml')
        with open(vmware_integration_yml_path) as f:
            yml_example = yaml.safe_load(f)
        sorted_yml_file = tmp_path / 'test.yml'
        with sorted_yml_file.open('w') as f:
            yaml.dump(yml_example, f, sort_keys=True)  # sorting the keys to have different order
        with sorted_yml_file.open() as f:
            sorted_yml = yaml.safe_load(f)
        sorted_yml['description'] = 'test'
        sorted_yml['configuration'][0]['defaultvalue'] = 'test'
        del sorted_yml['configuration'][1]['defaultvalue']
        sorted_yml['script']['commands'][0]['outputs'].append({"contextPath": "VMWare.test", "description": "VM test"})
        with sorted_yml_file.open('w') as f:
            yaml.dump(sorted_yml, f)

        mocker.patch.object(BaseUpdateYML, 'get_id_and_version_path_object', return_value={'id': "vmware"})
        mocker.patch.object(update_generic, 'get_remote_file', return_value=yml_example)
        base_update_yml = BaseUpdateYML(input=str(sorted_yml_file))
        base_update_yml.sync_data_to_master()
        assert base_update_yml.data == sorted_yml
        assert OrderedDict(base_update_yml.data) != OrderedDict(sorted_yml)

    def test_equal_id_and_name_integartion(self, pack, mocker):
        """
        Given
            - A new integration yml which is the `id` value and `name` value are not equal
        When
            - Running format on an integration
        Then
            - The `id` value should be changed to the `name` value
        """

        import demisto_sdk.commands.format.update_generic as update_generic
        name = 'my_integration'
        integration = pack.create_integration()
        uid = str(uuid.uuid4())
        integration.yml.write_dict({'commonfields': {'id': uid}, 'name': name})
        mocker.patch.object(update_generic, 'get_remote_file', return_value=None)
        base_yml = IntegrationYMLFormat(input=integration.yml.path)
        base_yml.update_id_to_equal_name()
        assert base_yml.data.get('commonfields', {}).get('id') == name

    def test_equal_id_and_name_playbook(self, pack, mocker):
        """
        Given
            - A new playbook yml which is the `id` and `name` are not equal
        When
            - Running format on a playbook
        Then
            - The `id` value should be changed to the `name` value
        """
        import demisto_sdk.commands.format.update_generic as update_generic
        name = 'my_playbook'
        playbook = pack.create_playbook()
        uid = str(uuid.uuid4())
        playbook.yml.write_dict({'id': uid, 'name': name})
        mocker.patch.object(update_generic, 'get_remote_file', return_value=None)
        base_yml = IntegrationYMLFormat(input=playbook.yml.path)
        base_yml.update_id_to_equal_name()
        assert base_yml.data.get('id') == name

    def test_equal_id_and_name_integartion_from_master(self, pack, mocker):
        """
        Given
            - A modified integration yml which is the new `id` value is not equal to the old `id` value
        When
            - Running format on an integration
        Then
            - The `id` value should be changed to its old `id` value
        """
        import demisto_sdk.commands.format.update_generic as update_generic
        name = 'my_integration'
        integration = pack.create_integration()
        uid = str(uuid.uuid4())
        integration.yml.write_dict({'commonfields': {'id': name}, 'name': name})
        mocker.patch.object(update_generic, 'get_remote_file', return_value={'commonfields': {'id': uid}})
        base_yml = IntegrationYMLFormat(input=integration.yml.path)
        base_yml.update_id_to_equal_name()
        assert base_yml.data.get('commonfields', {}).get('id') == uid

    def test_equal_id_and_name_playbook_from_master(self, pack, mocker):
        """
        Given
            - A modified playbook yml which is the new `id` value is not equal to the old `id` value
        When
            - Running format on a playbook
        Then
            - The `id` value should be changed to its old `id` value
        """
        import demisto_sdk.commands.format.update_generic as update_generic
        name = 'my_playbook'
        playbook = pack.create_playbook()
        uid = str(uuid.uuid4())
        playbook.yml.write_dict({'id': name, 'name': name})
        mocker.patch.object(update_generic, 'get_remote_file', return_value={'id': uid})
        base_yml = IntegrationYMLFormat(input=playbook.yml.path)
        base_yml.update_id_to_equal_name()
        assert base_yml.data.get('id') == uid
