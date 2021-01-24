from functools import partial

from demisto_sdk.commands.test_content.TestContentClasses import (
    TestConfiguration, TestContext, TestPlaybook)
from demisto_sdk.commands.test_content.tests.build_context_test import \
    generate_test_configuration


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

    test_context = test_context_builder(is_instance_using_docker=False)
    assert not test_context._is_runnable_on_current_server_instance()
    test_context = test_context_builder(is_instance_using_docker=True)
    assert test_context._is_runnable_on_current_server_instance()
