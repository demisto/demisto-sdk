import re
from datetime import datetime
from typing import Optional

from dateutil import parser
from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    NATIVE_IMAGE_DOCKER_NAME,
)
from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient

# TODO: un-comment line below and import functions from docker_helper to replace dockerhub_client functions
from demisto_sdk.commands.common.docker_helper import DockerBase, get_python_version
from demisto_sdk.commands.common.logger import logger


class DockerImage(str):
    # regex to extract parts of any docker-image in the following structure (repo/image-name:tag)
    DOCKER_IMAGE_REGX = r"^([^/]+)/(.*?)(?::(.*))?$"
    DEMISTO_PYTHON_BASE_IMAGE_REGEX = re.compile(
        r"[\d\w]+/python3?:(?P<python_version>[23]\.\d+(\.\d+)?)"  # regex to extract python version for image name
    )

    _dockerhub_client = DockerHubClient()  # DELETE
    _docker_client = DockerBase()

    def __new__(
        cls,
        docker_image: str,
        raise_if_not_valid: bool = False,
    ) -> "DockerImage":
        """
        Creates a new instance of DockerImage.

        This method parses the given docker image string and initializes a new DockerImage object
        with the extracted repository, image name, and tag information.

        Args:
            docker_image (str): The full docker image string in the format "repository/image-name:tag".
            raise_if_not_valid (bool, optional): If True, raises a ValueError if the docker image
                string has an invalid structure. Defaults to False.

        Returns:
            DockerImage: A new instance of the DockerImage class.

        Raises:
            ValueError: If raise_if_not_valid is True and the docker image string is not valid.

        Example:
            >>> docker_image = DockerImage("demisto/python3:3.8.6.14516")
            >>> print(docker_image.repository)
            'demisto'
            >>> print(docker_image.image_name)
            'python3'
            >>> print(docker_image.tag)
            '3.8.6.14516'

        Note:
            - The method uses a regular expression to parse the docker image string. If the string
              doesn't match the expected format, the repository, image_name, and tag attributes
              will be set to empty strings.
             - The _docker_client attribute is initialized as an instance of DockerBase, which is used for interacting with a DockerHub proxy.

        """
        docker_image_instance = super().__new__(cls, docker_image)
        pattern = re.compile(cls.DOCKER_IMAGE_REGX)
        if matches := pattern.match(docker_image):
            docker_image_instance._repository = matches.group(1)  # type: ignore[attr-defined]
            docker_image_instance._image_name = matches.group(2)  # type: ignore[attr-defined]
            docker_image_instance._tag = matches.group(3)  # type: ignore[attr-defined]
        else:
            docker_image_instance._repository = ""  # type: ignore[attr-defined]
            docker_image_instance._image_name = ""  # type: ignore[attr-defined]
            docker_image_instance._tag = ""  # type: ignore[attr-defined]

        if raise_if_not_valid and not docker_image_instance.is_valid:
            raise ValueError(
                f"Docker image {docker_image} is not valid, should be in the form of repository/image-name:tag"
            )

        return docker_image_instance

    @property
    def summary(self) -> str:
        return f"DockerImage(docker-image={self}, valid={self.is_valid}, creation-date={self.creation_date}, python-version:{self.python_version}, latest-tag={self.latest_tag})"

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
    def name(self) -> str:
        """
        Returns the repository + image name. .e.g: demisto/python3, demisto/pan-os-python
        """
        return f"{self.repository}/{self.image_name}"

    @property
    def full_image_name(self) -> str:
        """
        Returns the repository + image name + tag. .e.g: demisto/python3:3.11.10.111526, demisto/pan-os-python:latest
        """
        return f"{self.repository}/{self.image_name}:{self.tag}"

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
    def is_python3_image(self) -> bool:
        return self.is_demisto_repository and self.image_name == "python3"

    @property
    def is_native_image(self) -> bool:
        return self.name == NATIVE_IMAGE_DOCKER_NAME

    @property
    def creation_date(self) -> datetime:
        """Retrieves the creation date of a Docker image.

        This property parses the 'Created' attribute from the Docker image metadata
        and returns it as a datetime object. The timezone information is removed
        to return a naive datetime object.

        Returns:
            datetime: The creation date of the Docker image as a naive datetime object.

        Raises:
            AttributeError: If the Docker image has not been initialized or lacks the 'Created' attribute.
            ValueError: If the date string cannot be parsed.
        """
        image = self._docker_client.pull_image(self.full_image_name)
        return parser.parse(image.attrs["Created"]).replace(tzinfo=None)

        # return self._dockerhub_client.get_docker_image_tag_creation_date(
        #     self.name, tag=self.tag
        # )

    @property
    def python_version(self) -> Optional[Version]:
        if self.is_valid:
            if "pwsh" == self.image_name or "powershell" == self.image_name:
                logger.debug(
                    f"The {self} image is a powershell image, does not have python version"
                )
                return None

            if self.is_python3_image and (
                match := self.DEMISTO_PYTHON_BASE_IMAGE_REGEX.match(self)
            ):
                return Version(match.group("python_version"))

            logger.debug(f"Could not get python version for image {self} from regex")

            # image_env = self._dockerhub_client.get_image_env(self.name, tag=self.tag)

            # if python_version := next(
            #     (
            #         var.split("=")[1]
            #         for var in image_env
            #         if var.startswith("PYTHON_VERSION=")
            #     ),
            #     None,
            # ):
            #     return Version(python_version)

            if python_version := get_python_version(self.name):
                return python_version
            else:
                logger.error(f"Could not find python-version of docker-image {self}")

        else:
            logger.debug(
                f"docker-image {self} is not valid, could not get its python-version"
            )
        return None

    @property
    def is_image_exist(self) -> bool:
        """
        Check if the Docker image exists in the Docker registry.

        This property uses the DockerBase client to verify the availability
        of the Docker image in the registry.

        Returns:
            bool: True if the image exists in the registry, False otherwise.
        """
        return self._docker_client.is_image_available(self.full_image_name)

    @property
    def latest_tag(self) -> Version:
        # FIXME: Currently return last available tag of the client, not necessarily the latest in DockerHub
        return self._docker_client.get_latest_docker_image_tag(self.name)

    @property
    def latest_docker_image(self) -> "DockerImage":
        """
        Returns the docker image with the latest tag
        """
        # return DockerImage(self._dockerhub_client.get_latest_docker_image(self.name))
        return DockerImage(f"{self.repository}:{self.latest_tag}")
