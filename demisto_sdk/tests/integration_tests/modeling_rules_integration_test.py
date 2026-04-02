import os
from pathlib import Path

import pytest
import requests_mock
import typer
from typer.testing import CliRunner

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.test_content.xsiam_tools.test_data import Validations

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
TEST_DATA_FILE_PATH = Path(
    f"{git_path()}/demisto_sdk/commands/test_content/test_modeling_rule/tests/test_data/fake_test_data_file.json"
)


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


@pytest.fixture
def requests_mocker(requests_mock):
    # A requests mocker that mocks the API call to /xsoar/about
    with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
        requests_mock.get(
            f"{fake_env_vars.demisto_base_url}/xsoar/about",
            json={"demistoVersion": "8.4.0"},
        )
        yield requests_mock


class TestSkippingInvalidModelingRule:
    @pytest.mark.parametrize(
        "fromVersion, toVersion, demistoVersion",
        [("6.8.0", "8.3.0", "8.4.0"), ("6.8.0", "99.99.99", "6.5.0")],
    )
    def test_skipping_invalid_modeling_rule(
        self, pack, monkeypatch, mocker, fromVersion, toVersion, demistoVersion
    ):
        """
        Given:
            - A from and to version configuration of a modeling rule.
            - The demisto version of the XSIAM tenant.

        When:
            - Running the modeling-rule test command.

        Then:
            - Verify no exception is raised.
            - Verify we get a message saying the the modeling rule is not compatible with the demisto version of the tenant.

        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )
        # Create Test Data File
        pack.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME,
            yml={
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": fromVersion,
                "toversion": toVersion,
                "tags": "tag",
                "rules": "",
                "schema": "",
            },
        )
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))
        try:
            with requests_mock.Mocker() as m:
                with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                    m.get(
                        f"{fake_env_vars.demisto_base_url}/xsoar/about",
                        json={"demistoVersion": demistoVersion},
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
                    assert (
                        "XSIAM Tenant's Demisto version doesn't match Modeling Rule"
                        in result.output
                    )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."


class TestTheTestModelingRuleCommandSingleRule:
    def test_the_test_modeling_rule_command_pack_not_on_tenant(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
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
                assert f"Pack {pack.name} was not found" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_push_test_data(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    status_code=500,
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                    json={},
                    status_code=500,
                )
                # Act
                result = CliRunner().invoke(
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
                assert "Failed pushing test data" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_check_dataset_exists(
        self, pack, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )

        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
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
                assert (
                    f"Dataset {fake_test_data.data[0].dataset} does not exist"
                    in result.output
                )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_start_xql_query(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                    [
                        {
                            "json": {"reply": "fake-execution-id"},
                            "status_code": 200,
                        },
                        {"json": {}, "status_code": 500},
                    ],
                )
                requests_mocker.post(
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
                assert "Error executing XQL query" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_fail_to_get_xql_query_results(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )

        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                    [
                        {
                            "json": {"reply": "fake-execution-id"},
                            "status_code": 200,
                        },
                        {"json": {}, "status_code": 500},
                    ],
                )
                requests_mocker.post(
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
                assert "Error executing XQL query" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_delayed_to_get_xql_query_results(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )

        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
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
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # installed_packs mock request
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                # push_to_dataset mock request
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                # start_xql_query mocked request
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                    [
                        {
                            "json": {"reply": "fake-execution-id"},
                            "status_code": 200,
                        }
                    ],
                )
                # get_xql_query_result mocked request
                requests_mocker.post(
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
                assert "All mappings validated successfully" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_match_expectations(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )

        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
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
                requests_mocker.post(
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
                assert "All mappings validated successfully" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_with_ignored_validations(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        # so the logged output when running the command will be printed with a width of 120 characters

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )

        test_data_file = pack.modeling_rules[0].testdata

        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_as_text(fake_test_data.json(indent=4))
        test_data_file.update(
            {"ignored_validations": [Validations.SCHEMA_TYPES_ALIGNED_WITH_TEST_DATA]}
        )

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
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
                requests_mocker.post(
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
                assert "All mappings validated successfully" in result.output
                # make sure the schema validation was skipped.
                schema_path = pack.modeling_rules[0].schema.path
                assert (
                    f"Skipping the validation to check that the schema {schema_path} is aligned with TestData file"
                    in result.output
                )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_with_non_existent_ignored_validations(
        self, pack, mocker, requests_mocker
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
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )

        test_data_file = pack.modeling_rules[0].testdata

        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_as_text(fake_test_data.json(indent=4))
        test_data_file.update({"ignored_validations": ["blabla"]})

        with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
            # Arrange
            requests_mocker.get(
                f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                json=[{"name": pack.name, "id": pack.name}],
            )
            requests_mocker.post(
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
            assert "Failed to parse test data file" in result.output

    def test_the_test_modeling_rule_command_results_do_not_match_expectations(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
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
                requests_mocker.post(
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
                assert "xdm.event.outcome_reason" in result.output
                assert '"DisAllowed" != "Allowed"' in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_the_test_modeling_rule_command_results_do_not_match_expectations_with_ignore_config(
        self, pack, monkeypatch, mocker, requests_mocker
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

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )

        test_data_file = pack.modeling_rules[0].testdata
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_as_text(fake_test_data.json(indent=4))
        test_data_file.update(
            {"ignored_validations": [Validations.TEST_DATA_CONFIG_IGNORE]}
        )

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                    json={"reply": "fake-execution-id"},
                    status_code=200,
                )

                id_key = f"{fake_test_data.data[0].dataset}.test_data_event_id"
                event_id_1 = str(fake_test_data.data[0].test_data_event_id)
                event_id_2 = str(fake_test_data.data[1].test_data_event_id)
                query_results_1 = fake_test_data.data[0].expected_values.copy()
                query_results_1["xdm.event.outcome_reason"] = "DisAllowed"
                requests_mocker.post(
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
                assert (
                    "test data config is ignored skipping the test data validation"
                    in result.output
                )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."


class TestTheTestModelingRuleCommandMultipleRules:
    def test_fail_one_pass_second(self, repo, monkeypatch, mocker, requests_mocker):
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

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

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
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
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
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
        test_data_file.write_text(fake_test_data.json(indent=4))

        try:
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # Arrange
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    [
                        {"json": [], "status_code": 200},
                        {
                            "json": [{"name": pack_2.name, "id": pack_2.name}],
                            "status_code": 200,
                        },
                    ],
                )
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                requests_mocker.post(
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
                requests_mocker.post(
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
                assert f"Pack {pack_1.name} was not found" in result.output
                assert "All mappings validated successfully" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."


class TestTheTestModelingRuleCommandInteractive:
    def test_no_testdata_file_exists(self, repo, monkeypatch, mocker, requests_mocker):
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
        monkeypatch.setenv("COLUMNS", "1000")

        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

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
            result = CliRunner().invoke(
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
            assert result.exit_code == 0
            assert test_data_file.exists()
            assert result.output.count("Creating test data file for: ") == 1


class TestDeleteExistingDataset:
    def test_delete_data_set(self, pack, monkeypatch, mocker, requests_mocker):
        """
        Given:
            - An existing dataset on the tenant.

        When:
            - The command is run with 'delete_existing_dataset' flag.

        Then:
            - Verify no exception is raised.
            - Verify we get a message saying the dataset was deleted.

        """

        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            app as test_modeling_rule_cmd,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

        runner = CliRunner()
        mocker.patch(
            "demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule.sleep",
            return_value=None,
        )

        # Create Test Data File
        pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
        modeling_rule_directory = Path(
            pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME
        )
        test_data_file = (
            modeling_rule_directory / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        )
        fake_test_data = TestData.parse_file(TEST_DATA_FILE_PATH.as_posix())
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
            with SetFakeXsiamClientEnvironmentVars() as fake_env_vars:
                # installed_packs mock request
                requests_mocker.get(
                    f"{fake_env_vars.demisto_base_url}/xsoar/contentpacks/metadata/installed",
                    json=[{"name": pack.name, "id": pack.name}],
                )
                # push_to_dataset mock request
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/logs/v1/xsiam",
                    json={},
                    status_code=200,
                )
                # delete_dataset mock request
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/delete_dataset",
                    json={},
                    status_code=200,
                )
                # start_xql_query mocked request
                requests_mocker.post(
                    f"{fake_env_vars.demisto_base_url}/public_api/v1/xql/start_xql_query/",
                    [
                        {
                            "json": {"reply": "fake-execution-id"},
                            "status_code": 200,
                        }
                    ],
                )
                # get_xql_query_result mocked request
                requests_mocker.post(
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
                assert "Deleting existing fake_fakerson_raw dataset" in result.output
                assert "Dataset fake_fakerson_raw deleted successfully" in result.output
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."
