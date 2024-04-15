from functools import partial

import pytest
from packaging.version import Version

from demisto_sdk.commands.common.constants import PB_Status
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.test_content.Docker import Docker
from demisto_sdk.commands.test_content.TestContentClasses import (
    Integration,
    TestConfiguration,
    TestContext,
    TestPlaybook,
)
from demisto_sdk.commands.test_content.tests.build_context_test import (
    generate_content_conf_json,
    generate_integration_configuration,
    generate_secret_conf_json,
    generate_test_configuration,
    get_mocked_build_context,
)
from demisto_sdk.commands.test_content.tests.DemistoClientMock import DemistoClientMock
from demisto_sdk.commands.test_content.tests.server_context_test import (
    generate_mocked_server_context,
)


@pytest.fixture
def playbook(mocker):
    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(
            playbook_id="playbook_with_context", integrations=["integration"]
        ),
        default_test_timeout=30,
    )
    pb_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    pb_instance.build_context.logging_module = mocker.MagicMock()
    return pb_instance


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
        generate_test_configuration(
            playbook_id="playbook_runnable_only_on_docker", runnable_on_docker_only=True
        ),
        default_test_timeout=30,
    )
    test_context_builder = partial(
        TestContext,
        build_context=mocker.MagicMock(),
        playbook=TestPlaybook(mocker.MagicMock(), test_playbook_configuration),
        client=mocker.MagicMock(),
    )

    test_context = test_context_builder(
        server_context=mocker.MagicMock(is_instance_using_docker=False)
    )
    assert not test_context._is_runnable_on_current_server_instance()
    test_context = test_context_builder(
        server_context=mocker.MagicMock(is_instance_using_docker=True)
    )
    assert test_context._is_runnable_on_current_server_instance()


# Retries mechanism UT


class RunIncidentTestMock:
    def __init__(self, response_list):
        self.call_count = 0
        self.count_response_list = response_list

    def run_incident_test(self):
        res = self.count_response_list[self.call_count]
        self.call_count += 1
        return res


# Unmockable


def init_server_context(mocker, tmp_path, mockable=False):
    playbook_type = "mocked_playbook" if mockable else "unmocked_playbook"
    playbook_id_type = "mocked_playbook" if mockable else "unmocked_playbook"
    integrations_type = "mocked_integration" if mockable else "unmocked_integration"
    mock_func = "_execute_unmockable_tests" if mockable else "_execute_mockable_tests"
    unmockable_integration = {integrations_type: "reason"} if not mockable else {}

    filtered_tests = [playbook_type]
    tests = [
        generate_test_configuration(
            playbook_id=playbook_id_type, integrations=[integrations_type]
        )
    ]
    integrations_configurations = [
        generate_integration_configuration(integrations_type)
    ]
    secret_test_conf = generate_secret_conf_json(integrations_configurations)
    content_conf_json = generate_content_conf_json(
        tests=tests, unmockable_integrations=unmockable_integration
    )
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        secret_conf_json=secret_test_conf,
        content_conf_json=content_conf_json,
        filtered_tests_content=filtered_tests,
    )
    mocked_demisto_client = DemistoClientMock(integrations=[integrations_type])
    server_context = generate_mocked_server_context(
        build_context, mocked_demisto_client, mocker
    )
    mocker.patch.object(server_context, mock_func, return_value=None)

    return build_context, server_context


def test_unmockable_playbook_passes_on_first_run(mocker, tmp_path):
    """
    Given:
        - An unmockable test
    When:
        - The unmockable test passes on the first run
    Then:
        - Ensure that it exists in the succeeded_playbooks set
        - Ensure that it does not exist in the failed_playbook set
    """
    execution_results = [PB_Status.COMPLETED]
    build_context, server_context = init_server_context(mocker, tmp_path)
    incident_test_mock = RunIncidentTestMock(execution_results)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()
    assert incident_test_mock.call_count == 1
    assert not build_context.tests_data_keeper.failed_playbooks  # empty set
    assert "unmocked_playbook" in build_context.tests_data_keeper.succeeded_playbooks


