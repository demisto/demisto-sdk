import re
from typing import Dict, Optional

from packaging.version import Version
from pydantic import BaseModel

from demisto_sdk.commands.common.constants import (
    DOCKER_IMAGE_REGEX,
    DOCKERFILES_INFO_REPO,
)
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.singleton import PydanticSingleton
from demisto_sdk.commands.common.tools import get_remote_file_from_api

DOCKER_IMAGES_METADATA_NAME = "docker_images_metadata.json"


class DockerImageTagMetadata(BaseModel):
    python_version: Optional[str]


class DockerImagesMetadata(PydanticSingleton, BaseModel):
    docker_images: Dict[str, Dict[str, DockerImageTagMetadata]]

    @classmethod
    def get_instance_from(cls, *args, **kwargs):
        return cls.from_github(*args, **kwargs)

    @classmethod
    def from_github(
        cls, file_name: str = DOCKER_IMAGES_METADATA_NAME, tag: str = "master"
    ):
        tag = "4c162e56174bec3ee7bb1b418ad2b20e4bdce3e0"
        logger.debug(
            f"loading the {DOCKER_IMAGES_METADATA_NAME} from {DOCKERFILES_INFO_REPO}"
        )
        dockerfiles_metadata = get_remote_file_from_api(
            file_name,
            tag=tag,
            git_content_config=GitContentConfig(
                repo_name=DOCKERFILES_INFO_REPO, repo_hostname=GitContentConfig.GITHUB
            ),
            encoding="utf-8-sig",
        )
        logger.info(f"{dockerfiles_metadata=}")
        if not dockerfiles_metadata:
            raise ValueError(
                f"Could not retrieve the {DOCKERFILES_INFO_REPO} from {DOCKERFILES_INFO_REPO} repo"
            )

        return cls.parse_obj(dockerfiles_metadata)

    def get_docker_image_metadata_value(
        self, docker_image: str, docker_metadata_key: str
    ) -> Optional[str]:
        """
        Get the content of the requested key in the metadata
        """
        try:
            match = re.match(DOCKER_IMAGE_REGEX, docker_image)
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
        if python_version := self.get_docker_image_metadata_value(
            docker_image, "python_version"
        ):
            logger.info(
                f"successfully got {python_version=} for {docker_image=} from {DOCKER_IMAGES_METADATA_NAME}"
            )
            return Version(python_version)

        return None
