import sys

import pytest
from demisto_sdk.commands.test_content.mock_server import MITMProxy
from demisto_sdk.commands.test_content.TestContentClasses import ServerContext
from demisto_sdk.commands.test_content.tests.BuildContext_test import (
    generate_content_conf_json, generate_integration_configuration,
    generate_secret_conf_json, generate_test_configuration,
    get_mocked_build_context)
from demisto_sdk.commands.test_content.tests.DemistoClientMock_test import \
    DemistoClientMock


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
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor == 7:
        pytest.skip('The mock required for this test is supported only in python 3.8+')

    # Setting up the build context
    filtered_tests = ['playbook_without_integrations',
                      'playbook_with_mockable_integration',
                      'playbook_with_unmockable_integration']
    tests = [generate_test_configuration(playbook_id='playbook_without_integrations'),
             generate_test_configuration(playbook_id='playbook_with_mockable_integration',
                                         integrations=['mockable_integration']),
             generate_test_configuration(playbook_id='playbook_with_unmockable_integration',
                                         integrations=['unmockable_integration'])]
    content_conf_json = generate_content_conf_json(tests=tests,
                                                   unmockable_integrations={'unmockable_integration': 'reason'})
    integrations = [generate_integration_configuration('mockable_integration'),
                    generate_integration_configuration('unmockable_integration')]
    secret_test_conf = generate_secret_conf_json(integrations)
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             secret_conf_json=secret_test_conf,
                                             filtered_tests_content=filtered_tests)
    # Setting up the client
    mocker.patch('demisto_client.configure', return_value=DemistoClientMock)
    mocker.patch('demisto_client.generic_request_func', side_effect=DemistoClientMock.generic_request_func)
    DemistoClientMock.add_integration_configuration('mockable_integration')
    DemistoClientMock.add_integration_configuration('unmockable_integration')
    # Mocking unnecessary calls
    mocker.patch('demisto_sdk.commands.test_content.mock_server.run_with_mock').return_value.__enter__.return_value = {}
    mocker.patch('demisto_sdk.commands.test_content.IntegrationsLock.safe_lock_integrations', return_value=True)
    mocker.patch('demisto_sdk.commands.test_content.IntegrationsLock.safe_unlock_integrations')
    mocker.patch('demisto_sdk.commands.test_content.TestContentClasses.TestContext._run_docker_threshold_test')
    mocker.patch.object(MITMProxy, '__init__', lambda *args, **kwargs: None)
    mocker.patch('time.sleep')

    # Executing the test
    server_context = ServerContext(build_context, '1.1.1.1')
    server_context.proxy = mocker.MagicMock()
    server_context.execute_tests()

    # Validating all tests were executed
    for test in filtered_tests:
        assert test in server_context.executed_tests
    assert build_context.mockable_tests_to_run.all_tasks_done
    assert build_context.unmockable_tests_to_run.all_tasks_done
    assert not build_context.tests_data_keeper.failed_playbooks
