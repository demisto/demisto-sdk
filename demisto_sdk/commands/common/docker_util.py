import io
import os
import tarfile
from typing import Dict, List, Optional, Union

import docker
from demisto_sdk.commands.common.logger import logger

client = docker.from_env()


class ContainerRunner:
    def __init__(self, image: str, container_name: Optional[str] = None):
        """

        Args:
            image: the image (name or id)
            container_name: you can give your container a meaningful name (optional)
        """
        self._base_image_name = image
        self._image_name = image
        self.container_name = container_name
        self._container_obj: Optional[docker.models.containers.Container] = None

    @property
    def container(self) -> docker.models.containers.Container:
        """
        Notes:
            try to avoid using the container in this way.
        Returns:
            a container object (docker.models.containers.Container).
        """
        if self._container_obj is None:
            self._create_container()
        return self._container_obj

    def _create_container(self, **kwargs):
        if self._container_obj:
            self.remove_container()
        self._container_obj = client.containers.create(image=self._image_name, name=self.container_name, **kwargs)

    def exec(self, command: Union[str, List[str]], **kwargs) -> Dict[str, Union[bytes, Dict, int]]:
        """
        Args:
            command: the command to run inside the docker container
            **kwargs: extra args to pass to the docker container (according to the docker API)

        Returns:
            a dict contains 3 elements:
                1. (Outputs) the container stdout
                2. (StatusCode) the command exit code
                3. (Error) the container stderr
        """
        # one important thing that you need to know about docker is that a dead container is basically an image.
        # and that is the reason why do we need to commit to create the image.
        # so we can build a new container on the basis of this dead container.
        if self._container_obj is not None:
            self._image_name = self.container.commit().id
            self.remove_container()
        kwargs['detach'] = True
        self._create_container(command=command, **kwargs)
        try:
            self.container.start()
        except Exception as error:
            logger.debug(error)
        return {**self.container.wait(), 'Outputs': self.container.logs()}

    def import_file(self, file_bytes: bytes, file_dest: str) -> bool:
        """

        Args:
            file_bytes: the file data in bytes
            file_dest: the file destination (e.g. path in the container)

        Returns:
            True if the operation was successful False otherwise
        """
        tar_byte_file = io.BytesIO()
        dir_dest, file_name = os.path.split(file_dest)
        if not dir_dest:
            dir_dest = '.'
        with tarfile.open(fileobj=tar_byte_file, mode='w') as temp_tar_file:
            temp_tar_file.addfile(**self._create_tar_info(file_name, file_bytes))
        tar_byte_file.seek(0)
        return self.container.put_archive(dir_dest, tar_byte_file.read())

    def export_file(self, file_src: str) -> bytes:
        """

        Args:
            file_src: the path to file in the container

        Returns:
            the file data in bytes
        """
        archive, stat = self.container.get_archive(f'{file_src}')
        byte_file = io.BytesIO(initial_bytes=b''.join(archive))
        byte_file.seek(0)
        with tarfile.open(fileobj=byte_file) as tar_file:
            io_obj = tar_file.extractfile(file_src.split(os.path.sep)[-1])
            return io_obj.read() if io_obj else b''

    def remove_container(self):
        """
        removing the container (e.g. docker rm)
        """
        if self._container_obj:
            self._container_obj.remove()
            self._container_obj = None

    def remove_images(self):
        """
        removing the images created by the commits along the containers live (see the explanation in the exec comment)
        """
        self.remove_container()
        if not (self._image_name == self._base_image_name):
            DockerTools.remove_image(self._image_name)
            self._image_name = self._base_image_name

    def __del__(self):
        self.remove_images()

    @staticmethod
    def _create_tar_info(name: str, file_bytes: bytes):
        file_data = io.BytesIO(initial_bytes=file_bytes)
        file_data.name = name
        file_data.seek(0)
        tar_info = tarfile.TarInfo(name=name)
        tar_info.size = file_data.getbuffer().nbytes
        return {'tarinfo': tar_info, 'fileobj': file_data}


class DockerTools:
    """
    docker extra tools that will be usefully also as stand alone commands
    """
    @staticmethod
    def remove_container(name_or_id: str, ignore_container_not_found: bool = True, force: bool = False):
        """
        Examples
            docker rm MyTestContainer
            can be replaced with
            DockerTools.remove_container("MyTestContainer")
            in your code
        Args:
            name_or_id: the name or id of the container
            ignore_container_not_found: dont raise an exception in that the container is already not existing
            force: like the -f in docker rm command

        Raises:
            docker.errors.NotFound in case that the container doesn't exist
        """
        try:
            client.containers.get(name_or_id).remove(force=force)
        except docker.errors.NotFound as not_found:
            if not ignore_container_not_found:
                raise not_found

    @staticmethod
    def remove_image(name_or_id: str, ignore_image_not_found: bool = True, force: bool = False):
        """
        Examples
            docker rmi MyTestImage
            can be replaced with
            DockerTools.remove_image("MyTestImage")
            in your code
        Args:
            name_or_id: the name or id of the image
            ignore_image_not_found: don't raise an exception in case the image already removed
            force: same as the -f option in the "docker rmi" command

        Raises:
            docker.errors.ImageNotFound in case that the image doesn't exist

        """
        try:
            client.images.remove(name_or_id, force=force)
        except docker.errors.ImageNotFound as not_found:
            if not ignore_image_not_found:
                raise not_found
