import logging  # noqa: TID251 # specific case, passed as argument to 3rd party
import os

from pathlib import Path
from threading import Thread
from typing import Any, List, Optional, Tuple, Union

import demisto_client
import pytest

import typer
from google.cloud import storage  # type: ignore[attr-defined]
from junitparser import Error, JUnitXml, TestCase, TestSuite
from junitparser.junitparser import Failure, Result, Skipped


from demisto_sdk.commands.common.constants import (
    PLAYBOOKS_FLOW_TEST,
    XSIAM_SERVER_TYPE,
)

from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
)
from demisto_sdk.commands.common.tools import (
    get_json_file,
    string_to_bool,
)
from demisto_sdk.commands.test_content.ParallelLoggingManager import (
    ParallelLoggingManager,
)
from demisto_sdk.commands.test_content.tools import (
    get_ui_url,
    XSIAM_CLIENT_SLEEP_INTERVAL,
    XSIAM_CLIENT_RETRY_ATTEMPTS,
    logs_token_cb,
    tenant_config_cb,
    create_retrying_caller,
    get_relative_path_to_content,
    duration_since_start_time,
    get_utc_now
)

from demisto_sdk.commands.test_content.xsiam_tools.xsiam_client import (
    XsiamApiClient,
    XsiamApiClientConfig,
)

CI_PIPELINE_ID = os.environ.get("CI_PIPELINE_ID")

app = typer.Typer()


# ============================================== Classes ============================================ #
class TestResultCapture:
    """
        This class is used to store the pytest results in test suite
    """

    def __init__(self, junit_testsuite):
        self.junit_testsuite = junit_testsuite

    def pytest_runtest_logreport(self, report):
        if report.when == "call":  # Only capture results of test calls
            test_case = TestCase(report.nodeid)
            test_case.classname = report.location[0]  # Test's module or class
            test_case.time = report.duration  # Add the test duration
            if report.outcome == "passed":
                self.junit_testsuite.add_testcase(test_case)
            elif report.outcome == "failed":
                failure = Failure(report.longreprtext if report.longrepr else "Test failed")
                test_case.result = failure
                self.junit_testsuite.add_testcase(test_case)
            elif report.outcome == "skipped":
                skipped = Skipped("Test skipped")
                test_case.result = skipped
                self.junit_testsuite.add_testcase(test_case)


class TestResults:
    def __init__(
            self,
            service_account: str = None,
            artifacts_bucket: str = None,
    ):
        self.test_results_xml_file = JUnitXml()
        self.errors = False
        self.service_account = service_account
        self.artifacts_bucket = artifacts_bucket

    def upload_result_json_to_bucket(
            self,
            repository_name: str,
            file_name,
            original_file_path: Path,
            logging_module: Union[Any, ParallelLoggingManager] = logging,
    ):
        """Uploads a JSON object to a specified path in the GCP bucket.

        Args:
          original_file_path: The path to the JSON file to upload.
          repository_name: The name of the repository within the bucket.
          file_name: The desired filename for the uploaded JSON data.
          logging_module: Logging module to use for upload_result_json_to_bucket.
        """
        logging_module.info("Start uploading playbook flow test results file to bucket")

        storage_client = storage.Client.from_service_account_json(self.service_account)
        storage_bucket = storage_client.bucket(self.artifacts_bucket)

        blob = storage_bucket.blob(
            f"content-playbook-flow-test/{repository_name}/{file_name}"
        )
        blob.upload_from_filename(
            original_file_path.as_posix(),
            content_type="application/xml",
        )

        logging_module.info("Finished uploading playbook flow test results file to bucket")


