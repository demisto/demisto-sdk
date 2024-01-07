import re
from pathlib import Path
from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    NATIVE_IMAGE_FILE_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.docker_helper import (
    get_python_version,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
)
from demisto_sdk.commands.content_graph.common import lazy_property
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


class DockerImage:
    def __init__(
        self,
        repository: str = "",
        image_name: str = "",
        tag: str = "",
    ):
        self.repository = repository  # the repository e.g.: demisto
        self.image_name = image_name  # the image name e.g.: python3, pan-os-python
        self.tag = tag  # the tag

    @property
    def name(self):
        """
        Returns the repositroy + image name. .e.g: demisto/python3, demisto/pan-os-python
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
        return self.name == "demisto/py3-native"

    def __str__(self):
        return f"{self.repository}/{self.image_name}:{self.tag}"

    @classmethod
    def from_regex(cls, docker_image: str) -> "DockerImage":
        pattern = re.compile(r"^([^/]+)/(.*?)(?::(.*))?$")
        if matches := pattern.match(docker_image):
            return cls(matches.group(1), matches.group(2), matches.group(3))
        else:
            return cls()


class IntegrationScript(ContentItem):
    type: str
    subtype: Optional[str]
    docker_image: Optional[str]
    alt_docker_images: List[str] = []
    description: Optional[str] = Field("")
    is_unified: bool = Field(False, exclude=True)
    code: Optional[str] = Field(None, exclude=True)
    unified_data: dict = Field(None, exclude=True)

    @lazy_property
    def python_version(self) -> Optional[str]:
        """
        Get the python version from the script/integration docker-image in case it's a python image
        """
        if self.type == "python" and (
            python_version := get_python_version(self.docker_image)
        ):
            return str(python_version)

        return None

    @property
    def docker_images(self) -> List[str]:
        return [self.docker_image] + self.alt_docker_images if self.docker_image else []

    @property
    def docker_image_object(self) -> DockerImage:

        if self.docker_image:
            return DockerImage.from_regex(self.docker_image)

        raise ValueError(f"The content item {self.path} does not have docker image")

    @property
    def is_powershell(self) -> bool:
        return self.type == "powershell"

    @property
    def is_javascript(self) -> bool:
        return self.type == "javascript"

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        data = (
            self.data
            if kwargs.get("unify_only")
            else super().prepare_for_upload(current_marketplace)
        )
        data = IntegrationScriptUnifier.unify(
            self.path, data, current_marketplace, **kwargs
        )
        self.unified_data = data
        return data

    def get_supported_native_images(
        self, marketplace: MarketplaceVersions, ignore_native_image: bool = False
    ) -> List[str]:
        if not ignore_native_image:
            if not Path(f"Tests/{NATIVE_IMAGE_FILE_NAME}").exists():
                logger.debug(f"The {NATIVE_IMAGE_FILE_NAME} file could not be found.")
                return []
            return ScriptIntegrationSupportedNativeImages(
                _id=self.object_id,
                docker_image=self.docker_image,
                native_image_config=NativeImageConfig.get_instance(),
            ).get_supported_native_image_versions(get_raw_version=True)
        return []