def test_unmockable_playbook_passes_most_of_the_time(mocker, tmp_path):
    """
    Given:
        - An unmockable test
    When:
        - The unmockable test passes on the second and third run
    Then:
        - Ensure that it exists in the succeeded_playbooks set
        - Ensure that it does not exist in the failed_playbook set
    """
    execution_results = [PB_Status.FAILED, PB_Status.COMPLETED, PB_Status.COMPLETED]
    build_context, server_context = init_server_context(mocker, tmp_path)
    incident_test_mock = RunIncidentTestMock(execution_results)
    logs = build_context.logging_module = mocker.MagicMock()
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    assert incident_test_mock.call_count == 3
    assert not build_context.tests_data_keeper.failed_playbooks
    assert "unmocked_playbook" in build_context.tests_data_keeper.succeeded_playbooks
    assert any(
        "Test-Playbook was executed 3 times, and passed 2 times. Adding to succeeded playbooks."
        in log_item[0][0]
        for log_item in logs.info.call_args_list
    )


def test_unmockable_playbook_fails_every_time(mocker, tmp_path):
    """
    Given:
        - An unmockable test
    When:
        - The unmockable test fails in all the runs
    Then:
        - Ensure that it does not exist in the succeeded_playbooks set
        - Ensure that it exists in the failed_playbook set
    """
    execution_results = [PB_Status.FAILED, PB_Status.FAILED, PB_Status.FAILED]
    build_context, server_context = init_server_context(mocker, tmp_path)
    incident_test_mock = RunIncidentTestMock(execution_results)
    logs = build_context.logging_module = mocker.MagicMock()
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    assert incident_test_mock.call_count == 3
    assert (
        "unmocked_playbook (Mock Disabled)"
        in build_context.tests_data_keeper.failed_playbooks
    )
    assert not build_context.tests_data_keeper.succeeded_playbooks
    assert any(
        "Test-Playbook was executed 3 times, and passed only 0 times. Adding to failed playbooks."
        in log_item[0][0]
        for log_item in logs.info.call_args_list
    )


def test_unmockable_playbook_fails_most_of_the_times(mocker, tmp_path):
    """
    Given:
        - An unmockable test
    When:
        - The unmockable test fails in most of the runs
    Then:
        - Ensure that it does not exist in the succeeded_playbooks set
        - Ensure that it exists in the failed_playbook set
    """
    execution_results = [PB_Status.FAILED, PB_Status.COMPLETED, PB_Status.FAILED]
    build_context, server_context = init_server_context(mocker, tmp_path)
    incident_test_mock = RunIncidentTestMock(execution_results)
    logs = build_context.logging_module = mocker.MagicMock()
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    assert incident_test_mock.call_count == 3
    assert (
        "unmocked_playbook (Mock Disabled)"
        in build_context.tests_data_keeper.failed_playbooks
    )
    assert not build_context.tests_data_keeper.succeeded_playbooks
    assert any(
        "Test-Playbook was executed 3 times, and passed only 1 times. Adding to failed playbooks."
        in [log_item][0][0]
        for log_item in logs.info.call_args_list
    )


# Mockable


def test_mockable_playbook_first_playback_passes(mocker, tmp_path):
    """
    Given:
        - A mockable test
    When:
        - The mockable test passes on the first playback run
    Then:
        - Ensure that it exists in the succeeded_playbooks set
        - Ensure that it does not exist in the failed_playbook set
    """
    execution_results = [PB_Status.COMPLETED]
    build_context, server_context = init_server_context(mocker, tmp_path, mockable=True)
    incident_test_mock = RunIncidentTestMock(execution_results)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    assert incident_test_mock.call_count == 1
    assert "mocked_playbook" in build_context.tests_data_keeper.succeeded_playbooks
    assert not build_context.tests_data_keeper.failed_playbooks


def test_mockable_playbook_second_playback_passes(mocker, tmp_path):
    """
    Given:
        - A mockable test
    When:
        - The mockable test that fails on the first playback but then passes the recording and second playback
    Then:
        - Ensure that it exists in the succeeded_playbooks set
        - Ensure that it does not exist in the failed_playbook set
    """
    execution_results = [PB_Status.FAILED, PB_Status.COMPLETED, PB_Status.COMPLETED]
    build_context, server_context = init_server_context(mocker, tmp_path, mockable=True)
    incident_test_mock = RunIncidentTestMock(execution_results)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    assert incident_test_mock.call_count == 3
    assert "mocked_playbook" in build_context.tests_data_keeper.succeeded_playbooks
    assert not build_context.tests_data_keeper.failed_playbooks