class BuildContext:
    def __init__(
            self,
            nightly: bool,
            build_number: Optional[str],
            branch_name: Optional[str],
            retry_attempts: int,
            sleep_interval: int,
            logging_module: ParallelLoggingManager,
            cloud_servers_path: str,
            cloud_servers_api_keys: str,
            service_account: Optional[str],
            artifacts_bucket: Optional[str],
            xsiam_url: Optional[str],
            xsiam_token: Optional[str],
            api_key: Optional[str],
            auth_id: Optional[str],
            collector_token: Optional[str],
            inputs: Optional[List[Path]],
            machine_assignment: str,
            ctx: typer.Context,
    ):
        self.logging_module: ParallelLoggingManager = logging_module
        self.retrying_caller = create_retrying_caller(retry_attempts, sleep_interval)
        self.ctx = ctx

        # --------------------------- overall build configuration -------------------------------
        self.is_nightly = nightly
        self.build_number = build_number
        self.build_name = branch_name

        # -------------------------- Manual run on a single instance --------------------------
        self.xsiam_url = xsiam_url
        self.xsiam_token = xsiam_token
        self.api_key = api_key
        self.auth_id = auth_id
        self.collector_token = collector_token
        self.inputs = inputs

        # --------------------------- Machine preparation -------------------------------

        self.cloud_servers_path_json = get_json_file(cloud_servers_path)
        self.cloud_servers_api_keys_json = get_json_file(cloud_servers_api_keys)
        self.machine_assignment_json = get_json_file(machine_assignment)

        # --------------------------- Testing preparation -------------------------------

        self.tests_data_keeper = TestResults(
            service_account,
            artifacts_bucket,
        )

        # --------------------------- Machine preparation logic -------------------------------

        self.servers = self.create_servers()

    @staticmethod
    def prefix_with_packs(path_str: Union[str, Path]) -> Path:
        path = Path(path_str)
        if path.parts[0] == "Packs":
            return path
        return Path("Packs") / path

    def create_servers(self):
        """
        Create servers object based on build type.
        """
        # If xsiam_url is provided we assume it's a run on a single server.
        if self.xsiam_url:
            return [
                CloudServerContext(
                    self,
                    base_url=self.xsiam_url,
                    api_key=self.api_key,  # type: ignore[arg-type]
                    auth_id=self.auth_id,  # type: ignore[arg-type]
                    token=self.xsiam_token,  # type: ignore[arg-type]
                    collector_token=self.collector_token,
                    ui_url=get_ui_url(self.xsiam_url),
                    tests=[BuildContext.prefix_with_packs(test) for test in self.inputs]
                    if self.inputs
                    else [],
                )
            ]
        servers_list = []
        for machine, assignment in self.machine_assignment_json.items():
            tests = [
                test
                for test in assignment.get("tests", {}).get(PLAYBOOKS_FLOW_TEST, [])
            ]
            if not tests:
                logger.info(f"No playbook flow tests found for machine {machine}")
                continue
            servers_list.append(
                CloudServerContext(
                    self,
                    base_url=self.cloud_servers_path_json.get(machine, {}).get(
                        "base_url", ""
                    ),
                    ui_url=self.cloud_servers_path_json.get(machine, {}).get(
                        "ui_url", ""
                    ),
                    tests=tests,
                    api_key=self.cloud_servers_api_keys_json.get(machine, {}).get(
                        "api-key"
                    ),
                    auth_id=self.cloud_servers_api_keys_json.get(machine, {}).get(
                        "x-xdr-auth-id"
                    ),
                    token=self.cloud_servers_api_keys_json.get(machine, {}).get(
                        "token"
                    ),
                )
            )
        return servers_list


