import re
from datetime import datetime
from typing import Optional

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    NATIVE_IMAGE_DOCKER_NAME,
)
from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient
from demisto_sdk.commands.common.logger import logger


class DockerImage(str):

    DOCKER_IMAGE_REGX = (
        r"^([^/]+)/(.*?)(?::(.*))?$"  # regex to extract parts of a docker-image
    )
    DEMISTO_PYTHON_BASE_IMAGE_REGEX = re.compile(
        r"[\d\w]+/python3?:(?P<python_version>[23]\.\d+(\.\d+)?)"  # regex to extract python version for image name
    )
    _dockerhub_client = DockerHubClient()

    def __new__(cls, docker_image: str, raise_if_not_valid: bool = False):
        instance = super().__new__(cls, docker_image)
        pattern = re.compile(cls.DOCKER_IMAGE_REGX)
        if matches := pattern.match(docker_image):
            instance._repository = matches.group(1)  # type: ignore[attr-defined]
            instance._image_name = matches.group(2)  # type: ignore[attr-defined]
            instance._tag = matches.group(3)  # type: ignore[attr-defined]
        else:
            instance._repository = ""  # type: ignore[attr-defined]
            instance._image_name = ""  # type: ignore[attr-defined]
            instance._tag = ""  # type: ignore[attr-defined]

        if raise_if_not_valid and not instance.is_valid:
            raise ValueError(
                f"Docker image {docker_image} is not valid, should be in the form of repository/image-name:tag"
            )

        return instance

    @property
    def repository(self) -> str:
        return getattr(self, "_repository", "")

    @property
    def image_name(self) -> str:
        return getattr(self, "_image_name", "")

    @property
    def tag(self) -> str:
        return getattr(self, "_tag", "")

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