def test_mockable_playbook_recording_passes_most_of_the_time_playback_pass(
    mocker, tmp_path
):
    """
    Given:
        - A mockable test
    When:
        - The mockable test that fails on the first playback, then passes most of the recordings and second playback.
    Then:
        - Ensure that it exists in the succeeded_playbooks set
        - Ensure that it does not exist in the failed_playbook set
    """
    execution_results = [
        PB_Status.FAILED,
        PB_Status.FAILED,
        PB_Status.COMPLETED,
        PB_Status.COMPLETED,
        PB_Status.COMPLETED,
    ]
    build_context, server_context = init_server_context(mocker, tmp_path, mockable=True)
    incident_test_mock = RunIncidentTestMock(execution_results)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    data_keeper = build_context.tests_data_keeper
    assert incident_test_mock.call_count == 5
    assert "mocked_playbook" in data_keeper.succeeded_playbooks
    assert not data_keeper.failed_playbooks


def test_mockable_playbook_recording_passes_most_of_the_time_playback_fails(
    mocker, tmp_path
):
    """
    Given:
        - A mockable test
    When:
        - The mockable test that fails on the first playback, then passes most of the recordings but the second playback fails.
    Then:
        - Ensure that it does not exist in the succeeded_playbooks set
        - Ensure that it exists in the failed_playbook set
    """
    execution_results = [
        PB_Status.FAILED,
        PB_Status.FAILED,
        PB_Status.COMPLETED,
        PB_Status.COMPLETED,
        PB_Status.FAILED,
    ]
    build_context, server_context = init_server_context(mocker, tmp_path, mockable=True)
    incident_test_mock = RunIncidentTestMock(execution_results)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    data_keeper = build_context.tests_data_keeper
    assert incident_test_mock.call_count == 5
    assert not data_keeper.succeeded_playbooks
    assert "mocked_playbook (Second Playback)" in data_keeper.failed_playbooks
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_executions"] == 3
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_successful_runs"]
        == 2
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["failed_stage"]
        == "Second playback"
    )


def test_mockable_playbook_recording_fails_most_of_the_time(mocker, tmp_path):
    """
    Given:
        - A mockable test
    When:
        - The mockable test that fails on the first playback, then fails most of the recordings.
    Then:
        - Ensure that it does not exist in the succeeded_playbooks set
        - Ensure that it exists in the failed_playbook set
        - no second playback is needed
    """
    execution_results = [
        PB_Status.FAILED,
        PB_Status.FAILED,
        PB_Status.COMPLETED,
        PB_Status.FAILED,
    ]
    incident_test_mock = RunIncidentTestMock(execution_results)
    build_context, server_context = init_server_context(mocker, tmp_path, mockable=True)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    data_keeper = build_context.tests_data_keeper
    assert incident_test_mock.call_count == 4
    assert not data_keeper.succeeded_playbooks
    assert "mocked_playbook" in data_keeper.failed_playbooks
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_executions"] == 3
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_successful_runs"]
        == 1
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["failed_stage"] == "Execution"
    )


def test_mockable_playbook_recording_fails_every_time(mocker, tmp_path):
    """
    Given:
        - A mockable test
    When:
        - The mockable test that fails on the first playback, then fails on every record run.
    Then:
        - Ensure that it does not exist in the succeeded_playbooks set
        - Ensure that it exists in the failed_playbook set
        - no second playback is needed
    """
    execution_results = [
        PB_Status.FAILED,
        PB_Status.FAILED,
        PB_Status.FAILED,
        PB_Status.FAILED,
    ]
    incident_test_mock = RunIncidentTestMock(execution_results)
    build_context, server_context = init_server_context(mocker, tmp_path, mockable=True)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    data_keeper = build_context.tests_data_keeper
    assert incident_test_mock.call_count == 4
    assert not data_keeper.succeeded_playbooks
    assert "mocked_playbook" in data_keeper.failed_playbooks
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_executions"] == 3
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_successful_runs"]
        == 0
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["failed_stage"] == "Execution"
    )


