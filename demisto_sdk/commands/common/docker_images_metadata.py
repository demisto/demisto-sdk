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


DOCKER_IMAGES_METADATA_NAME = "docker_images_metadata.json"
URL = f"https://api.github.com/repos/demisto/dockerfiles-info/contents/{DOCKER_IMAGES_METADATA_NAME}?ref=aa6fa17889cea0bf5c0a982be637f00313a56743"


json = JSON_Handler()


class DockerImageTagMetadata(Singleton, BaseModel):
    python_version: Optional[str]


class DockerImagesMetadata(BaseModel):
    docker_images: Dict[str, Dict[str, DockerImageTagMetadata]] = {}

    @validator("docker_images", always=True)
    def get_docker_images_metadata_content(cls, v: Dict) -> Dict:
        try:
            response = requests.get(URL, verify=False)
            response.raise_for_status()
        except requests.ConnectionError:
            logger.debug(f'Got connection error when trying to get {DOCKER_IMAGES_METADATA_NAME}, retrying')
            response = requests.get(URL, verify=False)
            response.raise_for_status()

        try:
            response_as_json = response.json()
        except json.JSONDecodeError:
            logger.error(f'Could not retrieve response from {URL=} in a json format')
            return v

        try:
            file_content = base64.b64decode(response_as_json.get("content")).decode('utf-8-sig')
        except Exception as e:
            logger.error(f'Could not decode {DOCKER_IMAGES_METADATA_NAME} content, error: {e}')
            return v

        try:
            return json.loads(file_content)
        except json.JSONDecodeError:
            return v

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
