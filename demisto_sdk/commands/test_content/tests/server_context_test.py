from demisto_sdk.commands.test_content.mock_server import MITMProxy
from demisto_sdk.commands.test_content.TestContentClasses import (
    BuildContext,
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
        - A ServerContext instance that should execute three tests:
            1) A test with no integrations
            2) A test with mockable integration
            3) A test with unmockable integration

    When:
        - Running execute_tests.

    Then:
        - Ensure the server context has executed all the tests
        - Ensure the mockable and unmockable tests queues were emptied
        - Ensure no test has failed during that test
    """
    # Setting up the build context
    filtered_tests = [
        "playbook_without_integrations",
        "playbook_with_mockable_integration",
        "playbook_with_unmockable_integration",
        "skipped_playbook",
    ]
    # Setting up the content conf.json
    tests = [
        generate_test_configuration(playbook_id="playbook_without_integrations"),
        generate_test_configuration(
            playbook_id="playbook_with_mockable_integration",
            integrations=["mockable_integration"],
        ),
        generate_test_configuration(
            playbook_id="playbook_with_unmockable_integration",
            integrations=["unmockable_integration"],
        ),
        generate_test_configuration(playbook_id="skipped_playbook"),
    ]
    content_conf_json = generate_content_conf_json(
        tests=tests,
        unmockable_integrations={"unmockable_integration": "reason"},
        skipped_tests={"skipped_playbook": "reason"},
    )
    # Setting up the content-test-conf conf.json
    integration_names = ["mockable_integration", "unmockable_integration"]
    integrations_configurations = [
        generate_integration_configuration(integration_name)
        for integration_name in integration_names
    ]
    secret_test_conf = generate_secret_conf_json(integrations_configurations)

    # Setting up the build_context instance
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        secret_conf_json=secret_test_conf,
        filtered_tests_content=filtered_tests,
    )
    # Setting up the client
    mocked_demisto_client = DemistoClientMock(integrations=integration_names)
    server_context = generate_mocked_server_context(
        build_context, mocked_demisto_client, mocker
    )
    server_context.execute_tests()

    # Validating all tests were executed
    for test in set(filtered_tests) - {"skipped_playbook"}:
        assert test in server_context.executed_tests

    # Validating all queues were emptied
    assert build_context.mockable_tests_to_run.all_tasks_done
    assert build_context.unmockable_tests_to_run.all_tasks_done

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
        "demisto_sdk.commands.test_content.mock_server.run_with_mock"
    ).return_value.__enter__.return_value = {}
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
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.TestContext._notify_failed_test"
    )
    mocker.patch.object(MITMProxy, "__init__", lambda *args, **kwargs: None)
    mocker.patch("time.sleep")
    # Executing the test
    server_context = ServerContext(build_context, "1.1.1.1")
    server_context.proxy = mocker.MagicMock()
    return server_context
