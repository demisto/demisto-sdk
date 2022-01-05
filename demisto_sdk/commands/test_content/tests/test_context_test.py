import ast
import json
import logging
from functools import partial

import pytest

from demisto_sdk.commands.common.constants import PB_Status
from demisto_sdk.commands.test_content.Docker import Docker
from demisto_sdk.commands.test_content.TestContentClasses import (
    Integration, TestConfiguration, TestContext, TestPlaybook)
from demisto_sdk.commands.test_content.tests.build_context_test import (
    generate_content_conf_json, generate_integration_configuration,
    generate_secret_conf_json, generate_test_configuration,
    get_mocked_build_context)
from demisto_sdk.commands.test_content.tests.DemistoClientMock import \
    DemistoClientMock
from demisto_sdk.commands.test_content.tests.server_context_test import \
    generate_mocked_server_context


def test_is_runnable_on_this_instance(mocker):
    """
    Given:
        - A test configuration configured to run only on instances that uses docker as container engine
    When:
        - The method _is_runnable_on_current_server_instance is invoked from the TestContext class
    Then:
        - Ensure that it returns False when the test is running on REHL instance that uses podman
        - Ensure that it returns True when the test is running on a regular Linux instance that uses docker
    """
    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(playbook_id='playbook_runnable_only_on_docker',
                                    runnable_on_docker_only=True), default_test_timeout=30)
    test_context_builder = partial(TestContext,
                                   build_context=mocker.MagicMock(),
                                   playbook=TestPlaybook(mocker.MagicMock(),
                                                         test_playbook_configuration),
                                   client=mocker.MagicMock())

    test_context = test_context_builder(server_context=mocker.MagicMock(is_instance_using_docker=False))
    assert not test_context._is_runnable_on_current_server_instance()
    test_context = test_context_builder(server_context=mocker.MagicMock(is_instance_using_docker=True))
    assert test_context._is_runnable_on_current_server_instance()


def test_second_playback_enforcement(mocker, tmp_path):
    """
    Given:
        - A mockable test
    When:
        - The mockable test fails on the second playback
    Then:
        - Ensure that it exists in the failed_playbooks set
        - Ensure that it does not exists in the succeeded_playbooks list
    """

    class RunIncidentTestMock:
        call_count = 0
        count_response_mapping = {
            1: PB_Status.FAILED,  # The first playback run
            2: PB_Status.COMPLETED,  # The record run
            3: PB_Status.FAILED  # The second playback run
        }

        @staticmethod
        def run_incident_test(*_):
            # First playback run
            RunIncidentTestMock.call_count += 1
            return RunIncidentTestMock.count_response_mapping[RunIncidentTestMock.call_count]

    filtered_tests = ['mocked_playbook']
    tests = [generate_test_configuration(playbook_id='mocked_playbook',
                                         integrations=['mocked_integration'])]
    integrations_configurations = [generate_integration_configuration('mocked_integration')]
    secret_test_conf = generate_secret_conf_json(integrations_configurations)
    content_conf_json = generate_content_conf_json(tests=tests)
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             secret_conf_json=secret_test_conf,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests)
    mocked_demisto_client = DemistoClientMock(integrations=['mocked_integration'])
    server_context = generate_mocked_server_context(build_context, mocked_demisto_client, mocker)
    mocker.patch('demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test',
                 RunIncidentTestMock.run_incident_test)
    server_context.execute_tests()
    assert 'mocked_playbook (Second Playback)' in build_context.tests_data_keeper.failed_playbooks
    assert 'mocked_playbook' not in build_context.tests_data_keeper.succeeded_playbooks


def test_docker_thresholds_for_non_pwsh_integrations(mocker):
    """
    Given:
        - A test context with a playbook that uses a python integration
    When:
        - Running 'get_threshold_values' method
    Then:
        - Ensure that the memory threshold is the default python memory threshold value
        - Ensure that the pis threshold is the default python pid threshold value
    """
    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(playbook_id='playbook_runnable_only_on_docker',
                                    integrations=['integration']), default_test_timeout=30)
    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    playbook_instance.integrations[0].integration_type = Docker.PYTHON_INTEGRATION_TYPE
    test_context = TestContext(build_context=mocker.MagicMock(),
                               playbook=playbook_instance,
                               client=mocker.MagicMock(),
                               server_context=mocker.MagicMock())
    memory_threshold, pid_threshold = test_context.get_threshold_values()
    assert memory_threshold == Docker.DEFAULT_CONTAINER_MEMORY_USAGE
    assert pid_threshold == Docker.DEFAULT_CONTAINER_PIDS_USAGE


