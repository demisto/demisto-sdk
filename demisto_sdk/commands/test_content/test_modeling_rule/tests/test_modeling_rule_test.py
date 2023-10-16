import logging
import os
from pathlib import Path
from uuid import UUID

import junitparser
import pytest
import requests_mock
import typer
from freezegun import freeze_time
from typer.testing import CliRunner

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.test_content.xsiam_tools.test_data import Validations
from TestSuite.test_tools import str_in_call_args_list

logger = logging.getLogger("demisto-sdk")

ONE_MODEL_RULE_TEXT = """
[MODEL: dataset=fake_fakerson_raw]
alter
    xdm.session_context_id = externalId,
    xdm.observer.action = act,
    xdm.event.outcome = outcome,
    xdm.event.outcome_reason = reason,
    xdm.network.http.method = requestMethod,
    xdm.network.http.url = request,
    xdm.source.host.hostname = devicehostname,
    xdm.source.host.ipv4_addresses = arraycreate(coalesce(src, "")),
    xdm.target.host.ipv4_addresses = arraycreate(coalesce(dst, "")),
    xdm.network.application_protocol_category = cat,
    xdm.network.protocol_layers = arraycreate(coalesce(app, "")),
    xdm.source.user.username = suser,
    xdm.source.zone = spriv,
    xdm.network.http.domain = dhost,
    xdm.network.http.response_code = outcome,
    xdm.target.sent_bytes = to_integer(out),
    xdm.network.http.url_category = cs2,
    xdm.network.http.content_type = contenttype,
    xdm.alert.category = cs4,
    xdm.alert.name = cs5,
    xdm.alert.severity = to_string(cn1),
    xdm.observer.name = _reporting_device_name,
    xdm.source.user_agent = requestClientApplication,
    xdm.target.interface = destinationServiceName,
    xdm.source.ipv4 = sourceTranslatedAddress,
    xdm.event.type = FakeFakersonURLClass,
    xdm.observer.product = _product,
    xdm.observer.vendor = _vendor,
    xdm.target.process.executable.file_type = fileType;
"""
DEFAULT_MODELING_RULE_NAME = "TestModelingRule"
DEFAULT_MODELING_RULE_NAME_2 = "TestModelingRule2"
DEFAULT_TEST_EVENT_ID = UUID("00000000-0000-0000-0000-000000000000")
DEFAULT_TEST_EVENT_ID_2 = UUID("11111111-1111-1111-1111-111111111111")


class ModelingRuleMock:
    path = Path(CONTENT_PATH)

    def normalize_file_name(self):
        return "test_modeling_rule.yml"


class SetFakeXsiamClientEnvironmentVars:
    def __init__(
        self,
        demisto_base_url: str = "https://api-fake.com",
        demisto_api_key: str = "fake-api-key",
        xsiam_auth_id: str = "fake-auth-id",
        xsiam_token: str = "fake-token",
        collector_token: str = "fake-collector-token",
    ):
        self.og_demisto_base_url = os.getenv("DEMISTO_BASE_URL")
        self.og_demisto_api_key = os.getenv("DEMISTO_API_KEY")
        self.og_xsiam_auth_id = os.getenv("XSIAM_AUTH_ID")
        self.og_xsiam_token = os.getenv("XSIAM_TOKEN")
        self.og_collector_token = os.getenv("COLLECTOR_TOKEN")
        self.demisto_base_url = demisto_base_url
        self.demisto_api_key = demisto_api_key
        self.xsiam_auth_id = xsiam_auth_id
        self.xsiam_token = xsiam_token
        self.collector_token = collector_token

    def __enter__(self):
        os.environ["DEMISTO_BASE_URL"] = self.demisto_base_url
        os.environ["DEMISTO_API_KEY"] = self.demisto_api_key
        os.environ["XSIAM_AUTH_ID"] = self.xsiam_auth_id
        os.environ["XSIAM_TOKEN"] = self.xsiam_token
        os.environ["COLLECTOR_TOKEN"] = self.collector_token
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del os.environ["DEMISTO_BASE_URL"]
        del os.environ["DEMISTO_API_KEY"]
        del os.environ["XSIAM_AUTH_ID"]
        del os.environ["XSIAM_TOKEN"]
        del os.environ["COLLECTOR_TOKEN"]
        if self.og_demisto_base_url:
            os.environ["DEMISTO_BASE_URL"] = self.og_demisto_base_url
        if self.og_demisto_api_key:
            os.environ["DEMISTO_API_KEY"] = self.og_demisto_api_key
        if self.og_xsiam_auth_id:
            os.environ["XSIAM_AUTH_ID"] = self.og_xsiam_auth_id
        if self.og_xsiam_token:
            os.environ["XSIAM_TOKEN"] = self.og_xsiam_token
        if self.og_collector_token:
            os.environ["COLLECTOR_TOKEN"] = self.og_collector_token


