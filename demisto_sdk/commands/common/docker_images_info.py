import functools
from typing import Dict, Optional

from pydantic import BaseModel

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.singleton import Singleton


class DockerImageTagMetadata(BaseModel):
    python_version: Optional[str]


class DockerImagesInfo(Singleton, BaseModel):
    docker_images: Dict[str, Dict[str, DockerImageTagMetadata]]

    def __init__(self, url: str = "https://github.com/demisto/dockerfiles-info/blob/7608b23e95707d3cee14320898316fd67d79dbbd/dockerfiles-metadata.json"):
        response = requests.get(url)
        super().__init__(**response.json())

    def get_docker_image_metadata_value(
        self, docker_image: str, docker_metadata_key: str
    ) -> str:
        try:
            docker_name, tag = docker_image.replace("demisto/", "").split(":")
            docker_image_metadata = self.docker_images.get(docker_name, {}).get(tag)
            return getattr(docker_image_metadata, docker_metadata_key)
        except (AttributeError, ValueError, TypeError) as err:
            logger.debug(
                f"Could not get {docker_metadata_key} for {docker_image=} because {err=} occurred"
            )
            return ""

    def python_version(self, docker_image: str) -> str:
        return self.get_docker_image_metadata_value(docker_image, "python_version")