def test_docker_thresholds_for_pwsh_integrations(mocker):
    """
    Given:
        - A test context with a playbook that uses a powershell integration
    When:
        - Running 'get_threshold_values' method
    Then:
        - Ensure that the memory threshold is the default powershell memory threshold value
        - Ensure that the pis threshold is the default powershell pid threshold value
    """
    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(playbook_id='playbook_runnable_only_on_docker',
                                    integrations=['integration']), default_test_timeout=30)
    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    playbook_instance.integrations[0].integration_type = Docker.POWERSHELL_INTEGRATION_TYPE
    test_context = TestContext(build_context=mocker.MagicMock(),
                               playbook=playbook_instance,
                               client=mocker.MagicMock(),
                               server_context=mocker.MagicMock())
    memory_threshold, pid_threshold = test_context.get_threshold_values()
    assert memory_threshold == Docker.DEFAULT_PWSH_CONTAINER_MEMORY_USAGE
    assert pid_threshold == Docker.DEFAULT_PWSH_CONTAINER_PIDS_USAGE


class TestPrintContextToLog:

    @staticmethod
    def create_playbook_instance(mocker):
        test_playbook_configuration = TestConfiguration(generate_test_configuration(
            playbook_id='playbook_with_context',
            integrations=['integration']
        ),
            default_test_timeout=30)
        pb_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
        pb_instance.build_context.logging_module = mocker.MagicMock()
        return pb_instance

    def test_print_context_to_log__success(self, mocker):
        """
        Given:
            - A test context with a context_print_dt value
            - The context result is a string "{'foo': 'goo'}"
        When:
            - Running 'print_context_to_log' method
        Then:
            - Ensure that a proper json result is being printed to the context
        """
        dt_result = "{'foo': 'goo'}"
        expected_result = json.dumps(ast.literal_eval(dt_result), indent=4)
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = (dt_result, 200)
        playbook_instance.print_context_to_log(client, incident_id='1')
        assert playbook_instance.build_context.logging_module.info.call_args[0][0] == expected_result

    def test_print_context_to_log__empty(self, mocker):
        """
        Given:
            - A test context with a context_print_dt value
            - The context result is empty
        When:
            - Running 'print_context_to_log' method
        Then:
            - Ensure that an empty result is being printed to the context
        """
        expected_dt = '{}'
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = (expected_dt, 200)
        playbook_instance.print_context_to_log(client, incident_id='1')
        assert playbook_instance.build_context.logging_module.info.call_args[0][0] == expected_dt

    def test_print_context_to_log__none(self, mocker):
        """
        Given:
            - A test context with a context_print_dt value
            - The context result is None
        When:
            - Running 'print_context_to_log' method
        Then:
            - Ensure that an exception is raised and handled via logging error
        """
        expected_dt = None
        expected_error = 'unable to parse result for result with value: None'
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = (expected_dt, 200)
        playbook_instance.print_context_to_log(client, incident_id='1')
        assert playbook_instance.build_context.logging_module.error.call_args[0][0] == expected_error

    def test_print_context_to_log__error(self, mocker):
        """
        Given:
            - A test context with a context_print_dt value
            - The context return with an HTTP error code
        When:
            - Running 'print_context_to_log' method
        Then:
            - Ensure that an exception is raised and handled via logging error messages
        """
        expected_dt = 'No Permission'
        expected_first_error = 'incident context fetch failed with Status code 403'
        expected_second_error = f"('{expected_dt}', 403)"
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = (expected_dt, 403)
        playbook_instance.print_context_to_log(client, incident_id='1')
        assert playbook_instance.build_context.logging_module.error.call_args_list[0][0][0] == expected_first_error
        assert playbook_instance.build_context.logging_module.error.call_args_list[1][0][0] == expected_second_error