class TestVerifyResults:
    def test_verify_results_single_event_matching_expected_outputs(self):
        """
        Given:
            - Simulated query results for one event.
            - Test data for one event, including the expected outputs.

        When:
            - The expected outputs match the simulated query results.

        Then:
            - Verify the function returns True indicating the verification passed.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            verify_results,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        # Arrange
        tested_dataset = "vendor_product_raw"
        query_results = [
            {
                "vendor_product_raw.test_data_event_id": str(DEFAULT_TEST_EVENT_ID),
                "xdm.field1": "value1",
                "xdm.field2": "value2",
                "xdm.field3": "value3",
            }
        ]
        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset=tested_dataset,
                    event_data={},
                    expected_values={
                        "xdm.field1": "value1",
                        "xdm.field2": "value2",
                        "xdm.field3": "value3",
                    },
                )
            ]
        )
        modeling_rule = ModelingRuleMock()

        try:
            assert verify_results(
                modeling_rule, tested_dataset, query_results, test_data
            )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_verify_results_single_event_non_matching_expected_outputs(self):
        """
        Given:
            - Simulated query results for one event.
            - Test data for one event, including the expected outputs.

        When:
            - The expected outputs do not match the simulated query results.

        Then:
            - Verify the function return False indicating the result not match the expected.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            verify_results,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        # Arrange
        tested_dataset = "vendor_product_raw"
        query_results = [
            {
                "vendor_product_raw.test_data_event_id": str(DEFAULT_TEST_EVENT_ID),
                "xdm.field1": "value1",
                "xdm.field2": "value2",
                "xdm.field3": "value3",
            }
        ]
        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset=tested_dataset,
                    event_data={},
                    expected_values={
                        "xdm.field1": "value1",
                        "xdm.field2": "value2",
                        "xdm.field3": "value4",
                    },
                )
            ]
        )

        modeling_rule = ModelingRuleMock()
        test_suite = junitparser.TestSuite("Testing")
        test_suite.add_testcases(
            verify_results(modeling_rule, tested_dataset, query_results, test_data)
        )
        assert (
            test_suite.errors + test_suite.failures != 0
        ), "Test modeling rule should fail"


