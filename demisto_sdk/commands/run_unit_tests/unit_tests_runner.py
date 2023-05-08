import os
import shutil
import sqlite3
import tempfile
import traceback
from pathlib import Path
from typing import List

import coverage
from junitparser import JUnitXml

import demisto_sdk.commands.common.docker_helper as docker_helper
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.coverage_analyze.helpers import coverage_files
from demisto_sdk.commands.lint.helpers import stream_docker_container_output

DOCKER_PYTHONPATH = [
    f"/content/{path.relative_to(CONTENT_PATH)}"
    for path in PYTHONPATH
    if path.is_relative_to(CONTENT_PATH)
]

DEFAULT_DOCKER_IMAGE = "demisto/python:1.3-alpine"

PYTEST_RUNNER = f"{(Path(__file__).parent / 'pytest_runner.sh')}"
POWERSHELL_RUNNER = f"{(Path(__file__).parent / 'pwsh_test_runner.sh')}"


def fix_coverage_report_path(code_directory: Path):
    """

    Args:
        code_directory: The integration script (absolute file).

    Notes:
        the .coverage files contain all the files list with their absolute path.
        but our tests (pytest step) are running inside a docker container.
        so we have to change the path to the correct one.
    """
    coverage_file = code_directory / ".coverage"
    if not coverage_file.exists():
        logger.debug(
            f"Skipping {code_directory} as it does not contain a coverage report."
        )
        return
    logger.debug(f"Editing coverage report for {coverage_file}")
    with tempfile.NamedTemporaryFile() as temp_file:
        # we use a tempfile because the original file could be readonly, this way we assure we can edit it.
        shutil.copy(coverage_file, temp_file.name)
        with sqlite3.connect(temp_file.name) as sql_connection:
            cursor = sql_connection.cursor()
            files = cursor.execute("SELECT * FROM file").fetchall()
            for id_, file in files:
                file_name = Path(file).name
                cursor.execute(
                    "UPDATE file SET path = ? WHERE id = ?",
                    (str(code_directory / file_name), id_),
                )
            sql_connection.commit()
            logger.debug("Done editing coverage report")
        coverage_file.unlink()
        shutil.copy(temp_file.name, coverage_file)


def unit_test_runner(file_paths: List[Path], verbose: bool = False) -> int:
    docker_client = docker_helper.init_global_docker_client()

    exit_code = 0
    for filename in file_paths:
        integration_script = BaseContent.from_path(Path(filename))
        if not isinstance(integration_script, IntegrationScript):
            logger.warning(f"Skipping {filename} as it is not a content item.")
            continue

        if (test_data_dir := (integration_script.path / "test_data")).exists():
            (test_data_dir / "__init__.py").touch()

        working_dir = (
            f"/content/{integration_script.path.parent.relative_to(CONTENT_PATH)}"
        )
        runner = (
            POWERSHELL_RUNNER
            if integration_script.type == "powershell"
            else PYTEST_RUNNER
        )
        shutil.copy(runner, integration_script.path.parent / "test_runner.sh")
        docker_images = [integration_script.docker_image or DEFAULT_DOCKER_IMAGE]
        if os.getenv("GITLAB_CI"):
            docker_images = [
                f"docker-io.art.code.pan.run/{docker_image}"
                for docker_image in docker_images
            ]
        logger.debug(f"{docker_images=}")
        for docker_image in docker_images:
            logger.info(f"Running test for {filename} using {docker_image=}")
            try:
                docker_client.images.pull(docker_image)
                shutil.copy(
                    Path(__file__).parent / ".pytest.ini",
                    integration_script.path.parent / ".pytest.ini",
                )
                shutil.copy(
                    CONTENT_PATH
                    / "Tests"
                    / "scripts"
                    / "dev_envs"
                    / "pytest"
                    / "conftest.py",
                    integration_script.path.parent / "conftest.py",
                )
                container = docker_client.containers.run(
                    image=docker_image,
                    environment={
                        "PYTHONPATH": ":".join(DOCKER_PYTHONPATH),
                        "REQUESTS_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                    volumes=[
                        f"{CONTENT_PATH}:/content",
                        "/etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt",
                        "/etc/pip.conf:/etc/pip.conf",
                    ],
                    command="sh test_runner.sh",
                    working_dir=working_dir,
                    detach=True,
                )
                logger.debug(f"Running test in container {container.id}")
                stream_docker_container_output(
                    container.logs(stream=True),
                    logger.info if verbose else logger.debug,
                )
                # wait for container to finish
                if container.wait()["StatusCode"]:
                    if not (
                        integration_script.path.parent / ".report_pytest.xml"
                    ).exists():
                        raise Exception(
                            f"No pytest report found in {integration_script.path.parent}. Logs: {container.logs()}"
                        )
                    for suite in JUnitXml.fromfile(
                        integration_script.path.parent / ".report_pytest.xml"
                    ):
                        for case in suite:
                            if not case.is_passed:
                                logger.error(
                                    f"Test for {integration_script.object_id} failed in {case.name} with error {case.result[0].message}: {case.result[0].text}"
                                )
                    exit_code = 1
                else:
                    logger.info(f"All tests passed for {filename} in {docker_image}")
                container.remove(force=True)
                fix_coverage_report_path(integration_script.path.parent)
            except Exception as e:
                logger.error(
                    f"Failed to run test for {filename} in {docker_image}: {e}"
                )
                traceback.print_exc()
                exit_code = 1
            finally:
                # remove pytest.ini no matter the results
                shutil.rmtree(
                    integration_script.path.parent / ".pytest.ini", ignore_errors=True
                )
    cov = coverage.Coverage(data_file=CONTENT_PATH / ".coverage")
    cov.combine(coverage_files())
    cov.xml_report(outfile=str(CONTENT_PATH / "coverage.xml"))
    logger.info(f"Coverage report saved to {CONTENT_PATH / 'coverage.xml'}")
    return exit_code
