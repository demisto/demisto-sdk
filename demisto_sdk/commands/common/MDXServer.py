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


def server_script_path():
    return Path(__file__).parent.parent / 'common' / _SERVER_SCRIPT_NAME


class DockerMDXServer:
    def __enter__(self):
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
        self._container = container
        container.start()
        if 'MDX server is listening on port' not in (str(next(container.logs(stream=True)).decode('utf-8'))):
            self._container.stop()
            logging.error('Docker for MDX server was not started correctly')
            logging.info(f'docker logs: {container.logs().decode("utf-8")}')
        else:
            self.started_successfully = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info('Stopping mdx docker server')
        self._container.stop()

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
                self.terminate()
            else:
                self.started_successfully = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()

    @staticmethod
    def terminate():
        global _MDX_SERVER_PROCESS
        if _MDX_SERVER_PROCESS:
            _MDX_SERVER_PROCESS.terminate()
            _MDX_SERVER_PROCESS = None

    def is_started(self):
        return self.started_successfully
