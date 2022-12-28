import logging
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional

import docker
import docker.errors
import docker.models.containers

from demisto_sdk.commands.common.constants import DEPENDENCIES_DOCKER
from demisto_sdk.commands.common.docker_helper import (
    get_docker,
    init_global_docker_client,
)
from demisto_sdk.commands.common.errors import Errors

EXPECTED_SUCCESS_MESSAGE = "MDX server is listening on port"

DEMISTO_DEPS_DOCKER_NAME = "demisto-dependencies"
_SERVER_SCRIPT_NAME = "mdx-parse-server.js"
_MDX_SERVER_PROCESS: Optional[subprocess.Popen] = None
_RUNNING_CONTAINER_IMAGE: Optional[docker.models.containers.Container] = None


def server_script_path():
    """The path to the script that runs the mdxserver

    Returns: Path to the script

    """
    return Path(__file__).parent.parent / "common" / _SERVER_SCRIPT_NAME


@contextmanager
def start_docker_MDX_server(
    handle_error: Optional[Callable] = None, file_path: Optional[str] = None
):
    """
        This function will start a docker container running a node server listening on port 6161.
        The container will erase itself after exit.
        If there's a running server already with the same name it will be stopped before starting a new one.

    Args:
        handle_error: handle_error function
        file_path: path of the content item

    Returns:
        A context manager

    """
    logging.info("Starting docker mdx server")
    get_docker().pull_image(DEPENDENCIES_DOCKER)
    if running_container := init_global_docker_client().containers.list(
        filters={"name": DEMISTO_DEPS_DOCKER_NAME}
    ):
        running_container[0].stop()
    location_in_docker = f"/content/{_SERVER_SCRIPT_NAME}"
    container: docker.models.containers.Container = get_docker().create_container(
        name=DEMISTO_DEPS_DOCKER_NAME,
        image=DEPENDENCIES_DOCKER,
        command=["node", location_in_docker],
        user=f"{os.getuid()}:4000",
        files_to_push=[(server_script_path(), location_in_docker)],
        auto_remove=True,
        ports={"6161/tcp": 6161},
    )
    container.start()
    if EXPECTED_SUCCESS_MESSAGE not in (
        line := (str(next(container.logs(stream=True)).decode("utf-8")))
    ):
        stop_docker_container(container)
        logging.error("Docker for MDX server was not started correctly")
        logging.error(f'docker logs:\n{container.logs().decode("utf-8")}')
        error_message, error_code = Errors.error_starting_docker_mdx_server(line=line)
        if handle_error and file_path:
            if handle_error(error_message, error_code, file_path=file_path):
                return False
        else:
            raise Exception(error_message)

    try:
        yield True
    finally:
        stop_docker_container(container)


def stop_docker_container(container):
    if container:
        logging.info("Stopping mdx docker server")
        container.stop()  # type: ignore


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
        process.terminate()