class CloudServerContext:
    def __init__(
            self,
            build_context: BuildContext,
            base_url: str,
            api_key: str,
            auth_id: str,
            token: str,
            ui_url: str,
            tests: List[Path],
            collector_token: Optional[str] = None,
    ):
        self.build_context = build_context
        self.client = None
        self.base_url = base_url
        self.api_key = api_key
        self.auth_id = auth_id
        self.token = token
        self.collector_token = collector_token
        os.environ.pop(
            "DEMISTO_USERNAME", None
        )  # we use client without demisto username
        self.configure_new_client()
        self.ui_url = ui_url
        self.tests = tests

    def configure_new_client(self):
        if self.client:
            self.client.api_client.pool.close()
            self.client.api_client.pool.terminate()
            del self.client
        self.client = demisto_client.configure(
            base_url=self.base_url,
            api_key=self.api_key,
            auth_id=self.auth_id,
            verify_ssl=False,
        )

    def execute_tests(self):
        try:
            self.build_context.logging_module.info(
                f"Starts tests with server url - {get_ui_url(self.ui_url)}",
                real_time=True,
            )
            start_time = get_utc_now()
            self.build_context.logging_module.info(
                f"Running the following tests: {self.tests}",
                real_time=True,
            )

            xsiam_client_cfg = XsiamApiClientConfig(
                base_url=self.base_url,  # type: ignore[arg-type]
                api_key=self.api_key,  # type: ignore[arg-type]
                auth_id=self.auth_id,  # type: ignore[arg-type]
                token=self.token,  # type: ignore[arg-type]
                collector_token=self.collector_token,  # type: ignore[arg-type]
            )
            xsiam_client = XsiamApiClient(xsiam_client_cfg)

            for i, playbook_flow_test_directory in enumerate(self.tests, start=1):
                logger.info(
                    f"<cyan>[{i}/{len(self.tests)}] playbook flow tests: {get_relative_path_to_content(playbook_flow_test_directory)}</cyan>",
                )

                success, playbook_flow_test_test_suite = run_playbook_flow_test_pytest(
                    playbook_flow_test_directory,
                    xsiam_client=xsiam_client
                )

                if success:
                    logger.info(
                        f"<green>Playbook flow test {get_relative_path_to_content(playbook_flow_test_directory)} passed</green>",
                    )
                else:
                    self.build_context.tests_data_keeper.errors = True
                    logger.error(
                        f"<red>Playbook flow test {get_relative_path_to_content(playbook_flow_test_directory)} failed</red>",
                    )
                if playbook_flow_test_test_suite:
                    playbook_flow_test_test_suite.add_property(
                        "start_time",
                        start_time,  # type:ignore[arg-type]
                    )
                    self.build_context.tests_data_keeper.test_results_xml_file.add_testsuite(
                        playbook_flow_test_test_suite
                    )

                    self.build_context.logging_module.info(
                        f"Finished tests with server url - " f"{self.ui_url}",
                        real_time=True,
                    )
            duration = duration_since_start_time(start_time)
            self.build_context.logging_module.info(
                f"Finished tests with server url - {self.ui_url}, Took: {duration} seconds",
                real_time=True,
            )
        except Exception:
            self.build_context.logging_module.exception("~~ Thread failed ~~")
            self.build_context.tests_data_keeper.errors = True
        finally:
            self.build_context.logging_module.execute_logs()

# ============================================== Command logic ============================================ #

def run_playbook_flow_test_pytest(
        playbook_flow_test_directory: Path,
        xsiam_client: XsiamApiClient,
        durations: int = 5) -> Tuple[bool, Union[TestSuite, None]]:
    """Runs a playbook flow test

        Args:
            playbook_flow_test_directory (Path): Path to the playbook flow test directory.
            durations (int): Number of slow tests to show durations for.
            xsiam_client (XsiamApiClient): The XSIAM client used to do API calls to the tenant.
    """
    # Creating an instance of your results collector
    playbook_flow_test_suite = TestSuite(f"Playbook Flow Test")
    playbook_flow_test_suite.add_property(
        "file_name", str(playbook_flow_test_directory)
    )

    # # Configure pytest arguments
    # os.environ["CLIENT_CONF"] = (f"base_url={str(xsiam_client.base_url)},"
    #                              f"api_key={xsiam_client.api_key},"
    #                              f"auth_id={xsiam_client.auth_id}")

    pytest_args = [
        "-v",
        f"--client_conf=base_url={str(xsiam_client.base_url)},api_key={xsiam_client.api_key},auth_id={xsiam_client.auth_id}",
        str(playbook_flow_test_directory),
        f"--durations={str(durations)}",
        "--log-cli-level=CRITICAL"
    ]

    logger.info(f"Runnig pytest for file {playbook_flow_test_directory}")

    # Running pytest
    result_capture = TestResultCapture(playbook_flow_test_suite)
    status_code = pytest.main(pytest_args, plugins=[result_capture])

    if status_code == pytest.ExitCode.OK:
        logger.info(f"<green>Pytest run tests in {playbook_flow_test_directory} successfully</green>")
        return True, playbook_flow_test_suite
    else:
        logger.error(
            f"<red>Pytest failed with statsu {status_code}</red>",
        )
        return False, playbook_flow_test_suite


