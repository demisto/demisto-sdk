import logging
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional

import click
import docker
import docker.errors
import docker.models.containers

from demisto_sdk.commands.common.constants import MDX_SERVER_DOCKER_IMAGE
from demisto_sdk.commands.common.docker_helper import (
    get_docker,
    init_global_docker_client,
)
from demisto_sdk.commands.common.errors import Errors

EXPECTED_SUCCESS_MESSAGE = "MDX server is listening on port"

DEMISTO_DEPS_DOCKER_NAME = "mdx_server"
_SERVER_SCRIPT_NAME = "mdx-parse-server.js"
_MDX_SERVER_PROCESS: Optional[subprocess.Popen] = None
_RUNNING_CONTAINER_IMAGE: Optional[docker.models.containers.Container] = None


def server_script_path():
    """The path to the script that runs the mdxserver

    Returns: Path to the script

    """
    return (
        Path(__file__).parent.parent
        / "common"
        / "markdown_server"
        / _SERVER_SCRIPT_NAME
    )


@contextmanager
def start_docker_MDX_server(
    handle_error: Optional[Callable] = None, file_path: Optional[str] = None
):
    """
        This function will start a docker container running a node server listening on port 6161.
        The container will erase itself after exit.
        If there's a running server already with the same name it will be removed before starting a new one.

    Args:
        handle_error: handle_error function
        file_path: path of the content item

    Returns:
        A context manager

    """
    logging.info("Starting docker mdx server")
    get_docker().pull_image(MDX_SERVER_DOCKER_IMAGE)
    iteration_num = 1
    while mdx_container := init_global_docker_client().containers.list(
        filters={"name": DEMISTO_DEPS_DOCKER_NAME}
    ):
        print(f"Found the following container(s): {mdx_container}")
        print(f"{iteration_num=} when trying to remove {mdx_container}")
        remove_container(mdx_container[0])
        iteration_num += 1
    try:
        container: docker.models.containers.Container = get_docker().create_container(
            name=DEMISTO_DEPS_DOCKER_NAME,
            image=MDX_SERVER_DOCKER_IMAGE,
            auto_remove=True,
            ports={"6161/tcp": 6161},
        )
    except Exception as error:
        print(
            f"Error occurred when trying to create {DEMISTO_DEPS_DOCKER_NAME} container, {error=}"
        )
        print(
            f"all available containers: {[container.name for container in init_global_docker_client().containers.list(all=True)]}"
        )
        raise error

    container.start()
    try:
        line = str(next(container.logs(stream=True)).decode("utf-8"))

        raised_successfully = EXPECTED_SUCCESS_MESSAGE in line
    except docker.errors.NotFound:
        raised_successfully = False
        line = "Docker crashed on startup. To inspect, run the container in the same manner without the --rm flag."

    if not raised_successfully:
        try:
            remove_container(container)
            logging.error("Docker for MDX server was not started correctly")
            logging.error(f'docker logs:\n{container.logs().decode("utf-8")}')
        except docker.errors.NotFound:
            click.secho(line)

        error_message = Errors.error_starting_docker_mdx_server(line=line)

        if handle_error and file_path:
            if handle_error(error_message, file_path=file_path):
                return False
        else:
            raise Exception(error_message)
    else:
        click.secho("Successfully started node server in docker")

    try:
        yield True
    finally:
        remove_container(container)


def remove_container(container):
    if container:
        print("stopping and removing mdx server")
        print(f"Removing container {container.name}")
        container.remove(force=True)
        print(f"Successfully removed container {container.name}")


@contextmanager
def start_local_MDX_server(
    handle_error: Optional[Callable] = None, file_path: Optional[str] = None
):
    """
        This function will start a node server on the local machine and listen on port 6161
    Args:
        handle_error: handle_error function
        file_path: path of the content item

    Returns:
        A context manager

    """
    click.secho("Starting local mdx server")

    logging.debug(subprocess.check_output(["npm", "list", "--json"]))
    process = subprocess.Popen(
        ["node", str(server_script_path())], stdout=subprocess.PIPE, text=True
    )
    line = process.stdout.readline()  # type: ignore
    if EXPECTED_SUCCESS_MESSAGE not in line:
        logging.error(f"MDX local server couldnt be started: {line}")
        terminate_process(process)
        error_message, error_code = Errors.error_starting_mdx_server(line=line)
        if handle_error and file_path:
            if handle_error(error_message, error_code, file_path=file_path):
                return False
        else:
            raise Exception(error_message)

    try:
        yield True
    finally:
        terminate_process(process)


def terminate_process(process):
    if process:
        click.secho("Stopping local mdx server")
        process.terminate()
