from typing import Dict, Optional, Union

from packaging.version import Version
from pydantic import BaseModel
from requests.exceptions import ConnectionError

from demisto_sdk.commands.common.constants import (
    DOCKERFILES_INFO_REPO,
    DOCKERFILES_INFO_REPO_PRIMARY_BRANCH,
)
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.singleton import PydanticSingleton
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.common.tools import NoInternetConnectionException

DOCKER_IMAGES_METADATA_NAME = "docker_images_metadata.json"


class DockerImageTagMetadata(BaseModel):
    python_version: Optional[str]


class DockerImagesMetadata(PydanticSingleton, BaseModel):
    docker_images: Dict[str, Dict[str, DockerImageTagMetadata]]

    class MetadataValues(StrEnum):
        PYTHON_VERSION = "python_version"

    @classmethod
    def get_instance_from(cls, *args, **kwargs):
        return cls.__from_github(*args, **kwargs)

    @classmethod
    def __from_github(
        cls,
        file_name: str = DOCKER_IMAGES_METADATA_NAME,
        tag: str = DOCKERFILES_INFO_REPO_PRIMARY_BRANCH,
    ):
        """
        Get the docker_images_metadata.json from the dockerfiles-info repo and load it to a pydantic object.

        Args:
            file_name (str): the file path for the docker_images_metadata.json
            tag (str): branch/commit to get a specific docker_images_metadata.json

        """
        logger.debug(
            f"Trying to load the {DOCKER_IMAGES_METADATA_NAME} from {DOCKERFILES_INFO_REPO}"
        )
        try:
            dockerfiles_metadata = JsonFile.read_from_github_api(
                file_name,
                repo=DOCKERFILES_INFO_REPO,
                tag=tag,
                verify_ssl=False,
                encoding="utf-8-sig",
            )
        except (FileReadError, NoInternetConnectionException, ConnectionError) as error:
            logger.error(
                f"Could not read {DOCKER_IMAGES_METADATA_NAME} from {DOCKERFILES_INFO_REPO} repository, error: {error}"
            )
            dockerfiles_metadata = {"docker_images": {}}

        return cls.parse_obj(dockerfiles_metadata)

    def __get_metadata_value(
        self, docker_image: Union[str, DockerImage], docker_metadata_key: str
    ) -> Optional[str]:
        """
        Get the content of the requested key in the metadata

        Args:
            docker_image (str): the docker image from the script/integration yml
            docker_metadata_key (str): the key in the DockerImageTagMetadata class
        """
        if not self.docker_images:
            return None

        if not isinstance(docker_image, DockerImage):
            try:
                docker_image = DockerImage(docker_image, raise_if_not_valid=True)
            except ValueError as error:
                logger.debug(
                    f"Could not parse docker-image {docker_image}, error:{error}"
                )
                return None

        try:
            docker_image_metadata = (
                self.docker_images.get(docker_image.image_name) or {}
            ).get(docker_image.tag)
            return getattr(docker_image_metadata, docker_metadata_key)
        except Exception as err:
            logger.debug(
                f"Could not get {docker_metadata_key} for {docker_image=} because {err=} occurred"
            )
            return None

    def python_version(
        self, docker_image: Union[str, DockerImage]
    ) -> Optional[Version]:
        """
        Get the python version of a docker image.
        """
        if python_version := self.__get_metadata_value(
            docker_image, self.MetadataValues.PYTHON_VERSION
        ):
            logger.debug(
                f"successfully got {python_version=} for {docker_image=} from {DOCKER_IMAGES_METADATA_NAME}"
            )
            return Version(python_version)

        return None
