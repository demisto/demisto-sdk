import re
from enum import Enum
from typing import Dict, Optional

from packaging.version import Version
from pydantic import BaseModel

from demisto_sdk.commands.common.constants import (
    DOCKERFILES_INFO_REPO,
)
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.singleton import PydanticSingleton
from demisto_sdk.commands.common.tools import get_remote_file_from_api

DOCKER_IMAGES_METADATA_NAME = "docker_images_metadata.json"

# regex to extract docker-images that are specific to content / dockerfiles
DOCKERFILES_INFO_IMAGE_REGEX = r"^demisto/([^\s:]+):(\d+(\.\d+)*)$"


class DockerImageTagMetadata(BaseModel):
    python_version: Optional[str]


class DockerImagesMetadata(PydanticSingleton, BaseModel):
    docker_images: Dict[str, Dict[str, DockerImageTagMetadata]]

    class MetadataValues(str, Enum):
        PYTHON_VERSION = "python_version"

    @classmethod
    def get_instance_from(cls, *args, **kwargs):
        return cls.__from_github(*args, **kwargs)

    @classmethod
    def __from_github(
        cls, file_name: str = DOCKER_IMAGES_METADATA_NAME, tag: str = "master"
    ):
        """
        Get the docker_images_metadata.json from the dockerfiles-info repo and load it to a pydnatic object.

        Args:
            file_name (str): the file path for the docker_images_metadata.json
            tag (str): branch/commit to get a specific docker_images_metadata.json

        """
        logger.debug(
            f"Trying to load the {DOCKER_IMAGES_METADATA_NAME} from {DOCKERFILES_INFO_REPO}"
        )
        dockerfiles_metadata = get_remote_file_from_api(
            file_name,
            tag=tag,
            git_content_config=GitContentConfig(repo_name=DOCKERFILES_INFO_REPO),
            encoding="utf-8-sig",
        )
        if not dockerfiles_metadata:
            logger.error(
                f"Could not retrieve the {DOCKER_IMAGES_METADATA_NAME} from {DOCKERFILES_INFO_REPO} repo"
            )
            dockerfiles_metadata = {"docker_images": {}}

        return cls.parse_obj(dockerfiles_metadata)

    def __get_metadata_value(
        self, docker_image: str, docker_metadata_key: str
    ) -> Optional[str]:
        """
        Get the content of the requested key in the metadata

        Args:
            docker_image (str): the docker image from the script/integration yml
            docker_metadata_key (str): the key in the DockerImageTagMetadata class
        """
        try:
            # if we were not able to load the file
            if not self.docker_images:
                return None
            match = re.match(DOCKERFILES_INFO_IMAGE_REGEX, docker_image)
            docker_name, tag = match.group(1), match.group(2)  # type: ignore[union-attr]
            docker_image_metadata = (self.docker_images.get(docker_name) or {}).get(tag)
            return getattr(docker_image_metadata, docker_metadata_key)
        except (AttributeError, ValueError, TypeError) as err:
            logger.debug(
                f"Could not get {docker_metadata_key} for {docker_image=} because {err=} occurred"
            )
            return None

    def python_version(self, docker_image: str) -> Optional[Version]:
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
