import logging  # noqa: TID251 # specific case, passed as argument to 3rd party
import os
import re
import shutil
import subprocess
from pathlib import Path
from threading import Thread
from typing import Any, List, Optional, Tuple, Union

import demisto_client
import pytest
import typer
from google.cloud import storage  # type: ignore[attr-defined]
from junitparser import JUnitXml, TestCase, TestSuite
from junitparser.junitparser import Failure, Skipped

from demisto_sdk.commands.common.clients import get_client_from_server_type
from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import XsoarClient
from demisto_sdk.commands.common.constants import (
    TEST_USE_CASES,
    XSIAM_SERVER_TYPE,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
)
from demisto_sdk.commands.common.tools import (
    get_json_file,
    get_pack_name,
    string_to_bool,
)
from demisto_sdk.commands.test_content.ParallelLoggingManager import (
    ParallelLoggingManager,
)
from demisto_sdk.commands.test_content.tools import (
    duration_since_start_time,
    get_relative_path_to_content,
    get_ui_url,
    get_utc_now,
)

CI_PIPELINE_ID = os.environ.get("CI_PIPELINE_ID")

app = typer.Typer()


def copy_conftest(test_dir):
    """
    copy content's conftest.py file into the use case directory in order to be able to pass new custom
     pytest argument (client_conf)
    """
    source_conftest = Path(CONTENT_PATH) / "Tests/scripts/dev_envs/pytest/conftest.py"
    dest_conftest = test_dir / "conftest.py"

    shutil.copy(source_conftest, dest_conftest)


