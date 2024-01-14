import re
from datetime import datetime
from typing import Optional

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    NATIVE_IMAGE_DOCKER_NAME,
)
from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient
from demisto_sdk.commands.common.logger import logger


class DockerImage:

    DOCKER_IMAGE_REGX = (
        r"^([^/]+)/(.*?)(?::(.*))?$"  # regex to extract parts of a docker-image
    )
    DEMISTO_PYTHON_BASE_IMAGE_REGEX = re.compile(
        r"[\d\w]+/python3?:(?P<python_version>[23]\.\d+(\.\d+)?)"  # regex to extract python version for image name
    )

    def __init__(
        self,
        dockerhub_client: DockerHubClient,
        repository: str = "",
        image_name: str = "",
        tag: str = "",
    ):
        self._dockerhub_client = dockerhub_client
        self.repository = repository  # the repository e.g.: demisto
        self.image_name = image_name  # the image name e.g.: python3, pan-os-python
        self.tag = tag  # the tag

    @classmethod
    def parse(
        cls,
        docker_image: str,
        dockerhub_client: Optional[DockerHubClient] = None,
        raise_if_not_valid: bool = False,
    ) -> "DockerImage":
        """
        Parses a docker-image into repository, image name and its tag

        Args:
            docker_image: the docker image to parse
            dockerhub_client: client to interact with dockerhub client
            raise_if_not_valid: raise ValueError if the docker-image structure is not valid
        """
        _dockerhub_client = dockerhub_client or DockerHubClient()
        pattern = re.compile(cls.DOCKER_IMAGE_REGX)
        if matches := pattern.match(docker_image):
            docker_image_object = cls(
                _dockerhub_client,
                repository=matches.group(1),
                image_name=matches.group(2),
                tag=matches.group(3),
            )
        else:
            docker_image_object = cls(_dockerhub_client)

        if raise_if_not_valid and not docker_image_object.is_valid:
            raise ValueError(
                f"Docker image {docker_image} is not valid, should be in the form of repository/image-name:tag"
            )

        return docker_image_object

    def __str__(self):
        return f"{self.repository}/{self.image_name}:{self.tag}"

    @property
    def name(self):
        """
        Returns the repository + image name. .e.g: demisto/python3, demisto/pan-os-python
        """
        return f"{self.repository}/{self.image_name}"

    @property
    def is_valid(self) -> bool:
        """
        Validates that the structure of the docker-image is valid.

        Returns:
            bool: True if the structure is valid, False if not.
        """
        if not self.repository or not self.image_name or not self.tag:
            logger.warning(
                f"Docker image {self} is not valid, should be in the form of repository/image-name:tag"
            )
            return False
        return True

    @property
    def is_tag_latest(self) -> bool:
        return self.tag == "latest"

    @property
    def is_demisto_repository(self) -> bool:
        return self.repository == "demisto"

    @property
    def is_native_image(self) -> bool:
        return self.name == NATIVE_IMAGE_DOCKER_NAME

    @property
    def creation_date(self) -> datetime:
        return self._dockerhub_client.get_docker_image_tag_creation_date(
            self.name, tag=self.tag
        )

    @property
    def python_version(self) -> Optional[Version]:
        if self.is_valid:
            if "pwsh" == self.image_name or "powershell" == self.image_name:
                logger.debug(
                    f"The {self} is a powershell image, does not have python version"
                )
                return None

            if match := self.DEMISTO_PYTHON_BASE_IMAGE_REGEX.match(str(self)):
                return Version(match.group("python_version"))

            logger.debug(f"Could not get python version for image {self} from regex")
            image_env = self._dockerhub_client.get_image_env(self.name, tag=self.tag)

            if python_version := next(
                (
                    var.split("=")[1]
                    for var in image_env
                    if var.startswith("PYTHON_VERSION=")
                ),
                None,
            ):
                return Version(python_version)

            logger.error(f"Could not find python-version of docker-image {self}")
            return None

        logger.debug(
            f"docker-image {self} is not valid, could not get its python-version"
        )
        return None

    @property
    def is_image_exist(self) -> bool:
        """
        Returns True if the docker-image exist in dockerhub
        """
        return self._dockerhub_client.is_docker_image_exist(self.name, tag=self.tag)

    @property
    def latest_tag(self) -> Version:
        return self._dockerhub_client.get_latest_docker_image_tag(self.name)
