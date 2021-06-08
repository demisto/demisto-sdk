from functools import partial

from demisto_sdk.commands.common.constants import PB_Status
from demisto_sdk.commands.test_content.Docker import Docker
from demisto_sdk.commands.test_content.TestContentClasses import (
    TestConfiguration, TestContext, TestPlaybook)
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