def test_mockable_playbook_second_playback_fails(mocker, tmp_path):
    """
    Given:
        - A mockable test
    When:
        - The mockable test fails on the second playback
    Then:
        - Ensure that it exists in the failed_playbooks set
        - Ensure that it does not exist in the succeeded_playbooks list
    """

    execution_results = [PB_Status.FAILED, PB_Status.COMPLETED, PB_Status.FAILED]
    incident_test_mock = RunIncidentTestMock(execution_results)
    build_context, server_context = init_server_context(mocker, tmp_path, mockable=True)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_incident_test",
        incident_test_mock.run_incident_test,
    )
    server_context.execute_tests()

    data_keeper = build_context.tests_data_keeper
    assert incident_test_mock.call_count == 3
    assert not data_keeper.succeeded_playbooks
    assert "mocked_playbook (Second Playback)" in data_keeper.failed_playbooks
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_executions"] == 1
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["number_of_successful_runs"]
        == 1
    )
    assert (
        data_keeper.playbook_report["mocked_playbook"][0]["failed_stage"]
        == "Second playback"
    )


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
        generate_test_configuration(
            playbook_id="playbook_runnable_only_on_docker", integrations=["integration"]
        ),
        default_test_timeout=30,
    )
    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    playbook_instance.integrations[0].integration_type = Docker.PYTHON_INTEGRATION_TYPE
    test_context = TestContext(
        build_context=mocker.MagicMock(),
        playbook=playbook_instance,
        client=mocker.MagicMock(),
        server_context=mocker.MagicMock(),
    )
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
        generate_test_configuration(
            playbook_id="playbook_runnable_only_on_docker", integrations=["integration"]
        ),
        default_test_timeout=30,
    )
    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    playbook_instance.integrations[
        0
    ].integration_type = Docker.POWERSHELL_INTEGRATION_TYPE
    test_context = TestContext(
        build_context=mocker.MagicMock(),
        playbook=playbook_instance,
        client=mocker.MagicMock(),
        server_context=mocker.MagicMock(),
    )
    memory_threshold, pid_threshold = test_context.get_threshold_values()
    assert memory_threshold == Docker.DEFAULT_PWSH_CONTAINER_MEMORY_USAGE
    assert pid_threshold == Docker.DEFAULT_PWSH_CONTAINER_PIDS_USAGE


class TestPrintContextToLog:
    @staticmethod
    def create_playbook_instance(mocker):
        test_playbook_configuration = TestConfiguration(
            generate_test_configuration(
                playbook_id="playbook_with_context", integrations=["integration"]
            ),
            default_test_timeout=30,
        )
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
        dt_result = {"foo": "goo"}
        expected_result = json.dumps(dt_result, indent=4)
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = (dt_result, 200, {})
        playbook_instance.print_context_to_log(client, incident_id="1")
        assert (
            playbook_instance.build_context.logging_module.info.call_args[0][0]
            == expected_result
        )

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
        expected_dt = "{}"
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = ({}, 200, {})
        playbook_instance.print_context_to_log(client, incident_id="1")
        assert (
            playbook_instance.build_context.logging_module.info.call_args[0][0]
            == expected_dt
        )

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
        expected_dt = {
            None
        }  # Set isn't serializable, thus causing an exception, which is expected.
        expected_error = "unable to parse result for result with value: {None}"
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = (expected_dt, 200, {})
        playbook_instance.print_context_to_log(client, incident_id="1")
        assert (
            playbook_instance.build_context.logging_module.error.call_args[0][0]
            == expected_error
        )

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
        expected_dt = "No Permission"
        expected_error = f"incident context fetch failed - response:'{expected_dt}', status code:403 headers:{{}}"
        playbook_instance = self.create_playbook_instance(mocker)
        client = mocker.MagicMock()
        client.api_client.call_api.return_value = (expected_dt, 403, {})
        playbook_instance.print_context_to_log(client, incident_id="1")
        assert (
            playbook_instance.build_context.logging_module.error.call_args_list[0][0][0]
            == expected_error
        )


def test_replacing_placeholders(mocker, playbook, tmp_path):
    """
    Given:
        - Integration with placeholders, different servers
    When:
        - Calling _set_integration_params during creating integrations configurations
    Then:
        - Ensure that replacing placeholders happens not in place,
        and next integration with same build_context, will be able to replace '%%SERVER_HOST%%' placeholder.
    """
    # Setting up the build context
    filtered_tests = ["playbook_integration", "playbook_second_integration"]
    # Setting up the content conf.json
    tests = [
        generate_test_configuration(
            playbook_id="playbook_integration",
            integrations=["integration_with_placeholders"],
        ),
        generate_test_configuration(
            playbook_id="playbook_second_integration",
            integrations=["integration_with_placeholders"],
        ),
    ]
    content_conf_json = generate_content_conf_json(
        tests=tests,
        unmockable_integrations={"FirstIntegration": "reason"},
        skipped_tests={},
    )
    # Setting up the content-test-conf conf.json
    integration_names = ["integration_with_placeholders"]
    integrations_configurations = [
        generate_integration_configuration(
            name=integration_name, params={"url": "%%SERVER_HOST%%/server"}
        )
        for integration_name in integration_names
    ]
    secret_test_conf = generate_secret_conf_json(integrations_configurations)

    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(
            playbook_id="playbook_runnable_only_on_docker", integrations=["integration"]
        ),
        default_test_timeout=30,
    )
    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    playbook_instance.integrations[0].integration_type = Docker.PYTHON_INTEGRATION_TYPE

    # Setting up the build_context instance
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        secret_conf_json=secret_test_conf,
        filtered_tests_content=filtered_tests,
    )

    integration = Integration(
        build_context, "integration_with_placeholders", ["instance"], playbook
    )
    integration._set_integration_params(
        server_url="1.1.1.1", playbook_id="playbook_integration", is_mockable=False
    )
    integration = Integration(
        build_context, "integration_with_placeholders", ["instance"], playbook
    )
    integration._set_integration_params(
        server_url="1.2.3.4", playbook_id="playbook_integration", is_mockable=False
    )
    assert "%%SERVER_HOST%%" in build_context.secret_conf.integrations[0].params.get(
        "url"
    )


