import functools
from typing import Dict, Optional
import base64
from pydantic import BaseModel, validator
import requests
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.singleton import Singleton
from demisto_sdk.commands.common.git_util import GitUtil
from git import Repo
from demisto_sdk.commands.common.handlers import JSON_Handler
import tempfile
from pydantic import parse
from demisto_sdk.commands.common.tools import get_remote_file_from_api
from demisto_sdk.commands.common.git_content_config import GitContentConfig

DOCKER_IMAGES_METADATA_NAME = "docker_images_metadata.json"


json = JSON_Handler()


class DockerImageTagMetadata(Singleton, BaseModel):
    python_version: Optional[str]


class DockerImagesMetadata(BaseModel):
    docker_images: Dict[str, Dict[str, DockerImageTagMetadata]] = {}

    def __init__(self):
        docker_images_metadata_content = get_remote_file_from_api(
            "docker_images_metadata.json",
            tag="aa6fa17889cea0bf5c0a982be637f00313a56743",
            git_content_config=GitContentConfig(repo_name="demisto/dockerfiles-info"),
            encoding="utf-8-sig"
        )

        super().__init__(**docker_images_metadata_content)

    def get_docker_image_metadata_value(
        self, docker_image: str, docker_metadata_key: str
    ) -> Optional[str]:
        """
        Get the content of the requested key in the metadata
        """
        try:
            docker_name, tag = docker_image.replace("demisto/", "").split(":")
            docker_image_metadata = self.docker_images.get(docker_name, {}).get(tag)
            return getattr(docker_image_metadata, docker_metadata_key)
        except (AttributeError, ValueError, TypeError) as err:
            logger.debug(
                f"Could not get {docker_metadata_key} for {docker_image=} because {err=} occurred"
            )
            return None

    def python_version(self, docker_image: str) -> str:
        """
        Get the python version of a docker image.
        """
        return self.get_docker_image_metadata_value(docker_image, "python_version")