class TestTheTestModelingRuleCommandSingleRule:
    def test_the_test_modeling_rule_command_pack_not_on_tenant(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to not be on the tenant.
            - The command is run in non-interactive mode.

        Then:
            - Verify we get a message saying the pack is not on the tenant.
            - The command returns with a non-zero exit code.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert str_in_call_args_list(
                        logger_error.call_args_list, f"Pack {pack.name} was not found"
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_push_test_data(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to fail.

        Then:
            - Verify we get a message saying the push of the test data failed.
            - The command returns with a non-zero exit code.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        status_code=500,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        json={},
                        status_code=500,
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert str_in_call_args_list(
                        logger_error.call_args_list, "Failed pushing test data"
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_check_dataset_exists(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to fail.

        Then:
            - Verify we get a message saying the dataset was not found.
            - The command returns with a non-zero exit code.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        json={},
                        status_code=500,
                    )

                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert str_in_call_args_list(
                        logger_error.call_args_list,
                        f"Dataset {fake_test_data.data[0].dataset} does not exist",
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_start_xql_query(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to fail.

        Then:
            - Verify we get a message saying XQL query failed.
            - The command returns with a non-zero exit code.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        [
                            {
                                "json": {"reply": "fake-execution-id"},
                                "status_code": 200,
                            },
                            {"json": {}, "status_code": 500},
                        ],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        json={
                            "reply": {
                                "status": "SUCCESS",
                                "results": {"data": ["some-results"]},
                            }
                        },
                        status_code=200,
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert str_in_call_args_list(
                        logger_error.call_args_list, "Error executing XQL query"
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_get_xql_query_results(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to succeed.
            - Getting the XQL query results is simulated to fail.

        Then:
            - Verify we get a message saying XQL query failed.
            - The command returns with a non-zero exit code.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        [
                            {
                                "json": {"reply": "fake-execution-id"},
                                "status_code": 200,
                            },
                            {"json": {}, "status_code": 500},
                        ],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": ["some-results"]},
                                    }
                                },
                                "status_code": 200,
                            },
                            {"json": {}, "status_code": 500},
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert str_in_call_args_list(
                        logger_error.call_args_list, "Error executing XQL query"
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_delayed_to_get_xql_query_results(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to succeed.
            - Getting the XQL query results is delayed.

        Then:
            - Verify we get a message saying the results match the expectations.
            - The command returns with a zero exit code.
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        # mocking Variables
        id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
        event_id_1 = str(fake_test_data.data[0].test_data_event_id)
        event_id_2 = str(fake_test_data.data[1].test_data_event_id)
        mocker.patch(
            "demisto_sdk.commands.test_content.xsiam_tools.test_data.uuid4",
            side_effect=[event_id_1, event_id_2] * 3,
        )
        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # installed_packs mock request
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    # push_to_dataset mock request
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    # start_xql_query mocked request
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        [
                            {
                                "json": {"reply": "fake-execution-id"},
                                "status_code": 200,
                            }
                        ],
                    )
                    # get_xql_query_result mocked request
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": []},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {
                                            "data": [
                                                {
                                                    id_key: event_id_1,
                                                    **fake_test_data.data[
                                                        0
                                                    ].expected_values,
                                                },
                                                {
                                                    id_key: event_id_2,
                                                    **fake_test_data.data[
                                                        1
                                                    ].expected_values,
                                                },
                                            ]
                                        },
                                    }
                                },
                                "status_code": 200,
                            },
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 0
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        "All mappings validated successfully",
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_match_expectations(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to succeed.
            - Getting the XQL query results is simulated to succeed.
            - The results match the expectations.

        Then:
            - Verify we get a message saying the results match the expectations.
            - The command returns with a zero exit code.
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "1000")

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        json={"reply": "fake-execution-id"},
                        status_code=200,
                    )

                    id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
                    event_id_1 = str(fake_test_data.data[0].test_data_event_id)
                    event_id_2 = str(fake_test_data.data[1].test_data_event_id)
                    mocker.patch(
                        "demisto_sdk.commands.test_content.xsiam_tools.test_data.uuid4",
                        side_effect=[event_id_1, event_id_2] * 6,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": []},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": ["some-results"]},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {
                                            "data": [
                                                {
                                                    id_key: event_id_1,
                                                    **fake_test_data.data[
                                                        0
                                                    ].expected_values,
                                                },
                                                {
                                                    id_key: event_id_2,
                                                    **fake_test_data.data[
                                                        1
                                                    ].expected_values,
                                                },
                                            ]
                                        },
                                    }
                                },
                                "status_code": 200,
                            },
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 0
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        "All mappings validated successfully",
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_with_ignored_validations(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file including ignoring a schema/testdata mapping validations.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to succeed.
            - Getting the XQL query results is simulated to succeed.
            - The results match the expectations.

        Then:
            - Verify we get a message saying the results match the expectations.
            - The command returns with a zero exit code.
            - make sure that the schema/testdata mappings validation is skipped.
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "1000")

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )

        test_data_file = pack.modeling_rules[0].testdata

        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_as_text(fake_test_data.json(indent=4))
        test_data_file.update(
            {"ignored_validations": [Validations.SCHEMA_TYPES_ALIGNED_WITH_TEST_DATA]}
        )

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        json={"reply": "fake-execution-id"},
                        status_code=200,
                    )

                    id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
                    event_id_1 = str(fake_test_data.data[0].test_data_event_id)
                    event_id_2 = str(fake_test_data.data[1].test_data_event_id)
                    mocker.patch(
                        "demisto_sdk.commands.test_content.xsiam_tools.test_data.uuid4",
                        side_effect=[event_id_1, event_id_2] * 3,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": []},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": ["some-results"]},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {
                                            "data": [
                                                {
                                                    id_key: event_id_1,
                                                    **fake_test_data.data[
                                                        0
                                                    ].expected_values,
                                                },
                                                {
                                                    id_key: event_id_2,
                                                    **fake_test_data.data[
                                                        1
                                                    ].expected_values,
                                                },
                                            ]
                                        },
                                    }
                                },
                                "status_code": 200,
                            },
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 0
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        "All mappings validated successfully",
                    )
                    # make sure the schema validation was skipped.
                    schema_path = pack.modeling_rules[0].schema.path
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        f"Skipping the validation to check that the schema {schema_path} is aligned with TestData file",
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_with_non_existent_ignored_validations(
        self, pack, mocker
    ):
        """
        Given:
            - A test data file including ignoring un-expected validation names.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to succeed.
            - Getting the XQL query results is simulated to succeed.
            - The results match the expectations.

        Then:
            - Verify the code fails on ValidationError.
            - Make sure the exist code will be 1 (meaning failure).
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )

        test_data_file = pack.modeling_rules[0].testdata

        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_as_text(fake_test_data.json(indent=4))
        test_data_file.update({"ignored_validations": ["blabla"]})

        with requests_mock.Mocker() as m:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                m.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                m.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                # Act
                result = runner.invoke(
                    test_modeling_rule_cmd,
                    [
                        modeling_rule_directory.as_posix(),
                        "--non-interactive",
                        "--sleep_interval",
                        "0",
                        "--retry_attempts",
                        "0",
                    ],
                )
                # Assert
                assert result.exit_code == 1
                # make sure the schema validation was skipped.
                assert (
                    "The following validation names {'blabla'} are invalid"
                    in result.exception.errors()[0]["msg"]
                )

    def test_the_test_modeling_rule_command_results_do_not_match_expectations(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to succeed.
            - Getting the XQL query results is simulated to succeed.
            - The results do not match the expectations.

        Then:
            - Verify we get a message saying the results do not match the expectations.
            - The command returns with a non-zero exit code.
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        json={"reply": "fake-execution-id"},
                        status_code=200,
                    )

                    id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
                    event_id_1 = str(fake_test_data.data[0].test_data_event_id)
                    event_id_2 = str(fake_test_data.data[1].test_data_event_id)
                    mocker.patch(
                        "demisto_sdk.commands.test_content.xsiam_tools.test_data.uuid4",
                        side_effect=[event_id_1, event_id_1] * 3,
                    )
                    query_results_1 = fake_test_data.data[0].expected_values.copy()
                    query_results_1["xdm.event.outcome_reason"] = "DisAllowed"
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": []},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": ["some-results"]},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {
                                            "data": [
                                                {id_key: event_id_1, **query_results_1},
                                                {
                                                    id_key: event_id_2,
                                                    **fake_test_data.data[
                                                        1
                                                    ].expected_values,
                                                },
                                            ]
                                        },
                                    }
                                },
                                "status_code": 200,
                            },
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert str_in_call_args_list(
                        logger_info.call_args_list, "xdm.event.outcome_reason"
                    )
                    assert str_in_call_args_list(
                        logger_error.call_args_list, '"DisAllowed" != "Allowed"'
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_do_not_match_expectations_with_ignore_config(
        self, pack, monkeypatch, mocker
    ):
        """
        Given:
            - A test data file including ignoring modeling rule test data.

        When:
            - The pack is simulated to be on the tenant.
            - The command is run in non-interactive mode.
            - The push of the test data is simulated to succeed.
            - Checking the dataset exists is simulated to succeed.
            - Starting the XQL query is simulated to succeed.
            - Getting the XQL query results is simulated to succeed.
            - The results do not match the expectations.

        Then:
            - Verify we get a message saying the results do not match the expectations.
            - The command returns with a non-zero exit code.
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )

        test_data_file = pack.modeling_rules[0].testdata
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_as_text(fake_test_data.json(indent=4))
        test_data_file.update(
            {"ignored_validations": [Validations.TEST_DATA_CONFIG_IGNORE]}
        )

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        json={"reply": "fake-execution-id"},
                        status_code=200,
                    )

                    id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
                    event_id_1 = str(fake_test_data.data[0].test_data_event_id)
                    event_id_2 = str(fake_test_data.data[1].test_data_event_id)
                    query_results_1 = fake_test_data.data[0].expected_values.copy()
                    query_results_1["xdm.event.outcome_reason"] = "DisAllowed"
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": ["some-results"]},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {
                                            "data": [
                                                {id_key: event_id_1, **query_results_1},
                                                {
                                                    id_key: event_id_2,
                                                    **fake_test_data.data[
                                                        1
                                                    ].expected_values,
                                                },
                                            ],
                                        },
                                    }
                                },
                                "status_code": 200,
                            },
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 0
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        "test data config is ignored skipping the test data validation",
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."


