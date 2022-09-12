import logging
import os
from pathlib import Path

import docker
import docker.errors
import docker.models.containers

from demisto_sdk.commands.lint.docker_helper import (Docker,
                                                     init_global_docker_client)

DEMISTO_DEPS_DOCKER_NAME = "demisto-dependencies"


class DockerMDXServer:
    def __enter__(self):
        image_name = 'devdemisto/demisto-sdk-dependencies:1.0.0.33871'
        Docker.pull_image(image_name)
        if running_container := init_global_docker_client() \
                .containers.list(filters={'name': DEMISTO_DEPS_DOCKER_NAME}):
            running_container[0].stop()
        script_name = 'mdx-parse-server.js'
        location_in_docker = f'/content/{script_name}'
        mdx_parse_server = Path(__file__).parent.parent / 'common' / script_name
        container: docker.models.containers.Container = Docker.create_container(
            name=DEMISTO_DEPS_DOCKER_NAME,
            image=image_name,
            command=['node', location_in_docker],
            user=f"{os.getuid()}:4000",
            files_to_push=[(mdx_parse_server, location_in_docker)],
            auto_remove=True,
            ports={'6161/tcp': ('localhost', 6161)}

        )
        self._container = container
        container.start()
        if 'MDX server is listening on port' not in (str(next(container.logs(stream=True)).decode('utf-8'))):
            self._container.stop()
            logging.info('Docker server was not started correctly')
            logging.info(f'docker logs: {container.logs().decode("utf-8")}')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._container.stop()


class LocalMDXServer:
    def __enter__(self):
        pass