def run_command(command):
    """Run a shell command and capture the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        logging.error(
            f"Error executing command: {e}\nCommand: {command}\nOutput: {e.output.decode('utf-8')}\nError: {e.stderr.decode('utf-8')}"
        )
        return None


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
                error_text = self._sanitize_sensitive_data(
                    report.longreprtext if report.longrepr else "Test failed"
                )
                failure = Failure(error_text)
                test_case.result = failure
                self.junit_testsuite.add_testcase(test_case)
            elif report.outcome == "skipped":
                skipped = Skipped("Test skipped")
                test_case.result = skipped
                self.junit_testsuite.add_testcase(test_case)

    def _sanitize_sensitive_data(self, text):
        """
        Remove or redact sensitive data from the given text.

        Args:
            text (str): The text to sanitize.

        Returns:
            str: The sanitized text with sensitive data removed or redacted.
        """

        pattern = r"('Authorization':\s*')([^']+)(')"
        # Replace the sensitive part with '[REDACTED]'
        sanitized_text = re.sub(pattern, r"\1[REDACTED]\3", text)

        return sanitized_text


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
        logging_module.debug("Start uploading test use case results file to bucket")

        storage_client = storage.Client.from_service_account_json(self.service_account)
        storage_bucket = storage_client.bucket(self.artifacts_bucket)

        blob = storage_bucket.blob(
            f"content-test-use-case/{repository_name}/{file_name}"
        )
        blob.upload_from_filename(
            original_file_path.as_posix(),
            content_type="application/xml",
        )

        logging_module.debug("Finished uploading test use case results file to bucket")


class BuildContext:
    def __init__(
        self,
        nightly: bool,
        build_number: Optional[str],
        logging_module: ParallelLoggingManager,
        cloud_servers_path: str,
        cloud_servers_api_keys: str,
        service_account: Optional[str],
        artifacts_bucket: Optional[str],
        cloud_url: Optional[str],
        api_key: Optional[str],
        auth_id: Optional[str],
        inputs: Optional[List[Path]],
        machine_assignment: str,
        project_id: str,
        ctx: typer.Context,
    ):
        self.logging_module: ParallelLoggingManager = logging_module
        self.ctx = ctx

        # --------------------------- overall build configuration -------------------------------
        self.is_nightly = nightly
        self.build_number = build_number
        self.project_id = project_id

        # -------------------------- Manual run on a single instance --------------------------
        self.cloud_url = cloud_url
        self.api_key = api_key
        self.auth_id = auth_id
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

    def create_servers(self):
        """
        Create servers object based on build type.
        """
        # If cloud_url is provided we assume it's a run on a single server.
        if self.cloud_url:
            return [
                CloudServerContext(
                    self,
                    base_url=self.cloud_url,
                    api_key=self.api_key,  # type: ignore[arg-type]
                    auth_id=self.auth_id,  # type: ignore[arg-type]
                    ui_url=get_ui_url(self.cloud_url),
                    tests=[Path(test) for test in self.inputs] if self.inputs else [],
                )
            ]
        servers_list = []
        for machine, assignment in self.machine_assignment_json.items():
            tests = [
                Path(test)
                for test in assignment.get("tests", {}).get(TEST_USE_CASES, [])
            ]
            if not tests:
                logger.info(f"No test use cases found for machine {machine}")
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
        ui_url: str,
        tests: List[Path],
    ):
        self.build_context = build_context
        self.client = None
        self.base_url = base_url
        self.api_key = api_key
        self.auth_id = auth_id
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

            cloud_client = get_client_from_server_type(
                base_url=self.base_url, api_key=self.api_key, auth_id=self.auth_id
            )

            for i, test_use_case_directory in enumerate(self.tests, start=1):
                logger.info(
                    f"<cyan>[{i}/{len(self.tests)}] test use cases: {get_relative_path_to_content(test_use_case_directory)}</cyan>",
                )

                success, test_use_case_test_suite = run_test_use_case_pytest(
                    test_use_case_directory,
                    cloud_client=cloud_client,
                    project_id=self.build_context.project_id,
                )

                if success:
                    logger.info(
                        f"<green>Test use case {get_relative_path_to_content(test_use_case_directory)} passed</green>",
                    )
                else:
                    self.build_context.tests_data_keeper.errors = True
                    logger.error(
                        f"<red>Test use case {get_relative_path_to_content(test_use_case_directory)} failed</red>",
                    )
                if test_use_case_test_suite:
                    test_use_case_test_suite.add_property(
                        "start_time",
                        start_time,  # type:ignore[arg-type]
                    )
                    self.build_context.tests_data_keeper.test_results_xml_file.add_testsuite(
                        test_use_case_test_suite
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


def run_test_use_case_pytest(
    test_use_case_directory: Path,
    cloud_client: XsoarClient,
    durations: int = 5,
    project_id: str = None,
) -> Tuple[bool, Union[TestSuite, None]]:
    """Runs a test use case

    Args:
        test_use_case_directory (Path): Path to the test use case directory.
        durations (int): Number of slow tests to show durations for.
        cloud_client (XsoarClient): The XSIAM client used to do API calls to the tenant.
    """
    # Creating an instance of your results collector
    test_use_case_suite = TestSuite("Test Use Case")
    containing_pack = get_pack_name(test_use_case_directory)

    test_use_case_suite.add_property("file_name", str(test_use_case_directory.name))
    test_use_case_suite.add_property("pack_id", containing_pack)
    if CI_PIPELINE_ID:
        test_use_case_suite.add_property("ci_pipeline_id", CI_PIPELINE_ID)

    test_dir = test_use_case_directory.parent
    copy_conftest(test_dir)

    logger.debug(f"before sending pytest {str(cloud_client.base_url)}")
    pytest_args = [
        f"--client_conf=base_url={str(cloud_client.server_config.base_api_url)},"
        f"api_key={cloud_client.server_config.api_key.get_secret_value()},"
        f"auth_id={cloud_client.server_config.auth_id},"
        f"project_id={project_id}",
        str(test_use_case_directory),
        f"--durations={str(durations)}",
        "--log-cli-level=CRITICAL",
    ]

    logger.info(f"Running pytest for file {test_use_case_directory}")

    # Running pytest
    result_capture = TestResultCapture(test_use_case_suite)
    status_code = pytest.main(pytest_args, plugins=[result_capture])

    if status_code == pytest.ExitCode.OK:
        logger.info(
            f"<green>Pytest run tests in {test_use_case_directory} successfully</green>"
        )
        return True, test_use_case_suite
    elif status_code == pytest.ExitCode.TESTS_FAILED:
        logger.error(
            f"<red>Pytest failed with statsu {status_code}</red>",
        )
        return False, test_use_case_suite
    else:
        raise Exception(f"Pytest failed with {status_code=}")


def run_test_use_case(
    ctx: typer.Context,
    inputs: List[Path],
    xsiam_url: Optional[str],
    api_key: Optional[str],
    auth_id: Optional[str],
    output_junit_file: Optional[Path],
    service_account: Optional[str],
    cloud_servers_path: str,
    cloud_servers_api_keys: str,
    machine_assignment: str,
    build_number: str,
    nightly: str,
    artifacts_bucket: str,
    project_id: str,
    console_log_threshold: str,
    file_log_threshold: str,
    log_file_path: Optional[str],
    **kwargs,
):
    """
    Test a test use case against an XSIAM tenant
    """
    logging_setup(
        console_threshold=console_log_threshold,  # type: ignore[arg-type]
        file_threshold=file_log_threshold,  # type: ignore[arg-type]
        path=log_file_path,
        calling_function=__name__,
    )
    handle_deprecated_args(ctx.args)

    logging_module = ParallelLoggingManager(
        "test_use_case.log", real_time_logs_only=not nightly
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
        logging_module=logging_module,
        cloud_servers_path=cloud_servers_path,
        cloud_servers_api_keys=cloud_servers_api_keys,
        service_account=service_account,
        artifacts_bucket=artifacts_bucket,
        machine_assignment=machine_assignment,
        ctx=ctx,
        cloud_url=xsiam_url,
        api_key=api_key,
        auth_id=auth_id,
        inputs=inputs,
        project_id=project_id,
    )

    logging_module.debug(
        "test use cases to test:",
    )

    for build_context_server in build_context.servers:
        for test_use_case_directory in build_context_server.tests:
            logging_module.info(
                f"\tmachine:{build_context_server.base_url} - "
                f"{get_relative_path_to_content(test_use_case_directory)}"
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
                    f"test_use_case_{build_number}.xml",
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
            f"Test use case: Failed, took:{duration} seconds",
        )
        raise typer.Exit(1)

    logger.success(
        f"Test use case: Passed, took:{duration} seconds",
    )
