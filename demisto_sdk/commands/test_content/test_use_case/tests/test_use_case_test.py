import pytest
from junitparser import TestSuite
from pytest import ExitCode

import demisto_sdk.commands.test_content.test_use_case.test_use_case as test_use_case
from demisto_sdk.commands.test_content.test_use_case.test_use_case import (
    run_test_use_case_pytest,
)


# Mock the dependencies
@pytest.fixture
def mocker_cloud_client(mocker):
    # Mock the XsoarClient
    cloud_client = mocker.Mock()
    cloud_client.server_config.base_api_url = "https://example.com"
    cloud_client.server_config.api_key.get_secret_value.return_value = "API_KEY"
    cloud_client.server_config.auth_id = "AUTH_ID"
    return cloud_client


@pytest.fixture
def mocker_test_use_case_directory(mocker):
    # Mock the test_use_case_directory
    return mocker.Mock()


def test_run_test_use_case_pytest(
    mocker, mocker_cloud_client, mocker_test_use_case_directory
):
    """
    Given: parameters for running the tests.
    When: running the test_use_case command.
    Then: validate the correct params are used when running the pytest method.
    """
    test_result_mocker = mocker.Mock()
    mocker.patch.object(test_use_case, "get_pack_name", return_value="/path/to/pack")
    mocker.patch.object(test_use_case, "copy_conftest")
    mocker.patch.object(test_use_case, "logger")
    mocker.patch.object(
        test_use_case, "TestResultCapture", return_value=test_result_mocker
    )
    mocker.patch("pytest.main", return_value=ExitCode.OK)

    # Call the function to be tested
    result, test_use_case_suite = run_test_use_case_pytest(
        mocker_test_use_case_directory, mocker_cloud_client, durations=5
    )

    # Verify the expected behavior and assertions
    assert result is True
    assert isinstance(test_use_case_suite, TestSuite)

    # Additional assertions for the mocked dependencies
    pytest.main.assert_called_once_with(
        [
            "--client_conf=base_url=https://example.com,"
            "api_key=API_KEY,"
            "auth_id=AUTH_ID,"
            "project_id=None",
            str(mocker_test_use_case_directory),
            "--durations=5",
            "--log-cli-level=CRITICAL",
        ],
        plugins=[test_result_mocker],
    )
    mocker_cloud_client.server_config.api_key.get_secret_value.assert_called_once()


def test_pytest_runtest_logreport_passed(mocker):
    """
    When: pytest_runtest_logreport is called with a passing test,
    Given: a TestResultCapture instance and a passing report,
    Then: Validate the correct testcase is appended the test suite.


    """
    junit_testsuite = TestSuite("Test Suite")
    test_result_capture = test_use_case.TestResultCapture(junit_testsuite)

    report = mocker.Mock()
    report.when = "call"
    report.nodeid = "test_module.test_function"
    report.location = ("test_module",)
    report.duration = 0.5
    report.outcome = "passed"

    test_result_capture.pytest_runtest_logreport(report)

    assert len(junit_testsuite) == 1

    for testcase in junit_testsuite:
        assert testcase.name == "test_module.test_function"
        assert testcase.classname == "test_module"
        assert testcase.time == 0.5
        assert len(testcase.result) == 0


def test_pytest_runtest_logreport_failed(mocker):
    """
    When: pytest_runtest_logreport is called with a failing test,
    Given: a TestResultCapture instance and a failing report,
    Then: Validate the correct testcase is appended the test suite.
    """
    junit_testsuite = TestSuite("Test Suite")
    test_result_capture = test_use_case.TestResultCapture(junit_testsuite)

    report = mocker.Mock()
    report.when = "call"
    report.nodeid = "test_module.test_function"
    report.location = ("test_module",)
    report.duration = 0.5
    report.outcome = "failed"
    report.longreprtext = "AssertionError: Expected 1, but got 2"

    test_result_capture.pytest_runtest_logreport(report)

    assert len(junit_testsuite) == 1

    for testcase in junit_testsuite:
        assert testcase.name == "test_module.test_function"
        assert testcase.classname == "test_module"
        assert testcase.time == 0.5
        assert testcase.result[0].message == "AssertionError: Expected 1, but got 2"


def test_pytest_runtest_logreport_skipped(mocker):
    """
    When: pytest_runtest_logreport is called with a skipped test,
    Given: a TestResultCapture instance and a skipped report,
    Then: Validate the correct testcase is appended the test suite.
    """
    junit_testsuite = TestSuite("Test Suite")
    test_result_capture = test_use_case.TestResultCapture(junit_testsuite)

    report = mocker.Mock()
    report.when = "call"
    report.nodeid = "test_module.test_function"
    report.location = ("test_module",)
    report.duration = 0.5
    report.outcome = "skipped"

    test_result_capture.pytest_runtest_logreport(report)

    assert len(junit_testsuite) == 1

    for testcase in junit_testsuite:
        assert testcase.name == "test_module.test_function"
        assert testcase.classname == "test_module"
        assert testcase.time == 0.5
        assert testcase.result[0].message == "Test skipped"