def test_replacing_placeholders(mocker, tmp_path):
    """
    Given:
        - Integration with placeholders, different servers
    When:
        - Calling _set_integration_params during creating integrations configurations
    Then:
        - Ensure that replacing placeholders happens not in place,
        and next integration with same build_context, will able to replace '%%SERVER_HOST%%' placeholder.
    """
    # Setting up the build context
    filtered_tests = ['playbook_integration',
                      'playbook_second_integration']
    # Setting up the content conf.json
    tests = [generate_test_configuration(playbook_id='playbook_integration',
                                         integrations=['integration_with_placeholders']),
             generate_test_configuration(playbook_id='playbook_second_integration',
                                         integrations=['integration_with_placeholders'])
             ]
    content_conf_json = generate_content_conf_json(tests=tests,
                                                   unmockable_integrations={'FirstIntegration': 'reason'},
                                                   skipped_tests={})
    # Setting up the content-test-conf conf.json
    integration_names = ['integration_with_placeholders']
    integrations_configurations = [generate_integration_configuration(name=integration_name,
                                                                      params={'url': '%%SERVER_HOST%%/server'})
                                   for integration_name in integration_names]
    secret_test_conf = generate_secret_conf_json(integrations_configurations)

    # Setting up the build_context instance
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             secret_conf_json=secret_test_conf,
                                             filtered_tests_content=filtered_tests)

    integration = Integration(build_context, 'integration_with_placeholders', ['instance'])
    integration._set_integration_params(server_url='1.1.1.1', playbook_id='playbook_integration', is_mockable=False)
    integration = Integration(build_context, 'integration_with_placeholders', ['instance'])
    integration._set_integration_params(server_url='1.2.3.4', playbook_id='playbook_integration', is_mockable=False)
    assert '%%SERVER_HOST%%' in build_context.secret_conf.integrations[0].params.get('url')


CASES = [
    (  # case one input is found
        {'id': 'pb_test',
         'inputs': [{'key': 'Endpoint_hostname', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The hostname of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'ManualHunting.DetectedHosts', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'Hosts that were detected as infected during the manual hunting.',
                     'playbookInputQuery': None},
                    {'key': 'Endpoint_ip', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The IP of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'Endpoint_id', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The ID of the endpoint to isolate.', 'playbookInputQuery': None}],
         },
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostname": {
                    "simple": "test"
                },
            }
        },
        [{'key': 'Endpoint_hostname', 'value': {'simple': 'test', 'complex': None}, 'required': False,
          'description': 'The hostname of the endpoint to isolate.', 'playbookInputQuery': None}, {
             'key': 'ManualHunting.DetectedHosts', 'value': {'simple': '', 'complex': None}, 'required': False,
             'description': 'Hosts that were detected as infected during the manual hunting.',
             'playbookInputQuery': None}, {'key': 'Endpoint_ip', 'value': {'simple': '', 'complex': None},
                                           'required': False, 'description': 'The IP of the endpoint to isolate.',
                                           'playbookInputQuery': None}, {'key': 'Endpoint_id',
                                                                         'value': {'simple': '', 'complex': None},
                                                                         'required': False,
                                                                         'description': 'The ID of the endpoint to isolate.',
                                                                         'playbookInputQuery': None}]

    ),
]


@pytest.mark.parametrize('current, new_configuration, expected', CASES)
def test_replacing_pb_inputs(mocker, current, new_configuration, expected):
    from demisto_sdk.commands.test_content.TestContentClasses import demisto_client, \
        replace_external_playbook_configuration
    from demisto_client.demisto_api import DefaultApi

    class clientMock(DefaultApi):
        def generic_request(self, path, method, body=None, **kwargs):
            if path == '/about' and method == 'GET':
                return ("{'demistoVersion': '6.5.0'}", None, None)

    def generic_request_func(self, path, method, body=None, **kwargs):
        if path == '/playbook/inputs/pb_test' and method == 'POST':
            assert body == expected
        elif path == '/playbook/pb_test' and method == 'GET':
            return current, None, None
        else:
            assert False  # Unexpected path

    mocker.patch.object(demisto_client, 'generic_request_func', side_effect=generic_request_func)

    replace_external_playbook_configuration(clientMock(), new_configuration)