@app.command(
    no_args_is_help=True,
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": ["-h", "--help"],
    },
)
def test_playbook_flow_test(
        ctx: typer.Context,
        inputs: List[Path] = typer.Argument(
            None,
            exists=True,
            dir_okay=True,
            resolve_path=True,
            show_default=False,
            help="The path to a directory of a playbook flow tests. May pass multiple paths to test multiple playbook flow tests.",
        ),
        xsiam_url: Optional[str] = typer.Option(
            None,
            envvar="DEMISTO_BASE_URL",
            help="The base url to the xsiam tenant.",
            rich_help_panel="XSIAM Tenant Configuration",
            show_default=False,
            callback=tenant_config_cb,
        ),
        api_key: Optional[str] = typer.Option(
            None,
            envvar="DEMISTO_API_KEY",
            help="The api key for the xsiam tenant.",
            rich_help_panel="XSIAM Tenant Configuration",
            show_default=False,
            callback=tenant_config_cb,
        ),
        auth_id: Optional[str] = typer.Option(
            None,
            envvar="XSIAM_AUTH_ID",
            help="The auth id associated with the xsiam api key being used.",
            rich_help_panel="XSIAM Tenant Configuration",
            show_default=False,
            callback=tenant_config_cb,
        ),
        xsiam_token: Optional[str] = typer.Option(
            None,
            envvar="XSIAM_TOKEN",
            help="The token used to push event logs to XSIAM",
            rich_help_panel="XSIAM Tenant Configuration",
            show_default=False,
        ),
        collector_token: Optional[str] = typer.Option(
            None,
            envvar="XSIAM_COLLECTOR_TOKEN",
            help="The token used to push event logs to a custom HTTP Collector",
            rich_help_panel="XSIAM Tenant Configuration",
            show_default=False,
            callback=logs_token_cb,
        ),
        output_junit_file: Optional[Path] = typer.Option(
            None, "-jp", "--junit-path", help="Path to the output JUnit XML file."
        ),
        sleep_interval: int = typer.Option(
            XSIAM_CLIENT_SLEEP_INTERVAL,
            "-si",
            "--sleep_interval",
            min=0,
            show_default=True,
            help="The number of seconds to wait between requests to the server.",
        ),
        retry_attempts: int = typer.Option(
            XSIAM_CLIENT_RETRY_ATTEMPTS,
            "-ra",
            "--retry_attempts",
            min=0,
            show_default=True,
            help="The number of times to retry the request against the server.",
        ),
        service_account: Optional[str] = typer.Option(
            None,
            "-sa",
            "--service_account",
            envvar="GCP_SERVICE_ACCOUNT",
            help="GCP service account.",
            show_default=False,
        ),
        cloud_servers_path: str = typer.Option(
            "",
            "-csp",
            "--cloud_servers_path",
            help="Path to secret cloud server metadata file.",
            show_default=False,
        ),
        cloud_servers_api_keys: str = typer.Option(
            "",
            "-csak",
            "--cloud_servers_api_keys",
            help="Path to file with cloud Servers api keys.",
            show_default=False,
        ),
        machine_assignment: str = typer.Option(
            "",
            "-ma",
            "--machine_assignment",
            help="the path to the machine assignment file.",
            show_default=False,
        ),
        branch_name: str = typer.Option(
            "master",
            "-bn",
            "--branch_name",
            help="The current content branch name.",
            show_default=True,
        ),
        build_number: str = typer.Option(
            "",
            "-bn",
            "--build_number",
            help="The build number.",
            show_default=True,
        ),
        nightly: str = typer.Option(
            "false",
            "--nightly",
            "-n",
            help="Whether the command is being run in nightly mode.",
        ),
        artifacts_bucket: str = typer.Option(
            None,
            "-ab",
            "--artifacts_bucket",
            help="The artifacts bucket name to upload the results to",
            show_default=False,
        ),
        console_log_threshold: str = typer.Option(
            "INFO",
            "-clt",
            "--console-log-threshold",
            help="Minimum logging threshold for the console logger.",
        ),
        file_log_threshold: str = typer.Option(
            "DEBUG",
            "-flt",
            "--file-log-threshold",
            help="Minimum logging threshold for the file logger.",
        ),
        log_file_path: Optional[str] = typer.Option(
            None,
            "-lp",
            "--log-file-path",
            help="Path to save log files onto.",
        ),
):
    """
    Test a playbook flow test against an XSIAM tenant
    """
    logging_setup(
        console_threshold=console_log_threshold,  # type: ignore[arg-type]
        file_threshold=file_log_threshold,  # type: ignore[arg-type]
        path=log_file_path,
        calling_function=__name__,
    )
    handle_deprecated_args(ctx.args)

    logging_module = ParallelLoggingManager(
        "playbook_flow_test.log", real_time_logs_only=not nightly
    )

    if machine_assignment:
        if inputs:
            logger.error(
                "You cannot pass both machine_assignment and inputs arguments."
            )
            raise typer.Exit(1)
        if xsiam_url:
            logger.error(
                "You cannot pass both machine_assignment and xsiam_url arguments."
            )
            raise typer.Exit(1)

    start_time = get_utc_now()
    is_nightly = string_to_bool(nightly)
    build_context = BuildContext(
        nightly=is_nightly,
        build_number=build_number,
        branch_name=branch_name,
        retry_attempts=retry_attempts,
        sleep_interval=sleep_interval,
        logging_module=logging_module,
        cloud_servers_path=cloud_servers_path,
        cloud_servers_api_keys=cloud_servers_api_keys,
        service_account=service_account,
        artifacts_bucket=artifacts_bucket,
        machine_assignment=machine_assignment,
        ctx=ctx,
        xsiam_url=xsiam_url,
        xsiam_token=xsiam_token,
        api_key=api_key,
        auth_id=auth_id,
        collector_token=collector_token,
        inputs=inputs,
    )

    logging_module.info(
        "playbook flow tests to test:",
    )

    for build_context_server in build_context.servers:
        for playbook_flow_test_directory in build_context_server.tests:
            logging_module.info(
                f"\tmachine:{build_context_server.base_url} - "
                f"{get_relative_path_to_content(playbook_flow_test_directory)}"
            )

    threads_list = []
    for index, server in enumerate(build_context.servers, start=1):
        thread_name = f"Thread-{index} (execute_tests)"
        threads_list.append(Thread(target=server.execute_tests, name=thread_name))

    logging_module.info("Finished creating configurations, starting to run tests.")
    for thread in threads_list:
        thread.start()

    for t in threads_list:
        t.join()

    logging_module.info("Finished running tests.")

    if output_junit_file:
        logger.info(
            f"<cyan>Writing JUnit XML to {get_relative_path_to_content(output_junit_file)}</cyan>",
        )
        build_context.tests_data_keeper.test_results_xml_file.write(
            output_junit_file.as_posix(), pretty=True
        )
        if nightly:
            if service_account and artifacts_bucket:
                build_context.tests_data_keeper.upload_result_json_to_bucket(
                    XSIAM_SERVER_TYPE,
                    f"playbook_flow_test_{build_number}.xml",
                    output_junit_file,
                    logging_module,
                )
            else:
                logger.warning(
                    "<yellow>Service account or artifacts bucket not provided, skipping uploading JUnit XML to bucket</yellow>",
                )
    else:
        logger.info(
            "<cyan>No JUnit XML file path was passed - skipping writing JUnit XML</cyan>",
        )

    duration = duration_since_start_time(start_time)
    if build_context.tests_data_keeper.errors:
        logger.error(
            f"Playbook flow test: Failed, took:{duration} seconds",
        )
        raise typer.Exit(1)

    logger.success(
        f"Playbook flow test: Passed, took:{duration} seconds",
    )


if __name__ == "__main__":
    app()
