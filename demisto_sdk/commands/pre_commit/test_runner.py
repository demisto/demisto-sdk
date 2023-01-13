import argparse
import logging
import os
from pathlib import Path
from typing import Optional, Sequence
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logging_setup
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
import demisto_sdk.commands.common.docker_helper as docker_helper
from demisto_sdk.commands.lint.helpers import stream_docker_container_output

logging_setup(1)

logger = logging.getLogger("demisto-sdk")

PYTHONPATH = [
    Path(CONTENT_PATH),
    Path(CONTENT_PATH / "Packs" / "Base" / "Scripts" / "CommonServerPython"),
    Path(CONTENT_PATH / "Tests" / "demistomock"),
]

PYTHONPATH.extend(dir for dir in Path(CONTENT_PATH / "Packs" / "ApiModules" / "Scripts").iterdir())

PYTHONPATH = [f"/content/{path.relative_to(CONTENT_PATH)}" for path in PYTHONPATH]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)
    print(f"{os.getenv('DOCKER_HOST')=}")
    docker_client = docker_helper.init_global_docker_client()

    ret_val = 0
    for filename in args.filenames:
        integration_script = BaseContent.from_path(Path(filename))
        if not isinstance(integration_script, IntegrationScript):
            print(f"Skipping {filename} as it is not a content item.")
            continue
        working_dir = f"/content/{integration_script.path.parent.relative_to(CONTENT_PATH)}"
        docker_image = integration_script.docker_image
        if os.getenv("GITLAB_CI"):
            docker_image = f"docker-io.art.code.pan.run/{docker_image}"
        logger.info(f"Running test for {filename} with docker image {docker_image}")
        try:
            docker_client.images.pull(docker_image)
            container = docker_client.containers.run(
                image=docker_image,
                environment={
                    "PYTHONPATH": ":".join(PYTHONPATH),
                    "REQUESTS_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt",
                    "GITHUB_ACTIONS": os.getenv("GITHUB_ACTIONS"),
                    "PYTEST_RUN_PATH": working_dir,
                },
                volumes=[
                    f"{CONTENT_PATH}:/content",
                    f"{(Path(__file__).parent / 'runner.sh')}:/runner.sh",
                    "/etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt",
                    "/etc/pip.conf:/etc/pip.conf",
                ],
                command="sh /runner.sh",
                working_dir=working_dir,
                detach=True,
                restart_policy={"Name": "on-failure", "MaximumRetryCount": 3},
            )
            stream_docker_container_output(container.logs(stream=True))
            # wait for container to finish
            container_exit_code = container.attrs["State"]["ExitCode"]
            container.remove(force=True)
            if container_exit_code:
                print(f"Some test failed Test failed. Exit code: {container_exit_code}")
                ret_val = 1
        except Exception as e:
            logger.error(f"Failed to run test for {filename}: {e}")
            raise Exception(f"Failed to run test for {filename}: {e}")
            logger.info(container.logs())
            ret_val = 1
    return ret_val


if __name__ == "__main__":
    raise SystemExit(main())
