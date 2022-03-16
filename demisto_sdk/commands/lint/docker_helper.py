import logging
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import docker
from docker.types import Mount

from demisto_sdk.commands.common.constants import TYPE_PYTHON

DOCKER_CLIENT = None
logger = logging.getLogger('demisto-sdk')
PATH_OR_STR = Union[Path, str]
# this will be used to determine if the system supports mounts
CAN_MOUNT_FILES = not os.getenv('CIRCLECI', False)


def init_global_docker_client(timeout: int = 60, log_prompt: str = ''):

    global DOCKER_CLIENT
    if DOCKER_CLIENT is None:
        try:
            logger.info(f'{log_prompt} - init and login the docker client')
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


class Docker:

    @staticmethod
    def pull_image(image: str) -> docker.models.images.Image:
        """
        Pulling an image if it dosnt exist localy.
        """
        docker_client = init_global_docker_client()
        try:
            return docker_client.images.get(image)
        except docker.errors.ImageNotFound:
            return docker_client.images.pull(image)

    @staticmethod
    def get_mounts(files: List[Tuple[str, PATH_OR_STR]]) -> List[Mount]:
        """
        Args:
            files: a list of (target path in container, source path in machine).
        Returns:
            a list of mounts
        """
        mounts = []
        for target, src in files:
            try:
                src = Path(src)
                if src.exists():
                    mounts.append(Mount(target, str(src.absolute()), 'bind'))
            except Exception:
                logger.debug(f'Failed to mount {src} to {target}')
        return mounts

    @staticmethod
    def copy_files_container(container: docker.models.containers.Container, files: List[Tuple[str, PATH_OR_STR]]):
        """
        Args:
            container: the container object.
            files: a list of (target path in container, source path in machine).
        """
        if files:
            with tempfile.NamedTemporaryFile() as tar_file_path:
                with tarfile.open(name=tar_file_path.name, mode='w') as tar_file:
                    for dst, src in files:
                        try:
                            tar_file.add(src, arcname=dst)
                        except Exception as error:
                            logger.debug(error)
                with open(tar_file_path.name, 'rb') as byte_file:
                    container.put_archive('/', byte_file.read())

    @staticmethod
    def create_container(image: str, command: Union[str, List[str]], files_to_push: Optional[List] = None,
                         environment: Optional[Dict] = None, mount_files: bool = CAN_MOUNT_FILES, **kwargs) -> docker.models.containers.Container:
        """
        Creates a container and pushing requested files to the container.
        """
        kwargs = kwargs or {}
        if files_to_push and mount_files:
            kwargs['mounts'] = Docker.get_mounts(files_to_push)
        container: docker.models.containers.Container = init_global_docker_client().containers.create(
            image=image, command=command, environment=environment, **kwargs)
        if files_to_push and not mount_files:
            Docker.copy_files_container(container, files_to_push)
        return container

    @staticmethod
    def create_image(base_image: str, image: str, container_type: str = TYPE_PYTHON,
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
        if not CAN_MOUNT_FILES:
            raise docker.errors.BuildError(
                reason="Can't create a container in this environment rerunning the test after 5 min might work.", build_log='')
        changes = ['WORKDIR /devwork']
        changes.append('ENTRYPOINT ["/bin/sh", "-c"]') if container_type == TYPE_PYTHON else None
        script = f'{container_type}_image.sh'
        with tempfile.TemporaryDirectory(prefix=os.getcwd()) as tmp_dir_path:
            tmp_dir = Path(tmp_dir_path)
            requirements = tmp_dir / 'requirements.txt'
            requirements.touch()
            # list of mounts (see in get_mounts doc string)
            files_to_push = [
                (f'/{script}', Path(__file__).parent / 'resources' / 'installation_scripts' / script),
                ('/etc/pip.conf', copy_file('/etc/pip.conf', tmp_dir / 'pip.conf')),
                ('/etc/ssl/certs/ca-certificates.crt', copy_file('/etc/ssl/certs/ca-certificates.crt', tmp_dir / 'ca-certificates.crt')),
                ('/test-requirements.txt', requirements),
            ]
            if install_packages:
                requirements.write_text('\n'.join(install_packages))

            Docker.pull_image(base_image)

            container = Docker.create_container(
                image=base_image, files_to_push=files_to_push, command=f'/{script}',
                mount_files=True
            )
            container.start()
            if container.wait(condition="exited").get("StatusCode") != 0:
                raise docker.errors.BuildError(
                    reason="Installation script failed to run.", build_log=container.logs())
        repository, tag = image.split(':')
        container.commit(repository=repository, tag=tag, changes=changes)
        return image
