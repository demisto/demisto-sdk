import io
import os
import tarfile
from typing import Union, List, Optional
import docker
from demisto_sdk.commands.common.logger import logger

client = docker.from_env()


class ContainerRunner:

    def __init__(self, image: str, container_name: Optional[str]):
        self._base_image_name = image
        self._image_name = image
        self.container_name = container_name
        self._container_obj = None

    @property
    def container(self):
        if self._container_obj is None:
            self._create_container()
        return self._container_obj

    def _create_container(self, **kwargs):
        if self._container_obj:
            self.remove_container()
        self._container_obj = client.containers.create(image=self._image_name, name=self.container_name, **kwargs)

    def exec(self, command: Union[str, List[str]], **kwargs):
        if self._container_obj is not None:
            self._image_name = self._container_obj.commit().id
            self.remove_container()
        kwargs['detach'] = True
        self._create_container(command=command, **kwargs)
        try:
            self._container_obj.start()
        except Exception as error:
            logger.debug(error)
        return {**self._container_obj.wait(), 'Outputs': self._container_obj.logs()}

    def import_file(self, file_bytes: bytes, file_dest: Optional[str]):
        tar_byte_file = io.BytesIO()
        dir_dest, file_name = os.path.split(file_dest)
        if not dir_dest:
            dir_dest = '.'
        with tarfile.open(fileobj=tar_byte_file, mode='w') as temp_tar_file:
            temp_tar_file.addfile(**create_tar_info(file_name, file_bytes))
        tar_byte_file.seek(0)
        return self.container.put_archive(dir_dest, tar_byte_file.read())

    def export_file(self, file_src: str):
        archive, stat = self.container.get_archive(f'{file_src}')
        byte_file = io.BytesIO(initial_bytes=b''.join(archive))
        byte_file.seek(0)
        with tarfile.open(fileobj=byte_file) as tar_file:
            return tar_file.extractfile(file_src.split('/')[-1]).read()

    def remove_container(self):
        self._container_obj.remove()
        self._container_obj = None

    def remove_images(self):
        self.remove_container()
        DockerTools.remove_image(self._image_name)
        self._image_name = self._base_image_name

    def __del__(self):
        self.remove_images()


class DockerTools:

    @staticmethod
    def remove_container(name_or_id, ignore_container_not_found=True, force=False):
        try:
            client.containers.get(name_or_id).remove(force=force)
        except docker.errors.NotFound as not_found:
            if not ignore_container_not_found:
                raise not_found

    @staticmethod
    def remove_image(name_or_id, ignore_image_not_found=True, force=False):
        try:
            client.images.remove(name_or_id, force=force)
        except docker.errors.ImageNotFound as not_found:
            if not ignore_image_not_found:
                raise not_found


def create_tar_info(name, file_bytes):
    file_data = io.BytesIO(initial_bytes=file_bytes)
    file_data.name = name
    file_data.seek(0)
    tar_info = tarfile.TarInfo(name=name)
    tar_info.size = file_data.getbuffer().nbytes
    return {'tarinfo': tar_info, 'fileobj': file_data}
