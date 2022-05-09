import logging
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import docker
from docker.types import Mount

from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON

DOCKER_CLIENT = None
logger = logging.getLogger('demisto-sdk')
PATH_OR_STR = Union[Path, str]
FILES_SRC_TARGET = List[Tuple[PATH_OR_STR, str]]
# this will be used to determine if the system supports mounts
CAN_MOUNT_FILES = not os.getenv('CIRCLECI', False)


def init_global_docker_client(timeout: int = 60, log_prompt: str = ''):

    global DOCKER_CLIENT
    if DOCKER_CLIENT is None:
        try:
            if log_prompt:
                logger.info(f'{log_prompt} - init and login the docker client')
            else:
                logger.info('init and login the docker client')
            DOCKER_CLIENT = docker.from_env(timeout=timeout)
            docker_user = os.getenv('DOCKERHUB_USER')
            docker_pass = os.getenv('DOCKERHUB_PASSWORD')
            DOCKER_CLIENT.login(username=docker_user,
                                password=docker_pass,
                                registry="https://index.docker.io/v1")
        except Exception:
            logger.exception(f'{log_prompt} - failed to login to docker registry')

    return DOCKER_CLIENT


def copy_file(cp_from: PATH_OR_STR, cp_to: PATH_OR_STR) -> Path:
    cp_from = Path(cp_from)
    cp_to = Path(cp_to)
    cp_to.touch()
    if cp_from.exists():
        cp_to.write_bytes(cp_from.read_bytes())
    return cp_to


class DockerBase:
    def __init__(self):
        self.tmp_dir_name = tempfile.TemporaryDirectory(prefix=os.path.join(os.getcwd(), 'tmp'))
        self.tmp_dir = Path(self.tmp_dir_name.name)
        installation_scripts = Path(__file__).parent / 'resources' / 'installation_scripts'
        self.installation_scripts = {
            TYPE_PYTHON: installation_scripts / 'python_image.sh',
            TYPE_PWSH: installation_scripts / 'powershell_image.sh',
        }
        self.changes = {
            TYPE_PWSH: ['WORKDIR /devwork'],
            TYPE_PYTHON: ['WORKDIR /devwork', 'ENTRYPOINT ["/bin/sh", "-c"]'],
        }
        self.requirements = self.tmp_dir / 'requirements.txt'
        self.requirements.touch()
        self._files_to_push_on_installation: FILES_SRC_TARGET = [
            (self.requirements, '/test-requirements.txt'),
        ]

    def __del__(self):
        del self.tmp_dir_name

    def installation_files(self, container_type: str) -> FILES_SRC_TARGET:
        files = self._files_to_push_on_installation.copy()
        files.append((self.installation_scripts[container_type], '/install.sh'))
        return files

    @staticmethod
    def pull_image(image: str) -> docker.models.images.Image:
        """
        Pulling an image if it dosnt exist localy.
        """
        docker_client = init_global_docker_client()
        try:
            return docker_client.images.get(image)
        except docker.errors.ImageNotFound:
            logger.debug(f'docker image {image} not found, pulling')
            docker_client.images.pull(image)
            logger.debug(f'docker image {image} finished pulling')
            return docker_client

    @staticmethod
    def copy_files_container(container: docker.models.containers.Container, files: FILES_SRC_TARGET):
        """
        Args:
            container: the container object.
            files: a list of (target path in container, source path in machine).
        """
        if files:
            with tempfile.NamedTemporaryFile() as tar_file_path:
                with tarfile.open(name=tar_file_path.name, mode='w') as tar_file:
                    for src, dst in files:
                        try:
                            tar_file.add(src, arcname=dst)
                        except Exception as error:
                            logger.debug(error)
                with open(tar_file_path.name, 'rb') as byte_file:
                    container.put_archive('/', byte_file.read())

    def create_container(self, image: str, command: Union[str, List[str]], files_to_push: Optional[FILES_SRC_TARGET] = None,
                         environment: Optional[Dict] = None, **kwargs) -> docker.models.containers.Container:
        """
        Creates a container and pushing requested files to the container.
        """
        container: docker.models.containers.Container = init_global_docker_client().containers.create(
            image=image, command=command, environment=environment, **kwargs)
        if files_to_push:
            self.copy_files_container(container, files_to_push)
        return container

    def create_image(self, base_image: str, image: str, container_type: str = TYPE_PYTHON,
                     install_packages: Optional[List[str]] = None) -> docker.models.images.Image:
        """
        this function is used to create a new image of devtestsdemisto docker images.
        Args:
            base_image(str): the base docker image e.g. demisto/python3:3.10.0.23456
            image(str) the new image name to create e.g. devtestsdemisto/python3:3.10.0.23456-d41d8cd98f00b204e9800998ecf8427e
            container_type(str): can be 'python' or 'powershell'
            install_packages(list(str)): pip packages to install e.g ["pip='*'", "pytlint==1.2.3"]
        Returns:
            the new created image
        Flow:
            1. creating a container using an existing image
            2. running the istallation scripts
            3. committing the docker changes (installed packages) to a new local image
        """
        self.requirements.write_text('\n'.join(install_packages) if install_packages else '')
        logger.debug(f'Trying to pull image {base_image}')
        self.pull_image(base_image)
        container = self.create_container(image=base_image, files_to_push=self.installation_files(container_type), command='/install.sh')
        container.start()
        if container.wait(condition="exited").get("StatusCode") != 0:
            raise docker.errors.BuildError(
                reason=f"Installation script failed to run on container '{container.id}'.", build_log=container.logs())
        repository, tag = image.split(':')
        container.commit(repository=repository, tag=tag, changes=self.changes[container_type])
        return image


class MountableDocker(DockerBase):
    def __init__(self):
        super(MountableDocker, self).__init__()
        files = [
            Path('/etc/ssl/certs/ca-certificates.crt'),
            Path('/etc/pip.conf'),
        ]
        for file in files:
            if file.exists():
                self._files_to_push_on_installation.append(
                    (copy_file(file, self.tmp_dir / file.name), str(file))
                )

    @staticmethod
    def get_mounts(files: FILES_SRC_TARGET) -> List[Mount]:
        """
        Args:
            files: a list of (target path in container, source path in machine).
        Returns:
            a list of mounts
        """
        mounts = []
        for src, target in files:
            try:
                src = Path(src)
                if src.exists():
                    mounts.append(Mount(target, str(src.absolute()), 'bind'))
            except Exception:
                logger.debug(f'Failed to mount {src} to {target}')
        return mounts

    def create_container(self, image: str, command: Union[str, List[str]], files_to_push: Optional[FILES_SRC_TARGET] = None,
                         environment: Optional[Dict] = None, mount_files: bool = CAN_MOUNT_FILES, **kwargs) -> docker.models.containers.Container:
        """
        Creates a container and pushing requested files to the container.
        """
        kwargs = kwargs or {}
        if files_to_push and mount_files:
            return super(MountableDocker, self).create_container(image=image, command=command, environment=environment,
                                                                 mounts=self.get_mounts(files_to_push), files_to_push=None, **kwargs)
        else:
            return super(MountableDocker, self).create_container(image=image, command=command, environment=environment,
                                                                 files_to_push=files_to_push, **kwargs)


Docker = MountableDocker() if CAN_MOUNT_FILES else DockerBase()
