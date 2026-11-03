import os
import re
from datetime import datetime
from typing import Optional

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEFAULT_EXTENDED_REGISTRY,
    DEMISTO_EXTENDED_REPOSITORY,
    DEMISTO_REPOSITORY,
    DEMISTO_SDK_EXTENDED_REGISTRY_ENV,
    DOCKER_REGISTRY_URL,
    NATIVE_IMAGE_DOCKER_NAME,
    strip_cr_registry_prefix,
)
from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient
from demisto_sdk.commands.common.logger import logger


class DockerImage(str):
    # regex to extract parts of any docker-image in the following structure (repo/image-name:tag)
    DOCKER_IMAGE_REGX = r"^([^/]+)/(.*?)(?::(.*))?$"
    DEMISTO_PYTHON_BASE_IMAGE_REGEX = re.compile(
        r"[\d\w]+/python3?:(?P<python_version>[23]\.\d+(\.\d+)?)"  # regex to extract python version for image name
    )
    _dockerhub_client = None
    _extended_client = None

    @classmethod
    def _get_dockerhub_client(cls):
        """Get or create the DockerHub client with the appropriate registry and credentials."""
        # Use a truthiness (emptiness) check rather than an identity check against
        # None so the client is (re)created whenever the cached value is missing or
        # otherwise falsy, not only when it is exactly None.
        if not cls._dockerhub_client:
            username = os.getenv("DEMISTO_SDK_CR_USER", "")
            password = os.getenv("DEMISTO_SDK_CR_PASSWORD", "")
            cls._dockerhub_client = DockerHubClient(
                registry=DOCKER_REGISTRY_URL, username=username, password=password
            )
        return cls._dockerhub_client

    @classmethod
    def _get_extended_client(cls):
        """Get or create a DockerHubClient for the extended registry (GCR)."""
        if not cls._extended_client:
            extended_registry = os.getenv(
                DEMISTO_SDK_EXTENDED_REGISTRY_ENV, DEFAULT_EXTENDED_REGISTRY
            )
            if not extended_registry:
                logger.warning(f"No {DEMISTO_SDK_EXTENDED_REGISTRY_ENV} configured")
                return None
            client = DockerHubClient(registry=extended_registry)
            # get_registry_api_url() resolves to the GAR proxy in CI, so override
            # with the actual registry V2 endpoint: https://{host}/v2/{path}
            host, *path = extended_registry.rstrip("/").split("/", 1)
            client.registry_api_url = (
                f"https://{host}/v2{f'/{path[0]}' if path else ''}"
            )
            cls._extended_client = client
        return cls._extended_client

    def _get_client(self):
        """Routes to the correct registry client based on repository prefix."""
        if self.is_demistoextended_repository:
            if extended_client := self._get_extended_client():
                return extended_client
        return self._get_dockerhub_client()

    def __new__(
        cls, docker_image: str, raise_if_not_valid: bool = False
    ) -> "DockerImage":
        """
        Creates a new instance of DockerImage

        Args:
            docker_image: the full docker image
            raise_if_not_valid: if True, will raise ValueError if the docker-image has an invalid structure.
        """
        docker_image = strip_cr_registry_prefix(docker_image)

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
        return self.repository == DEMISTO_REPOSITORY

    @property
    def is_demistoextended_repository(self) -> bool:
        return self.repository == DEMISTO_EXTENDED_REPOSITORY

    @property
    def is_trusted_repository(self) -> bool:
        return self.repository in {DEMISTO_REPOSITORY, DEMISTO_EXTENDED_REPOSITORY}

    @property
    def is_python3_image(self) -> bool:
        return self.is_demisto_repository and self.image_name == "python3"

    @property
    def is_native_image(self) -> bool:
        return self.name == NATIVE_IMAGE_DOCKER_NAME

    @property
    def creation_date(self) -> datetime:
        return self._get_client().get_docker_image_tag_creation_date(
            self.name, tag=self.tag
        )

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
            image_env = self._get_client().get_image_env(self.name, tag=self.tag)

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

        else:
            logger.debug(
                f"docker-image {self} is not valid, could not get its python-version"
            )
        return None

    @property
    def is_image_exist(self) -> bool:
        """
        Returns True if the docker-image exist in the configured registry
        """
        return self._get_client().is_docker_image_exist(self.name, tag=self.tag)

    @property
    def latest_tag(self) -> Version:
        return self._get_client().get_latest_docker_image_tag(self.name)

    @property
    def latest_docker_image(self) -> "DockerImage":
        """
        Returns the docker image with the latest tag
        """
        return DockerImage(self._get_client().get_latest_docker_image(self.name))