class TestTheTestModelingRuleCommandMultipleRules:
    def test_fail_one_pass_second(self, repo, monkeypatch, mocker):
        """
        Given:
            - Two modeling rules with test data files.

        When:
            - The first modeling rule's containing pack is simulated to not be on the tenant.
            - The second modeling rule's containing pack is simulated to be on the tenant.
            - Testing the second modeling rule is simulated to succeed.
            - The command is run in non-interactive mode.

        Then:
            - Verify we get a message saying the first pack is not on the tenant.
            - Verify we get a message that the second modeling test passed.
            - The command returns with a non-zero exit code.
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "1000")

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Pack 1 with Modeling Rule
        pack_1 = repo.create_pack("Pack1")
        pack_1.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT
        )
        modeling_rule_directory_1 = Path(
            pack_1._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory_1 / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        # Create Pack 2 with Modeling Rule
        pack_2 = repo.create_pack("Pack2")
        pack_2.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME_2, rules=ONE_MODEL_RULE_TEXT
        )
        modeling_rule_directory_2 = Path(
            pack_2._modeling_rules_path / DEFAULT_MODELING_RULE_NAME_2
        )
        test_data_file = (
            modeling_rule_directory_2 / f"{DEFAULT_MODELING_RULE_NAME_2}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # Arrange
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        [
                            {"json": [], "status_code": 200},
                            {
                                "json": [{"name": pack_2.name, "id": pack_2.name}],
                                "status_code": 200,
                            },
                        ],
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        json={"reply": "fake-execution-id"},
                        status_code=200,
                    )

                    id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
                    event_id_1 = str(fake_test_data.data[0].test_data_event_id)
                    event_id_2 = str(fake_test_data.data[1].test_data_event_id)
                    mocker.patch(
                        "demisto_sdk.commands.test_content.xsiam_tools.test_data.uuid4",
                        side_effect=[event_id_1, event_id_2] * 6,
                    )
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": []},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": ["some-results"]},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {
                                            "data": [
                                                {
                                                    id_key: event_id_1,
                                                    **fake_test_data.data[
                                                        0
                                                    ].expected_values,
                                                },
                                                {
                                                    id_key: event_id_2,
                                                    **fake_test_data.data[
                                                        1
                                                    ].expected_values,
                                                },
                                            ]
                                        },
                                    }
                                },
                                "status_code": 200,
                            },
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory_1.as_posix(),
                            modeling_rule_directory_2.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert str_in_call_args_list(
                        logger_error.call_args_list, f"Pack {pack_1.name} was not found"
                    )
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        "All mappings validated successfully",
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."


class TestTheTestModelingRuleCommandInteractive:
    def test_no_testdata_file_exists(self, repo, monkeypatch, mocker):
        """
        Given:
            - A modeling rule with no test data file.

        When:
            - The command is run in interactive mode.

        Then:
            - Verify we get a message saying the test data file does not exist.
            - Ensure we are prompted  to create a test data file.
            - The command returns with a non-zero exit code.
            - Ensure the test data file was created.
            - Ensure that the log output from creating the testdata file is not duplicated.
        """
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )

        # need to override this because when running this way the command name is 'test-modeling-rule' (taken from the
        # module name from which it is imported) but the logic in 'init-test-data' command looks to see if the parent
        # command is 'test' to determine if it should execute setup_rich_logging logic
        test_modeling_rule_cmd.registered_commands[0].name = "test"

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "1000")

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Pack with Modeling Rule
        pack = repo.create_pack("Pack1")
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        if test_data_file.exists():
            test_data_file.unlink()

        try:
            with SetFakeXsiamClientEnvironmentVars():
                mock_confirm = mocker.patch(
                    "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule."
                    "typer.confirm"
                )
                mock_prompt = mocker.patch(
                    "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule."
                    "typer.prompt"
                )
                # Arrange
                mock_confirm.return_value = True
                mock_prompt.return_value = 2
                # Act
                result = runner.invoke(
                    test_modeling_rule_cmd,
                    [
                        modeling_rule_directory.as_posix(),
                        "--interactive",
                        "--sleep_interval",
                        "0",
                        "--retry_attempts",
                        "0",
                    ],
                )
                # Assert

                expected_log_count = 1
                assert result.exit_code == 0
                assert test_data_file.exists()
                assert str_in_call_args_list(
                    logger_warning.call_args_list, "No test data file found for"
                )
                call_counter = sum(
                    bool(
                        current_call
                        and isinstance(current_call[0], tuple)
                        and "Creating test data file for: " in current_call[0][0]
                    )
                    for current_call in logger_info.call_args_list
                )
                assert call_counter == expected_log_count

        except typer.Exit:
            assert False, "No exception should be raised in this scenario."


@pytest.mark.parametrize(
    "epoc_time, with_ms, human_readable_time",
    [
        (1686231456000, False, "Jun 8th 2023 13:37:36"),
        (1686231456123, False, "Jun 8th 2023 13:37:36"),
        (1686231456000, True, "Jun 8th 2023 13:37:36.000000"),
        (1686231456123, True, "Jun 8th 2023 13:37:36.123000"),
    ],
)
def test_convert_epoch_time_to_string_time(epoc_time, with_ms, human_readable_time):
    """
    Given:
        - An Epoch time.
            case-1: Epoch time with MS equal to 0. (ignore MS)
            case-2: Epoch time with MS equal to 123. (ignore MS)
            case-3: Epoch time with MS equal to 0.
            case-4: Epoch time with MS equal to 123.

    When:
        - The convert_epoch_time_to_string_time function is running.

    Then:
        - Verify we get the expected results.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
        convert_epoch_time_to_string_time,
    )

    with freeze_time("2023/06/14T10:20:00Z"):
        assert (
            convert_epoch_time_to_string_time(epoc_time, with_ms) == human_readable_time
        )