CASES = [
    (  # case one input is found
        {
            "id": "pb_test",
            "inputs": [
                {
                    "key": "Endpoint_hostname",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The hostname of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "ManualHunting.DetectedHosts",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "Hosts that were detected as infected during the manual hunting.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_ip",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The IP of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_id",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The ID of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
            ],
        },
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostname": {"simple": "test"},
            },
        },
        [
            {
                "key": "Endpoint_hostname",
                "value": {"simple": "test", "complex": None},
                "required": False,
                "description": "The hostname of the endpoint to isolate.",
                "playbookInputQuery": None,
            },
            {
                "key": "ManualHunting.DetectedHosts",
                "value": {"simple": "", "complex": None},
                "required": False,
                "description": "Hosts that were detected as infected during the manual hunting.",
                "playbookInputQuery": None,
            },
            {
                "key": "Endpoint_ip",
                "value": {"simple": "", "complex": None},
                "required": False,
                "description": "The IP of the endpoint to isolate.",
                "playbookInputQuery": None,
            },
            {
                "key": "Endpoint_id",
                "value": {"simple": "", "complex": None},
                "required": False,
                "description": "The ID of the endpoint to isolate.",
                "playbookInputQuery": None,
            },
        ],
    ),
]


@pytest.mark.parametrize("current, new_configuration, expected", CASES)
def test_replacing_pb_inputs(mocker, current, new_configuration, expected):
    """

    Given: Configuration with inputs to change
            Found configuration but running on older versions of server.
    When: Using the external configuration in conf.json in order to change playbook inputs on testing flow in build
    Then: Make sure the server request are correct

    """
    from demisto_client.demisto_api import DefaultApi

    from demisto_sdk.commands.test_content.TestContentClasses import (
        demisto_client,
    )

    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(
            playbook_id="playbook_runnable_only_on_docker", integrations=["integration"]
        ),
        default_test_timeout=30,
    )
    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    playbook_instance.integrations[0].integration_type = Docker.PYTHON_INTEGRATION_TYPE

    class clientMock(DefaultApi):
        ...

    test_context = TestContext(
        build_context=mocker.MagicMock(),
        playbook=playbook_instance,
        client=clientMock(),
        server_context=mocker.MagicMock(),
    )

    def generic_request_func(self, path, method, body=None, **kwargs):
        if path == "/playbook/inputs/pb_test" and method == "POST":
            assert body == expected
        elif path == "/playbook/pb_test" and method == "GET":
            return current, None, None
        else:
            assert False  # Unexpected path

    mocker.patch.object(
        demisto_client, "generic_request_func", side_effect=generic_request_func
    )
    test_context.replace_external_playbook_configuration(
        new_configuration, Version("6.5.0")
    )


BAD_CASES = [
    (  # case no configuration found
        {
            "id": "pb_test",
            "inputs": [
                {
                    "key": "Endpoint_hostname",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The hostname of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "ManualHunting.DetectedHosts",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "Hosts that were detected as infected during the manual hunting.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_ip",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The IP of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_id",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The ID of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
            ],
        },
        {},
        "6.5.0",
        "External Playbook Configuration not provided, skipping re-configuration.",
    ),
    (  # case configuration found in older version
        {
            "id": "pb_test",
            "inputs": [
                {
                    "key": "Endpoint_hostname",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The hostname of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "ManualHunting.DetectedHosts",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "Hosts that were detected as infected during the manual hunting.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_ip",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The IP of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_id",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The ID of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
            ],
        },
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostname": {"simple": "test"},
            },
        },
        "6.0.0",
        "External Playbook not supported in versions previous to 6.2.0, skipping re-configuration.",
    ),
]


