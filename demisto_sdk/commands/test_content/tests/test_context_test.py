import ast
import json
from functools import partial

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


# def test_replacing_pb_inputs(mocker, ):
#     def request_mocker(client, method, path, response_type):
#         assert
#
#     test_playbook_configuration = TestConfiguration(
#         generate_test_configuration(playbook_id='playbook_runnable_only_on_docker',
#                                     integrations=['integration']), default_test_timeout=30)
#     playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
#     playbook_instance.integrations[0].integration_type = Docker.PYTHON_INTEGRATION_TYPE
#     test_context = TestContext(build_context=mocker.MagicMock(),
#                                playbook=playbook_instance,
#                                client=mocker.MagicMock(),
#                                server_context=mocker.MagicMock())
#     new_configuration = {
#             "integrations": "VMware Carbon Black EDR v2",
#             "playbookID": "pb_test",
#             "external_playbook_config": {"playbookID": "Isolate Endpoint - Generic V2",
#                                         "input_parameters":{"Endpoint_hostname": {"simple": "test"}}}
#         }
#     current_config = {'id': 'ExamplePlaybook', 'version': 3, 'modified': '2021-12-27T07:38:25.309186328Z', 'sortValues': None, 'packID': 'CommonPlaybooks', 'itemVersion': '2.1.5', 'fromServerVersion': '5.5.0', 'toServerVersion': '', 'propagationLabels': [], 'packPropagationLabels': ['all'], 'vcShouldIgnore': False, 'vcShouldKeepItemLegacyProdMachine': False, 'commitMessage': '', 'shouldCommit': False, 'roles': [], 'allRead': False, 'allReadWrite': False, 'previousRoles': [], 'previousAllRead': False, 'previousAllReadWrite': False, 'hasRole': False, 'dbotCreatedBy': '', 'name': 'Isolate Endpoint - Generic V2', 'nameRaw': 'Isolate Endpoint - Generic V2', 'prevName': 'Isolate Endpoint - Generic V2', 'comment': 'This playbook isolates a given endpoint via various endpoint product integrations.\nMake sure to provide the valid playbook input for the integration you are using.', 'startTaskId': '0', 'tasks': {'0': {'id': '0', 'taskId': '20f01f93-7b37-4f3f-8c17-a466dac351ef', 'type': 'start', 'task': {'id': '20f01f93-7b37-4f3f-8c17-a466dac351ef', 'version': 2, 'modified': '2021-12-27T07:38:25.309055422Z', 'sortValues': None, 'name': '', 'playbookName': '', 'isLocked': False, 'type': '', 'conditions': None, 'isCommand': False, 'brand': ''}, 'nextTasks': {'#none#': ['6', '7', '9', '10', '11']}, 'scriptArguments': None, 'reputationCalc': 0, 'separateContext': False, 'restrictedCompletion': False, 'view': {'position': {'x': 910, 'y': 50}}, 'note': False, 'evidenceData': {'description': None, 'occurred': None, 'tags': None}, 'quietMode': 0, 'isOverSize': False, 'isAutoSwitchedToQuietMode': False}, '10': {'id': '10', 'taskId': '48226108-0787-44b0-80f6-cf333758b5e8', 'type': 'playbook', 'task': {'id': '48226108-0787-44b0-80f6-cf333758b5e8', 'version': 2, 'modified': '2021-12-27T07:38:25.309129176Z', 'sortValues': None, 'name': 'FireEye HX - Isolate Endpoint', 'description': 'This playbook will auto isolate endpoints by the endpoint ID that was provided in the playbook.', 'playbookName': 'FireEye HX - Isolate Endpoint', 'isLocked': False, 'type': 'playbook', 'conditions': None, 'isCommand': False, 'brand': ''}, 'nextTasks': {'#none#': ['2']}, 'scriptArguments': {'Endpoint_id': {'simple': '${inputs.Endpoint_id}', 'complex': None}, 'Hostname': {'simple': '${inputs.Endpoint_hostname}', 'complex': None}}, 'reputationCalc': 0, 'separateContext': True, 'restrictedCompletion': False, 'loop': {'scriptName': '', 'exitCondition': '', 'wait': 1, 'max': 100}, 'view': {'position': {'x': 1770, 'y': 195}}, 'note': False, 'evidenceData': {'description': None, 'occurred': None, 'tags': None}, 'skipUnavailable': True, 'quietMode': 0, 'isOverSize': False, 'isAutoSwitchedToQuietMode': False}, '11': {'id': '11', 'taskId': '04a17761-3b84-492f-87c6-ef29fc4adc7d', 'type': 'playbook', 'task': {'id': '04a17761-3b84-492f-87c6-ef29fc4adc7d', 'version': 3, 'modified': '2021-12-27T07:38:25.309039378Z', 'sortValues': None, 'name': 'Block Endpoint - Carbon Black Response V2', 'description': 'Carbon Black Response - isolate an endpoint for a given hostname.', 'playbookId': 'Block Endpoint - Carbon Black Response V2', 'playbookName': '', 'isLocked': False, 'type': 'playbook', 'conditions': None, 'isCommand': False, 'brand': ''}, 'nextTasks': {'#none#': ['2']}, 'scriptArguments': {'Hostname': {'simple': '${inputs.Endpoint_hostname}', 'complex': None}, 'Sensor_id': {'simple': '${inputs.Endpoint_id}', 'complex': None}}, 'reputationCalc': 0, 'separateContext': True, 'restrictedCompletion': False, 'loop': {'scriptName': '', 'exitCondition': '', 'wait': 1, 'max': 100}, 'view': {'position': {'x': 910, 'y': 195}}, 'note': False, 'evidenceData': {'description': None, 'occurred': None, 'tags': None}, 'skipUnavailable': True, 'quietMode': 0, 'isOverSize': False, 'isAutoSwitchedToQuietMode': False}, '2': {'id': '2', 'taskId': '050d36dd-0ec3-4490-827e-e210ac5e9a04', 'type': 'title', 'task': {'id': '050d36dd-0ec3-4490-827e-e210ac5e9a04', 'version': 2, 'modified': '2021-12-27T07:38:25.309073299Z', 'sortValues': None, 'name': 'Done', 'playbookName': '', 'isTitleTask': True, 'isLocked': False, 'type': 'title', 'conditions': None, 'isCommand': False, 'brand': ''}, 'nextTasks': None, 'scriptArguments': None, 'reputationCalc': 0, 'separateContext': False, 'restrictedCompletion': False, 'view': {'position': {'x': 910, 'y': 370}}, 'note': False, 'evidenceData': {'description': None, 'occurred': None, 'tags': None}, 'quietMode': 0, 'isOverSize': False, 'isAutoSwitchedToQuietMode': False}, '6': {'id': '6', 'taskId': '31a268a0-3862-4dcb-8549-b55d0ad936a0', 'type': 'playbook', 'task': {'id': '31a268a0-3862-4dcb-8549-b55d0ad936a0', 'version': 2, 'modified': '2021-12-27T07:38:25.309087067Z', 'sortValues': None, 'name': 'Isolate Endpoint - Cybereason', 'description': 'This playbook isolates an endpoint based on the hostname provided.', 'playbookName': 'Isolate Endpoint - Cybereason', 'isLocked': False, 'type': 'playbook', 'conditions': None, 'isCommand': False, 'brand': ''}, 'nextTasks': {'#none#': ['2']}, 'scriptArguments': {'Hostname': {'simple': '${inputs.Endpoint_hostname}', 'complex': None}}, 'reputationCalc': 0, 'separateContext': True, 'restrictedCompletion': False, 'loop': {'scriptName': '', 'exitCondition': '', 'wait': 1, 'max': 100}, 'view': {'position': {'x': 50, 'y': 195}}, 'note': False, 'evidenceData': {'description': None, 'occurred': None, 'tags': None}, 'skipUnavailable': True, 'quietMode': 0, 'isOverSize': False, 'isAutoSwitchedToQuietMode': False}, '7': {'id': '7', 'taskId': '46562ad2-14ed-4064-8ce8-9adfb791d660', 'type': 'playbook', 'task': {'id': '46562ad2-14ed-4064-8ce8-9adfb791d660', 'version': 2, 'modified': '2021-12-27T07:38:25.30910066Z', 'sortValues': None, 'name': 'Cortex XDR - Isolate Endpoint', 'description': "This playbook accepts an XDR endpoint ID and isolates it using the 'Palo Alto Networks Cortex XDR - Investigation and Response' integration.", 'playbookName': 'Cortex XDR - Isolate Endpoint', 'isLocked': False, 'type': 'playbook', 'conditions': None, 'isCommand': False, 'brand': ''}, 'nextTasks': {'#none#': ['2']}, 'scriptArguments': {'endpoint_id': {'simple': '${inputs.Endpoint_id}', 'complex': None}, 'hostname': {'simple': '${inputs.Endpoint_hostname}', 'complex': None}, 'ip_list': {'simple': '${inputs.Endpoint_ip}', 'complex': None}}, 'reputationCalc': 0, 'separateContext': True, 'restrictedCompletion': False, 'loop': {'scriptName': '', 'exitCondition': '', 'wait': 1, 'max': 100}, 'view': {'position': {'x': 480, 'y': 195}}, 'note': False, 'evidenceData': {'description': None, 'occurred': None, 'tags': None}, 'skipUnavailable': True, 'quietMode': 0, 'isOverSize': False, 'isAutoSwitchedToQuietMode': False}, '9': {'id': '9', 'taskId': '2604374d-9538-4451-8064-2f5bb5c6dd81', 'type': 'playbook', 'task': {'id': '2604374d-9538-4451-8064-2f5bb5c6dd81', 'version': 2, 'modified': '2021-12-27T07:38:25.309115045Z', 'sortValues': None, 'name': 'Crowdstrike Falcon - Isolate Endpoint', 'description': 'This playbook will auto isolate endpoints by the device ID that was provided in the playbook.', 'playbookName': 'Crowdstrike Falcon - Isolate Endpoint', 'isLocked': False, 'type': 'playbook', 'conditions': None, 'isCommand': False, 'brand': ''}, 'nextTasks': {'#none#': ['2']}, 'scriptArguments': {'Device_id': {'simple': '${inputs.Endpoint_id}', 'complex': None}}, 'reputationCalc': 0, 'separateContext': True, 'restrictedCompletion': False, 'loop': {'scriptName': '', 'exitCondition': '', 'wait': 1, 'max': 100}, 'view': {'position': {'x': 1340, 'y': 195}}, 'note': False, 'evidenceData': {'description': None, 'occurred': None, 'tags': None}, 'skipUnavailable': True, 'quietMode': 0, 'isOverSize': False, 'isAutoSwitchedToQuietMode': False}}, 'taskIds': ['04a17761-3b84-492f-87c6-ef29fc4adc7d', '20f01f93-7b37-4f3f-8c17-a466dac351ef', '050d36dd-0ec3-4490-827e-e210ac5e9a04', '31a268a0-3862-4dcb-8549-b55d0ad936a0', '46562ad2-14ed-4064-8ce8-9adfb791d660', '2604374d-9538-4451-8064-2f5bb5c6dd81', '48226108-0787-44b0-80f6-cf333758b5e8'], 'scriptIds': [], 'commands': [], 'brands': [], 'system': True, 'view': {'linkLabelsPosition': {}, 'paper': {'dimensions': {'height': 385, 'width': 2100, 'x': 50, 'y': 50}}}, 'inputs': [{'key': 'Endpoint_hostname', 'value': {'simple': '', 'complex': None}, 'required': False, 'description': 'The hostname of the endpoint to isolate.', 'playbookInputQuery': None}, {'key': 'ManualHunting.DetectedHosts', 'value': {'simple': '', 'complex': None}, 'required': False, 'description': 'Hosts that were detected as infected during the manual hunting.', 'playbookInputQuery': None}, {'key': 'Endpoint_ip', 'value': {'simple': '', 'complex': None}, 'required': False, 'description': 'The IP of the endpoint to isolate.', 'playbookInputQuery': None}, {'key': 'Endpoint_id', 'value': {'simple': '', 'complex': None}, 'required': False, 'description': 'The ID of the endpoint to isolate.', 'playbookInputQuery': None}], 'outputs': [{'contextPath': 'CbResponse.Sensors.CbSensorID', 'description': 'Carbon Black Response Sensors ids that has been isolated.', 'type': 'string'}, {'contextPath': 'Endpoint', 'description': 'The isolated enpoint.', 'type': 'string'}, {'contextPath': 'Traps.Isolate.EndpointID', 'description': 'The ID of the endpoint.', 'type': 'string'}, {'contextPath': 'Traps.IsolateResult.Status', 'description': 'The status of the isolation operation.', 'type': 'string'}, {'contextPath': 'Cybereason.Machine', 'description': 'Cybereason machine name.', 'type': ''}, {'contextPath': 'Cybereason.IsIsolated', 'description': 'Whether the machine is isolated.', 'type': ''}, {'contextPath': 'Endpoint.Hostname', 'description': 'Hostname of the endpoint.', 'type': ''}, {'contextPath': 'PaloAltoNetworksXDR.Endpoint.endpoint_id', 'description': 'The endpoint ID.', 'type': ''}, {'contextPath': 'PaloAltoNetworksXDR.Endpoint.endpoint_name', 'description': 'The endpoint name.', 'type': ''}, {'contextPath': 'PaloAltoNetworksXDR.Endpoint.endpoint_status', 'description': 'The status of the endpoint.', 'type': ''}, {'contextPath': 'PaloAltoNetworksXDR.Endpoint.ip', 'description': "The endpoint's IP address.", 'type': ''}, {'contextPath': 'PaloAltoNetworksXDR.Endpoint.is_isolated', 'description': 'Whether the endpoint is isolated.', 'type': ''}, {'contextPath': 'CbResponse.Sensors.Status', 'description': 'Sensor status.', 'type': 'unknown'}, {'contextPath': 'CbResponse.Sensors.Isolated', 'description': 'Whether the sensor is isolated.', 'type': 'unknown'}]}
#     demisto_client.generic_request_func
#
#     TestContext.replace_external_playbook_configuration()