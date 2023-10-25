import os
import traceback
from pathlib import Path
from typing import List

from junitparser import JUnitXml

import demisto_sdk.commands.common.docker_helper as docker_helper
from demisto_sdk.commands.common.constants import TYPE_JS
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.lint.helpers import stream_docker_container_output

DOCKER_PYTHONPATH = [
    f"/content/{path.relative_to(CONTENT_PATH)}"
    for path in PYTHONPATH
    if path.is_relative_to(CONTENT_PATH)
]

DEFAULT_DOCKER_IMAGE = "demisto/python:1.3-alpine"

PYTEST_COMMAND = "python -m pytest . -v --rootdir=/content --override-ini='asyncio_mode=auto' --override-ini='junit_family=xunit1' --junitxml=.report_pytest.xml --cov-report= --cov=."
PWSH_COMMAND = "pwsh -Command Invoke-Pester -Configuration '@{Run=@{Exit=$true}; Output=@{Verbosity=\"Detailed\"}}'"
TEST_REQUIREMENTS_DIR = Path(__file__).parent.parent / "lint" / "resources"


NO_TESTS_COLLECTED = 5


def unit_test_runner(file_paths: List[Path], verbose: bool = False) -> int:
    docker_client = docker_helper.init_global_docker_client()
    docker_base = docker_helper.get_docker()
    exit_code = 0
    for filename in file_paths:
        integration_script = BaseContent.from_path(Path(filename))
        if not isinstance(integration_script, IntegrationScript):
            logger.warning(f"Skipping {filename} as it is not a content item.")
            continue

        if integration_script.type == TYPE_JS:
            logger.info(
                f"Skipping tests for '{integration_script.name}' since it is a JavaScript integration/script"
            )
            continue

        relative_integration_script_path = integration_script.path.relative_to(
            CONTENT_PATH
        )

        if (test_data_dir := (integration_script.path.parent / "test_data")).exists():
            (test_data_dir / "__init__.py").touch()

        working_dir = f"/content/{relative_integration_script_path.parent}"
        docker_images = [integration_script.docker_image or DEFAULT_DOCKER_IMAGE]
        if os.getenv("CONTENT_GITLAB_CI"):
            docker_images = [
                f"docker-io.art.code.pan.run/{docker_image}"
                for docker_image in docker_images
            ]
        logger.debug(f"{docker_images=}")
        for docker_image in docker_images:
            try:
                test_docker_image, errors = docker_base.pull_or_create_test_image(
                    docker_image,
                    integration_script.type,
                    log_prompt=f"Unit test {integration_script.name}",
                )
                if errors:
                    raise RuntimeError(f"Creating docker failed due to {errors}")
                (integration_script.path.parent / "conftest.py").unlink(missing_ok=True)
                (integration_script.path.parent / "conftest.py").symlink_to(
                    (
                        CONTENT_PATH
                        / "Tests"
                        / "scripts"
                        / "dev_envs"
                        / "pytest"
                        / "conftest.py"
                    )
                )

                logger.info(
                    f"Running test for {relative_integration_script_path} using {docker_image=} with {test_docker_image=}"
                )
                container = docker_client.containers.run(
                    image=test_docker_image,
                    environment={
                        "PYTHONPATH": ":".join(DOCKER_PYTHONPATH),
                        "REQUESTS_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                    volumes=[
                        f"{CONTENT_PATH}:/content",
                    ],
                    command=PWSH_COMMAND
                    if integration_script.type == "powershell"
                    else [PYTEST_COMMAND],
                    user=f"{os.getuid()}:{os.getgid()}",
                    working_dir=working_dir,
                    detach=True,
                )
                logger.debug(f"Running test in container {container.id}")
                stream_docker_container_output(
                    container.logs(stream=True),
                    logger.info if verbose else logger.debug,
                )
                # wait for container to finish
                if status_code := container.wait()["StatusCode"]:
                    if status_code == NO_TESTS_COLLECTED:
                        logger.warning(
                            f"No test are collected for {relative_integration_script_path} using {docker_image}."
                        )
                        continue
                    if not (
                        integration_script.path.parent / ".report_pytest.xml"
                    ).exists():
                        raise Exception(
                            f"No pytest report found in {relative_integration_script_path.parent}. Logs: {container.logs()}"
                        )
                    test_failed = False
                    for suite in JUnitXml.fromfile(
                        integration_script.path.parent / ".report_pytest.xml"
                    ):
                        for case in suite:
                            if not case.is_passed:
                                logger.error(
                                    f"Test for {integration_script.object_id} failed in {case.name} with error {case.result[0].message}: {case.result[0].text}"
                                )
                                test_failed = True
                    if not test_failed:
                        logger.error(
                            f"Error running unit tests for {relative_integration_script_path} using {docker_image=}. Container reports  {status_code=}, logs: {container.logs()}"
                        )
                    exit_code = 1
                else:
                    logger.info(
                        f"[green]All tests passed for {relative_integration_script_path} in {docker_image}[/green]"
                    )
                container.remove(force=True)
            except Exception as e:
                logger.error(
                    f"Failed to run test for {filename} in {docker_image}: {e}"
                )
                traceback.print_exc()
                exit_code = 1
    return exit_code
