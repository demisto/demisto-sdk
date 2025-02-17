from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS
from demisto_sdk.commands.test_content.TestContentClasses import (
    BuildContext,
    OnPremServerContext,
    ServerContext,
)
from demisto_sdk.commands.test_content.tests.build_context_test import (
    generate_content_conf_json,
    generate_integration_configuration,
    generate_secret_conf_json,
    generate_test_configuration,
    get_mocked_build_context,
)
from demisto_sdk.commands.test_content.tests.DemistoClientMock import DemistoClientMock


def test_execute_tests(mocker, tmp_path):
    """
    Given:
        - A ServerContext instance that should execute two tests:
            1) A test with no integrations
            2) A test with integration

    When:
        - Running execute_tests.

    Then:
        - Ensure the server context has executed all the tests
        - Ensure the test queues were emptied
        - Ensure no test has failed during that test
    """

    # Setting up the build context
    filtered_tests = [
        "playbook_without_integrations",
        "playbook_with_integration",
        "skipped_playbook",
    ]

    machine_assignment_content = {
        "xsoar-machine": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: filtered_tests},
        }
    }
    # Setting up the content conf.json
    tests = [
        generate_test_configuration(playbook_id="playbook_without_integrations"),
        generate_test_configuration(
            playbook_id="playbook_with_integration",
            integrations=["integration"],
        ),
        generate_test_configuration(playbook_id="skipped_playbook"),
    ]
    content_conf_json = generate_content_conf_json(
        tests=tests,
        skipped_tests={"skipped_playbook": "reason"},
    )
    # Setting up the content-test-conf conf.json
    integration_names = ["integration"]
    integrations_configurations = [
        generate_integration_configuration(integration_name)
        for integration_name in integration_names
    ]
    secret_test_conf = generate_secret_conf_json(integrations_configurations)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.BuildContext.create_servers",
        return_value=set(),
    )

    # Setting up the build_context instance
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        secret_conf_json=secret_test_conf,
        machine_assignment_content=machine_assignment_content,
    )
    # Setting up the client
    mocked_demisto_client = DemistoClientMock(integrations=integration_names)
    server_context = generate_mocked_server_context(
        build_context, mocked_demisto_client, mocker
    )
    build_context.servers = {server_context}
    server_context.execute_tests()

    # Validating all tests were executed
    for test in set(filtered_tests) - {"skipped_playbook"}:
        assert test in server_context.executed_tests

    # Validating all queues were emptied
    assert next(iter(build_context.servers)).tests_to_run.all_tasks_done

    # Validating no failed playbooks
    assert not build_context.tests_data_keeper.failed_playbooks

    # Validating skipped test
    assert "skipped_playbook" not in server_context.executed_tests
    assert "skipped_playbook" in build_context.tests_data_keeper.skipped_tests


def generate_mocked_server_context(
    build_context: BuildContext, mocked_demisto_client: DemistoClientMock, mocker
) -> ServerContext:
    """
    Creates a ServerContext with the requested build context and mocked client.
    Args:
        build_context: The build context in which the server context should be created
        mocked_demisto_client: The mocked client with which the Server context will generate requests
        mocker: Mocker object

    Returns:
        A ServerContext instance
    """
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.demisto_client",
        mocked_demisto_client,
    )
    # Mocking unnecessary calls
    mocker.patch(
        "demisto_sdk.commands.test_content.IntegrationsLock.safe_lock_integrations",
        return_value=True,
    )
    mocker.patch(
        "demisto_sdk.commands.test_content.IntegrationsLock.safe_unlock_integrations"
    )
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_docker_threshold_test"
    )
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )

    mocker.patch("time.sleep")
    # Executing the test
    server_context = OnPremServerContext(build_context, "1.1.1.1")
    server_context.proxy = mocker.MagicMock()
    return server_context