@pytest.mark.parametrize(
    "current, new_configuration, version, expected_error", BAD_CASES
)
def test_replacing_pb_inputs_fails_with_build_pass(
    mocker, current, new_configuration, version, expected_error
):
    """

    Given: Missing configuration
            Found configuration but running on older versions of server.
    When: Using the external configuration in conf.json in order to change playbook inputs on testing flow in build
    Then: Make sure the build pass without errors

    """
    from demisto_client.demisto_api import DefaultApi

    from demisto_sdk.commands.test_content.TestContentClasses import (
        demisto_client,
    )

    class ClientMock(DefaultApi):
        ...

    def generic_request_func(self, path, method, body=None, **kwargs):
        if path == "/playbook/inputs/pb_test" and method == "POST":
            return
        elif path == "/playbook/pb_test" and method == "GET":
            return current, None, None
        else:
            assert False  # Unexpected path

    mocker.patch.object(
        demisto_client, "generic_request_func", side_effect=generic_request_func
    )

    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(
            playbook_id="playbook_runnable_only_on_docker", runnable_on_docker_only=True
        ),
        default_test_timeout=30,
    )

    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)

    test_context = TestContext(
        build_context=mocker.MagicMock(),
        playbook=playbook_instance,
        client=ClientMock(),
        server_context=mocker.MagicMock(),
    )

    test_context.replace_external_playbook_configuration(
        new_configuration, Version(version)
    )


BAD_CASES_BUILD_FAIL = [
    (  # case configuration not found.
        {
            "id": "createPlaybookErr",
            "status": 400,
            "title": "Could not create playbook",
            "detail": "Could not create playbook",
            "error": "Item not found (8)",
            "encrypted": None,
            "multires": None,
        },
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostname": {"simple": "test"},
            },
        },
        "6.2.0",
        "External Playbook pb_test was not found or has no inputs.",
    ),
    (  # case configuration was found but wrong input key given.
        {
            "id": "pb_test",
            "inputs": [
                {
                    "key": "Endpoint_hostname",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The hostname of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "ManualHunting.DetectedHosts",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "Hosts that were detected as infected during the manual hunting.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_ip",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The IP of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
                {
                    "key": "Endpoint_id",
                    "value": {"simple": "", "complex": None},
                    "required": False,
                    "description": "The ID of the endpoint to isolate.",
                    "playbookInputQuery": None,
                },
            ],
        },
        {
            "playbookID": "pb_test",
            "input_parameters": {
                "Endpoint_hostnames": {"simple": "test"},
            },
        },
        "6.2.0",
        "Some input keys was not found in playbook pb_test: Endpoint_hostnames.",
    ),
]


@pytest.mark.parametrize(
    "current, new_configuration, version, expected_error", BAD_CASES_BUILD_FAIL
)
def test_replacing_pb_inputs_fails_with_build_fail(
    mocker, current, new_configuration, version, expected_error
):
    """

    Given: Bad configuration - external playbooks is wrong
            Bad configuration - wrong input names
    When: Using the external configuration in conf.json in order to change playbook inputs on testing flow in build
    Then: Make sure the error contains the relevant issue.

    """
    from demisto_client.demisto_api import DefaultApi

    from demisto_sdk.commands.test_content.TestContentClasses import (
        demisto_client,
    )

    class clientMock(DefaultApi):
        ...

    def generic_request_func(self, path, method, body=None, **kwargs):
        if path == "/playbook/inputs/pb_test" and method == "POST":
            return
        elif path == "/playbook/pb_test" and method == "GET":
            return current, None, None
        else:
            assert False  # Unexpected path

    mocker.patch.object(
        demisto_client, "generic_request_func", side_effect=generic_request_func
    )

    test_playbook_configuration = TestConfiguration(
        generate_test_configuration(
            playbook_id="playbook_runnable_only_on_docker", runnable_on_docker_only=True
        ),
        default_test_timeout=30,
    )
    playbook_instance = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)

    test_context = TestContext(
        build_context=mocker.MagicMock(),
        playbook=playbook_instance,
        client=clientMock(),
        server_context=mocker.MagicMock(),
    )
    with pytest.raises(Exception) as e:
        test_context.replace_external_playbook_configuration(
            new_configuration, Version(version)
        )
    assert expected_error in str(e)
