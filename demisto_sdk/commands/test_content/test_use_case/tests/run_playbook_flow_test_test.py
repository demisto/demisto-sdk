import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path


# Mock dependencies
class TestSuite:
    def __init__(self, name):
        self.name = name
        self.properties = {}

    def add_property(self, key, value):
        self.properties[key] = value


class XsiamApiClient:
    def __init__(self, base_url, api_key, auth_id):
        self.base_url = base_url
        self.api_key = api_key
        self.auth_id = auth_id


class TestResultCapture:
    def __init__(self, test_suite):
        self.test_suite = test_suite


# Unit test class
class TestRunPlaybookFlowTestPytest(unittest.TestCase):

    @patch("pytest.main")
    @patch("__main__.TestResultCapture")
    def test_run_playbook_flow_test_pytest_success(self, mock_result_capture, mock_pytest_main):
        from demisto_sdk.commands.test_content.test_use_case.test_use_case import \
            run_test_use_case_pytest

        # Arrange
        playbook_flow_test_directory = Path("/path/to/test")
        xsiam_client = XsiamApiClient("http://example.com", "api_key", "auth_id")
        mock_pytest_main.return_value = 0
        mock_result_capture.return_value = MagicMock()

        # Act
        success, test_suite = run_test_use_case_pytest(
            playbook_flow_test_directory, xsiam_client, durations=5
        )

        # Assert
        self.assertTrue(success)
        self.assertIsInstance(test_suite, TestSuite)
        self.assertEqual(test_suite.properties["file_name"], str(playbook_flow_test_directory))

    @patch("pytest.main")
    @patch("__main__.TestResultCapture")
    def test_run_playbook_flow_test_pytest_failure(self, mock_result_capture, mock_pytest_main):
        # Arrange
        playbook_flow_test_directory = Path("/path/to/test")
        xsiam_client = XsiamApiClient("http://example.com", "api_key", "auth_id")
        mock_pytest_main.return_value = 1
        mock_result_capture.return_value = MagicMock()

        # Act
        success, test_suite = run_playbook_flow_test_pytest(
            playbook_flow_test_directory, xsiam_client, durations=5
        )

        # Assert
        self.assertFalse(success)
        self.assertIsInstance(test_suite, TestSuite)
        self.assertEqual(test_suite.properties["file_name"], str(playbook_flow_test_directory))
