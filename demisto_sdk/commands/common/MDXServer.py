import logging
import os
import subprocess
from abc import abstractmethod
from pathlib import Path
from typing import Callable, Optional

import docker
import docker.errors
import docker.models.containers

from demisto_sdk.commands.common.constants import DEPENDENCIES_DOCKER
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.lint.docker_helper import (Docker,
                                                     init_global_docker_client)

EXPECTED_SUCCESS_MESSAGE = 'MDX server is listening on port'

DEMISTO_DEPS_DOCKER_NAME = "demisto-dependencies"
_SERVER_SCRIPT_NAME = 'mdx-parse-server.js'
_MDX_SERVER_PROCESS: Optional[subprocess.Popen] = None
_RUNNING_CONTAINER_IMAGE: Optional[docker.models.containers.Container] = None


def server_script_path():
    return Path(__file__).parent.parent / 'common' / _SERVER_SCRIPT_NAME


class DockerMDXServer:
    def __init__(self, handle_error: Optional[Callable] = None, file_path: Optional[str] = None):
        self.handle_error = handle_error
        self.file_path = file_path

    def __enter__(self):
        self.started_successfully = True
        global _RUNNING_CONTAINER_IMAGE
        if not _RUNNING_CONTAINER_IMAGE:  # type: ignore
            logging.info('Starting docker mdx server')
            Docker.pull_image(DEPENDENCIES_DOCKER)
            if running_container := init_global_docker_client() \
                    .containers.list(filters={'name': DEMISTO_DEPS_DOCKER_NAME}):
                running_container[0].stop()
            location_in_docker = f'/content/{_SERVER_SCRIPT_NAME}'
            container: docker.models.containers.Container = Docker.create_container(
                name=DEMISTO_DEPS_DOCKER_NAME,
                image=DEPENDENCIES_DOCKER,
                command=['node', location_in_docker],
                user=f"{os.getuid()}:4000",
                files_to_push=[(server_script_path(), location_in_docker)],
                auto_remove=True,
                ports={'6161/tcp': ('localhost', 6161)}

            )
            self.owning_obj = True
            container.start()
            if EXPECTED_SUCCESS_MESSAGE not in (line := (str(next(container.logs(stream=True)).decode('utf-8')))):
                self.stop_docker_container()
                logging.error('Docker for MDX server was not started correctly')
                logging.error(f'docker logs:\n{container.logs().decode("utf-8")}')
                error_message, error_code = Errors.error_starting_docker_mdx_server(line=line)
                if self.handle_error and self.file_path:
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.started_successfully = False
                else:
                    raise Exception(error_message)
                return
            _RUNNING_CONTAINER_IMAGE = container
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_docker_container()

    def stop_docker_container(self):
        global _RUNNING_CONTAINER_IMAGE
        if _RUNNING_CONTAINER_IMAGE and hasattr(self, 'owning_obj'):
            logging.info('Stopping mdx docker server')
            _RUNNING_CONTAINER_IMAGE.stop()  # type: ignore
            _RUNNING_CONTAINER_IMAGE = None
        else:
            logging.info("not stop container as it wasn't started here")

    def is_started(self):
        return self.started_successfully


class LocalMDXServer:
    def __init__(self, handle_error: Optional[Callable] = None, file_path: Optional[str] = None):
        self.handle_error = handle_error
        self.file_path = file_path

    def __enter__(self):
        self.started_successfully = True
        global _MDX_SERVER_PROCESS
        if not _MDX_SERVER_PROCESS:
            _MDX_SERVER_PROCESS = subprocess.Popen(['node', str(server_script_path())],
                                                   stdout=subprocess.PIPE, text=True)
            line = _MDX_SERVER_PROCESS.stdout.readline()  # type: ignore
            if EXPECTED_SUCCESS_MESSAGE not in line:
                logging.error(f'MDX local server couldnt be started: {line}')
                self.terminate()
                error_message, error_code = Errors.error_starting_mdx_server(line=line)
                if self.handle_error and self.file_path:
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.started_successfully = False
                else:
                    raise Exception(error_message)
                return self
            else:
                self.owning_obj = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()

    def terminate(self):
        global _MDX_SERVER_PROCESS
        if _MDX_SERVER_PROCESS and hasattr(self, 'owning_obj'):
            _MDX_SERVER_PROCESS.terminate()
            _MDX_SERVER_PROCESS = None

    def is_started(self):
        return self.started_successfully
