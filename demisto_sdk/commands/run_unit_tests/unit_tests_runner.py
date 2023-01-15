import logging
import os
from pathlib import Path
import shutil
from typing import List
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
import demisto_sdk.commands.common.docker_helper as docker_helper
from demisto_sdk.commands.lint.helpers import stream_docker_container_output


logger = logging.getLogger("demisto-sdk")


DOCKER_PYTHONPATH = [f"/content/{path.relative_to(CONTENT_PATH)}" for path in PYTHONPATH]

DEFAULT_DOCKER_IMAGE = "demisto/python:1.3-alpine"

def unit_test_runner(file_paths: List[Path]) -> int:
    docker_client = docker_helper.init_global_docker_client()

    ret_val = 0
    for filename in file_paths:
        integration_script = BaseContent.from_path(Path(filename))
        if not isinstance(integration_script, IntegrationScript):
            print(f"Skipping {filename} as it is not a content item.")
            continue
        working_dir = f"/content/{integration_script.path.parent.relative_to(CONTENT_PATH)}"
        docker_image = integration_script.docker_image or DEFAULT_DOCKER_IMAGE
        if os.getenv("GITLAB_CI"):
            docker_image = f"docker-io.art.code.pan.run/{docker_image}"
        logger.info(f"Running test for {filename} with docker image {docker_image}")
        try:
            docker_client.images.pull(docker_image)
            shutil.copy(Path(__file__).parent / ".pytest.ini", integration_script.path.parent / '.pytest.ini')
            container = docker_client.containers.run(
                image=docker_image,
                environment={
                    "PYTHONPATH": ":".join(DOCKER_PYTHONPATH),
                    "REQUESTS_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt",
                },
                volumes=[
                    f"{CONTENT_PATH}:/content",
                    f"{(Path(__file__).parent / 'pytest_runner.sh')}:/runner.sh",
                    "/etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt",
                    "/etc/pip.conf:/etc/pip.conf",
                    
                ],
                command="sh /runner.sh",
                working_dir=working_dir,
                detach=True,
            )
            stream_docker_container_output(container.logs(stream=True), logger.debug)
            # wait for container to finish
            container_exit_code = container.wait()["StatusCode"]
            if container_exit_code:
                logger.error(f"Some tests failed. Run with -v to see full results. Exit code: {container_exit_code}")
                ret_val = 1
            else:
                logger.info(f"All tests passed for {filename}")
            # remove file
            shutil.rmtree(integration_script.path.parent / '.pytest.ini', ignore_errors=True)
            container.remove(force=True)
        except Exception as e:
            raise Exception(f"Failed to run test for {filename}: {e}")
    return ret_val