BAD_CASES = [
    (  # case no configuration found
        {'id': 'pb_test',
         'inputs': [{'key': 'Endpoint_hostname', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The hostname of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'ManualHunting.DetectedHosts', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'Hosts that were detected as infected during the manual hunting.',
                     'playbookInputQuery': None},
                    {'key': 'Endpoint_ip', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The IP of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'Endpoint_id', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The ID of the endpoint to isolate.', 'playbookInputQuery': None}],
         },
        {},
        '6.5.0',
        'External Playbook Configuration not provided, skipping re-configuration.'
    ),
    (  # case configuration found in older version
        {'id': 'pb_test',
         'inputs': [{'key': 'Endpoint_hostname', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The hostname of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'ManualHunting.DetectedHosts', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'Hosts that were detected as infected during the manual hunting.',
                     'playbookInputQuery': None},
                    {'key': 'Endpoint_ip', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The IP of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'Endpoint_id', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The ID of the endpoint to isolate.', 'playbookInputQuery': None}],
         },
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostname": {
                    "simple": "test"
                },
            }
        },
        '6.0.0',
        'External Playbook not supported in versions previous to 6.2.0, skipping re-configuration.'
    ),
]


@pytest.mark.parametrize('current, new_configuration, version, expected_error', BAD_CASES)
def test_replacing_pb_inputs_fails_with_build_pass(mocker, current, new_configuration, version, expected_error):
    from demisto_sdk.commands.test_content.TestContentClasses import demisto_client, \
        replace_external_playbook_configuration
    from demisto_client.demisto_api import DefaultApi

    class clientMock(DefaultApi):
        def generic_request(self, path, method, body=None, **kwargs):
            if path == '/about' and method == 'GET':
                return str({'demistoVersion': version}), None, None

    class LoggerMock(logging.Logger):
        def info(self, text, **kwargs):
            if text not in ['External Playbook in use, starting re-configuration.', 'Saved current configuration.']:
                assert text == expected_error

    def generic_request_func(self, path, method, body=None, **kwargs):
        if path == '/playbook/inputs/pb_test' and method == 'POST':
            return
        elif path == '/playbook/pb_test' and method == 'GET':
            return current, None, None
        else:
            assert False  # Unexpected path

    mocker.patch.object(demisto_client, 'generic_request_func', side_effect=generic_request_func)

    replace_external_playbook_configuration(clientMock(), new_configuration, LoggerMock('test logger'))


BAD_CASES_BUILD_FAIL = [
    (  # case configuration not found.
        {"id": "createPlaybookErr", "status": 400, "title": "Could not create playbook",
         "detail": "Could not create playbook", "error": "Item not found (8)", "encrypted": None, "multires": None},
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostname": {
                    "simple": "test"
                },
            }
        },
        '6.2.0',
        'External Playbook was not found or has no inputs.'
    ),
    (  # case configuration was found but wrong input key given.
        {'id': 'pb_test',
         'inputs': [{'key': 'Endpoint_hostname', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The hostname of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'ManualHunting.DetectedHosts', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'Hosts that were detected as infected during the manual hunting.',
                     'playbookInputQuery': None},
                    {'key': 'Endpoint_ip', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The IP of the endpoint to isolate.', 'playbookInputQuery': None},
                    {'key': 'Endpoint_id', 'value': {'simple': '', 'complex': None}, 'required': False,
                     'description': 'The ID of the endpoint to isolate.', 'playbookInputQuery': None}],
         },
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostnames": {
                    "simple": "test"
                },
            }
        },
        '6.2.0',
        'Some input keys was not found in playbook: Endpoint_hostnames.'
    ),

]


@pytest.mark.parametrize('current, new_configuration, version, expected_error', BAD_CASES_BUILD_FAIL)
def test_replacing_pb_inputs_fails_with_build_fail(mocker, current, new_configuration, version, expected_error):
    from demisto_sdk.commands.test_content.TestContentClasses import demisto_client, \
        replace_external_playbook_configuration
    from demisto_client.demisto_api import DefaultApi

    class clientMock(DefaultApi):
        def generic_request(self, path, method, body=None, **kwargs):
            if path == '/about' and method == 'GET':
                return str({'demistoVersion': version}), None, None

    def generic_request_func(self, path, method, body=None, **kwargs):
        if path == '/playbook/inputs/pb_test' and method == 'POST':
            return
        elif path == '/playbook/pb_test' and method == 'GET':
            return current, None, None
        else:
            assert False  # Unexpected path

    mocker.patch.object(demisto_client, 'generic_request_func', side_effect=generic_request_func)

    with pytest.raises(Exception) as e:
        replace_external_playbook_configuration(clientMock(), new_configuration)
    assert str(e.value) == expected_error