@pytest.mark.parametrize(
    "day, suffix",
    [
        (1, "st"),
        (2, "nd"),
        (3, "rd"),
        (4, "th"),
        (10, "th"),
        (11, "th"),
        (12, "th"),
        (21, "st"),
        (31, "st"),
    ],
)
def test_day_suffix(day, suffix):
    """
    Given:
        - A day of a month.
            case-1: 1 => st.
            case-2: 2 => nd.
            case-3: 3 => rd.
            case-4: 4 => th.
            case-5: 10 => th.
            case-6: 11 => th.
            case-7: 12 => th.
            case-8: 21 => st.
            case-9: 31 => st.

    When:
        - The day_suffix function is running.

    Then:
        - Verify we get the expected results.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
        day_suffix,
    )

    assert day_suffix(day) == suffix


@pytest.mark.parametrize(
    "mr_text, expected_result",
    [
        ("historically", False),
        ("call a", True),
    ],
)
def test_call_rule_regex(mr_text, expected_result):
    """
    Test the CALL_RULE_REGEX regex matches text containing 'call'.

    Given:
        - mr_text: Text to search for 'call'
        - expected_result: Whether we expect mr_text to match

    When:
        - Search mr_text with ModelingRule.CALL_RULE_REGEX

    Then:
        - The search result should match expected_result
    """
    from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import (
        ModelingRule,
    )

    mr = ModelingRule
    assert bool(mr.CALL_RULE_REGEX.search(mr_text)) == expected_result


class TestValidateSchemaAlignedWithTestData:
    @pytest.mark.parametrize(
        "event_data, schema_file",
        [
            (
                {
                    "int": 1,
                    "string": "2",
                    "bool": True,
                    "float": 1.0,
                    "datetime": "Nov 9th 2022 15:46:30",
                    "json": {"1": "2"},
                },
                {
                    "dataset": {
                        "int": {"type": "int", "is_array": False},
                        "string": {"type": "string", "is_array": False},
                        "float": {"type": "float", "is_array": False},
                        "datetime": {"type": "datetime", "is_array": False},
                        "bool": {"type": "boolean", "is_array": False},
                    }
                },
            ),
            (
                {
                    "list_int": [1, 2],
                    "list_string": ["1", "2"],
                    "list_bool": [True, False],
                    "list_float": [1.0, 2.0],
                    "list_datetime": ["Nov 9th 2022 15:46:30", "Nov 9th 2022 15:46:30"],
                    "list_json": [{"1": "2"}, {"1": "2"}],
                },
                {
                    "dataset": {
                        "list_int": {"type": "string", "is_array": False},
                        "list_string": {"type": "string", "is_array": False},
                        "list_float": {"type": "string", "is_array": False},
                        "list_datetime": {"type": "string", "is_array": False},
                        "list_bool": {"type": "string", "is_array": False},
                        "list_json": {"type": "string", "is_array": False},
                    }
                },
            ),
        ],
    )
    def test_validate_schema_aligned_with_test_data_positive(
        self, mocker, event_data: dict, schema_file: dict
    ):
        """
        Given:
            - Case A: event data with all schema types and correct corresponding schema file
            - Case B: event data with all schema types as lists and correct corresponding schema file

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify no exception is raised.
            - verify that there was not error raised
            - verify not warning was raised
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data=event_data,
                    expected_values={},
                )
            ]
        )

        validate_schema_aligned_with_test_data(test_data=test_data, schema=schema_file)
        assert not logger_error_mocker.called
        assert not logger_warning_mocker.called

    def test_validate_schema_aligned_with_test_data_missing_fields_in_test_data(
        self, mocker
    ):
        """
        Given:
            - event data that is missing one schema field.

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify no exception is raised.
            - verify that there was not error raised
            - verify that warning was raised indicating that the test data is missing schema field
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": 1},
                    expected_values={},
                )
            ]
        )

        validate_schema_aligned_with_test_data(
            test_data=test_data,
            schema={
                "dataset": {
                    "int": {"type": "int", "is_array": False},
                    "string": {"type": "string", "is_array": False},
                }
            },
        )
        assert not logger_error_mocker.called
        assert logger_warning_mocker.called

    def test_validate_schema_aligned_with_test_data_invalid_schema_mappings(
        self, mocker
    ):
        """
        Given:
            - event data that it's mapping to schema is wrong.

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify 'Typer.exception' is raised.
            - verify that there was not warning raised
            - verify that error was raised indicating that the test data is missing schema field
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": 1, "bool": True},
                    expected_values={},
                )
            ]
        )

        success, _ = validate_schema_aligned_with_test_data(
            test_data=test_data,
            schema={
                "dataset": {
                    "int": {"type": "string", "is_array": False},
                    "bool": {"type": "float", "is_array": False},
                }
            },
        )
        assert success is False
        assert logger_error_mocker.called
        assert not logger_warning_mocker.called

    def test_validate_schema_aligned_with_test_data_events_have_same_key_with_different_types(
        self, mocker
    ):
        """
        Given:
            - 2 events that have the same key with two different types (int and string).

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify no exception is raised.
            - verify that the correct message is printed to logger info.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": 1, "bool": True},
                    expected_values={},
                ),
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": "1", "bool": True},
                    expected_values={},
                ),
            ]
        )

        success, _ = validate_schema_aligned_with_test_data(
            test_data=test_data,
            schema={
                "dataset": {
                    "int": {"type": "int", "is_array": False},
                    "bool": {"type": "boolean", "is_array": False},
                }
            },
        )
        assert success is False
        assert (
            "The testdata contains events with the same event_key"
            in logger_error_mocker.call_args_list[0].args[0]
        )
        assert not logger_warning_mocker.called


class TestDeleteExistingDataset:
    def test_delete_data_set(self, pack, monkeypatch, mocker):
        """
        Given:
            - An existing dataset on the tenant.

        When:
            - The command is run with 'delete_existing_dataset' flag.

        Then:
            - Verify no exception is raised.
            - Verify we get a message saying the dataset was deleted.

        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        monkeypatch.setenv("COLUMNS", "1000")

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch("time.sleep", return_value=None)

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        path_to_fake_test_data_file = (
            Path(__file__).parent / "test_data/fake_test_data_file.json"
        )
        fake_test_data = TestData.parse_file(path_to_fake_test_data_file.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))
        # mocking Variables
        id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
        event_id_1 = str(fake_test_data.data[0].test_data_event_id)
        event_id_2 = str(fake_test_data.data[1].test_data_event_id)
        mocker.patch(
            "demisto_sdk.commands.test_content.xsiam_tools.test_data.uuid4",
            side_effect=[event_id_1, event_id_2] * 6,
        )
        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    # installed_packs mock request
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                        json=[{"name": pack.name, "id": pack.name}],
                    )
                    # push_to_dataset mock request
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                        json={},
                        status_code=200,
                    )
                    # delete_dataset mock request
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/delete_dataset",
                        json={},
                        status_code=200,
                    )
                    # start_xql_query mocked request
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                        [
                            {
                                "json": {"reply": "fake-execution-id"},
                                "status_code": 200,
                            }
                        ],
                    )
                    # get_xql_query_result mocked request
                    m.post(
                        f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/get_query_results/",
                        [
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": ["fake_results"]},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {"data": []},
                                    }
                                },
                                "status_code": 200,
                            },
                            {
                                "json": {
                                    "reply": {
                                        "status": "SUCCESS",
                                        "results": {
                                            "data": [
                                                {
                                                    id_key: event_id_1,
                                                    **fake_test_data.data[
                                                        0
                                                    ].expected_values,
                                                },
                                                {
                                                    id_key: event_id_2,
                                                    **fake_test_data.data[
                                                        1
                                                    ].expected_values,
                                                },
                                            ]
                                        },
                                    }
                                },
                                "status_code": 200,
                            },
                        ],
                    )
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [
                            modeling_rule_directory.as_posix(),
                            "--non-interactive",
                            "--sleep_interval",
                            "0",
                            "--retry_attempts",
                            "0",
                            "--delete_existing_dataset",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 0
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        "Deleting existing fake_fakerson_raw dataset",
                    )
                    assert str_in_call_args_list(
                        logger_info.call_args_list,
                        "Dataset fake_fakerson_raw deleted successfully",
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."
