import logging
import os
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import pytest
import requests_mock
import typer
from typer.testing import CliRunner

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


# the __init__ method of the Downloader class disables logging globally which breaks these tests
# so in the case the tests for the Downloader class are run first, we need to re-enable logging
class EnableLogging:
    def __init__(self) -> None:
        self.loggers_to_levels = deepcopy(logging.root.manager.loggerDict)

    def __enter__(self) -> "EnableLogging":
        logging.disable(logging.NOTSET)
        return self

    def __exit__(self, exctype, excval, exctraceback) -> None:
        logging.root.manager.loggerDict = self.loggers_to_levels


@pytest.fixture(name="enable_logging", scope="module", autouse=True)
def fixture_enable_logging():
    with EnableLogging():
        yield


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
            - Verify the function returns successfully.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            verify_results,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        # Arrange
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
                    dataset="vendor_product_raw",
                    event_data={},
                    expected_values={
                        "xdm.field1": "value1",
                        "xdm.field2": "value2",
                        "xdm.field3": "value3",
                    },
                )
            ]
        )

        try:
            verify_results(query_results, test_data)
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
            - Verify the function raises a typer.Exit exception.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            verify_results,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        # Arrange
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
                    dataset="vendor_product_raw",
                    event_data={},
                    expected_values={
                        "xdm.field1": "value1",
                        "xdm.field2": "value2",
                        "xdm.field3": "value4",
                    },
                )
            ]
        )

        with pytest.raises(typer.Exit):
            verify_results(query_results, test_data)


class TestTheTestModelingRuleCommandSingleRule:
    def test_the_test_modeling_rule_command_pack_not_on_tenant(self, pack):
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
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                        [mrule_dir.as_posix(), "--non-interactive"],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert f"Pack {pack.name} was not found" in result.stdout
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_push_test_data(self, pack):
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
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                    # Act
                    result = runner.invoke(
                        test_modeling_rule_cmd,
                        [mrule_dir.as_posix(), "--non-interactive"],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert "Failed pushing test data" in result.stdout
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_check_dataset_exists(
        self, pack, monkeypatch
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
        from functools import partial

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            check_dataset_exists,
        )

        func_path = (
            "demisto_sdk.commands.test_content.test_modeling_rule."
            "test_modeling_rule.check_dataset_exists"
        )
        # override the default timeout to 1 second so only one iteration of the loop will be executed
        check_dataset_exists_with_timeout = partial(check_dataset_exists, timeout=5)
        monkeypatch.setattr(func_path, check_dataset_exists_with_timeout)

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "120")

        runner = CliRunner()

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                        [mrule_dir.as_posix(), "--non-interactive"],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert (
                        f"Dataset {fake_test_data.data[0].dataset} does not exist"
                        in result.stdout
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_start_xql_query(
        self, pack, monkeypatch
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
        from functools import partial

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            check_dataset_exists,
        )

        func_path = (
            "demisto_sdk.commands.test_content.test_modeling_rule."
            "test_modeling_rule.check_dataset_exists"
        )
        # override the default timeout to 1 second so only one iteration of the loop will be executed
        check_dataset_exists_with_timeout = partial(check_dataset_exists, timeout=5)
        monkeypatch.setattr(func_path, check_dataset_exists_with_timeout)

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "120")

        runner = CliRunner()

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                        [mrule_dir.as_posix(), "--non-interactive"],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert "Error executing XQL query" in result.stdout
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_get_xql_query_results(
        self, pack, monkeypatch
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
        from functools import partial

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            check_dataset_exists,
        )

        func_path = (
            "demisto_sdk.commands.test_content.test_modeling_rule."
            "test_modeling_rule.check_dataset_exists"
        )
        # override the default timeout to 1 second so only one iteration of the loop will be executed
        check_dataset_exists_with_timeout = partial(check_dataset_exists, timeout=5)
        monkeypatch.setattr(func_path, check_dataset_exists_with_timeout)

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "120")

        runner = CliRunner()

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                        [mrule_dir.as_posix(), "--non-interactive"],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert "Error executing XQL query" in result.stdout
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_match_expectations(
        self, pack, monkeypatch
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
        from functools import partial

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            check_dataset_exists,
        )

        func_path = (
            "demisto_sdk.commands.test_content.test_modeling_rule."
            "test_modeling_rule.check_dataset_exists"
        )
        # override the default timeout to 1 second so only one iteration of the loop will be executed
        check_dataset_exists_with_timeout = partial(check_dataset_exists, timeout=5)
        monkeypatch.setattr(func_path, check_dataset_exists_with_timeout)

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "120")

        runner = CliRunner()

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                        [mrule_dir.as_posix(), "--non-interactive"],
                    )
                    # Assert
                    assert result.exit_code == 0
                    assert "Mappings validated successfully" in result.stdout
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_do_not_match_expectations(
        self, pack, monkeypatch
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
        from functools import partial

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            check_dataset_exists,
        )

        func_path = (
            "demisto_sdk.commands.test_content.test_modeling_rule."
            "test_modeling_rule.check_dataset_exists"
        )
        # override the default timeout to 1 second so only one iteration of the loop will be executed
        check_dataset_exists_with_timeout = partial(check_dataset_exists, timeout=5)
        monkeypatch.setattr(func_path, check_dataset_exists_with_timeout)

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "120")

        runner = CliRunner()

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                        [mrule_dir.as_posix(), "--non-interactive"],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert (
                        'xdm.event.outcome_reason --- "DisAllowed" != "Allowed"'
                        in result.stdout
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."


class TestTheTestModelingRuleCommandMultipleRules:
    def test_fail_one_pass_second(self, repo, monkeypatch):
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
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "120")

        runner = CliRunner()

        # Create Pack 1 with Modeling Rule
        pack_1 = repo.create_pack("Pack1")
        pack_1.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT
        )
        mrule_dir_1 = Path(pack_1._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir_1 / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
        mrule_dir_2 = Path(pack_2._modeling_rules_path / DEFAULT_MODELING_RULE_NAME_2)
        test_data_file = mrule_dir_2 / f"{DEFAULT_MODELING_RULE_NAME_2}_testdata.json"
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
                            mrule_dir_1.as_posix(),
                            mrule_dir_2.as_posix(),
                            "--non-interactive",
                        ],
                    )
                    # Assert
                    assert result.exit_code == 1
                    assert f"Pack {pack_1.name} was not found" in result.stdout
                    assert "Mappings validated successfully" in result.stdout
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
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )

        # need to override this because when running this way the command name is 'test-modeling-rule' (taken from the
        # module name from which it is imported) but the logic in 'init-test-data' command looks to see if the parent
        # command is 'test' to determine if it should execute setup_rich_logging logic
        test_modeling_rule_cmd.registered_commands[0].name = "test"

        # so the logged output when running the command will be printed with a width of 120 characters
        monkeypatch.setenv("COLUMNS", "120")

        runner = CliRunner()

        # Create Pack with Modeling Rule
        pack = repo.create_pack("Pack1")
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
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
                    test_modeling_rule_cmd, [mrule_dir.as_posix(), "--interactive"]
                )
                # Assert
                expected_log_count = 1
                assert result.exit_code == 0
                assert test_data_file.exists()
                assert "WARNING  No test data file found for" in result.stdout
                assert (
                    result.stdout.count("Creating test data file for: ")
                    == expected_log_count
                )

        except typer.Exit:
            assert False, "No exception should be raised in this scenario."
