import logging
import os
import subprocess
from abc import abstractmethod
from pathlib import Path
from typing import Optional

import docker
import docker.errors
import docker.models.containers

from demisto_sdk.commands.lint.docker_helper import (Docker,
                                                     init_global_docker_client)

DEMISTO_DEPS_DOCKER_NAME = "demisto-dependencies"
_SERVER_SCRIPT_NAME = 'mdx-parse-server.js'
_MDX_SERVER_PROCESS: Optional[subprocess.Popen] = None
_RUNNING_CONTAINER_IMAGE: Optional[docker.models.containers.Container] = None


def server_script_path():
    return Path(__file__).parent.parent / 'common' / _SERVER_SCRIPT_NAME


class DockerMDXServer:
    def __enter__(self):
        global _RUNNING_CONTAINER_IMAGE
        if not _RUNNING_CONTAINER_IMAGE:  # type: ignore
            logging.info('Starting docker mdx server')
            image_name = 'devdemisto/demisto-sdk-dependencies:1.0.0.33871'
            Docker.pull_image(image_name)
            if running_container := init_global_docker_client() \
                    .containers.list(filters={'name': DEMISTO_DEPS_DOCKER_NAME}):
                running_container[0].stop()
            location_in_docker = f'/content/{_SERVER_SCRIPT_NAME}'
            container: docker.models.containers.Container = Docker.create_container(
                name=DEMISTO_DEPS_DOCKER_NAME,
                image=image_name,
                command=['node', location_in_docker],
                user=f"{os.getuid()}:4000",
                files_to_push=[(server_script_path(), location_in_docker)],
                auto_remove=True,
                ports={'6161/tcp': ('localhost', 6161)}

            )
            self.owning_obj = True
            container.start()
            if 'MDX server is listening on port' not in (str(next(container.logs(stream=True)).decode('utf-8'))):
                self.stop_docker_container()
                logging.error('Docker for MDX server was not started correctly')
                logging.error(f'docker logs:\n{container.logs().decode("utf-8")}')
                return
            _RUNNING_CONTAINER_IMAGE = container

        self.started_successfully = True
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

    def __enter__(self):
        global _MDX_SERVER_PROCESS
        if not _MDX_SERVER_PROCESS:
            _MDX_SERVER_PROCESS = subprocess.Popen(['node', str(server_script_path())],
                                                   stdout=subprocess.PIPE, text=True)
            line = _MDX_SERVER_PROCESS.stdout.readline()  # type: ignore
            if 'MDX server is listening on port' not in line:
                logging.error(f'MDX local server couldnt be started: {line}')
                self.terminate()
                return self
            else:
                self.owning_obj = True
        self.started_successfully = True
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
