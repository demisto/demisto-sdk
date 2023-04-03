import logging
import os
import shutil
import traceback
from pathlib import Path
from typing import List

from junitparser import JUnitXml

import demisto_sdk.commands.common.docker_helper as docker_helper
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.lint.helpers import stream_docker_container_output

logger = logging.getLogger("demisto-sdk")


DOCKER_PYTHONPATH = [
    f"/content/{path.relative_to(CONTENT_PATH)}"
    for path in PYTHONPATH
    if path.is_relative_to(CONTENT_PATH)
]

DEFAULT_DOCKER_IMAGE = "demisto/python:1.3-alpine"

PYTEST_RUNNER = f"{(Path(__file__).parent / 'pytest_runner.sh')}"
POWERSHELL_RUNNER = f"{(Path(__file__).parent / 'pwsh_test_runner.sh')}"


def unit_test_runner(file_paths: List[Path], verbose: bool = False) -> int:
    docker_client = docker_helper.init_global_docker_client()

    exit_code = 0
    for filename in file_paths:
        integration_script = BaseContent.from_path(Path(filename))
        if not isinstance(integration_script, IntegrationScript):
            logger.warning(f"Skipping {filename} as it is not a content item.")
            continue
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
                container_exit_code = container.wait()["StatusCode"]
                if container_exit_code:
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
    return exit_code
