from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

from demisto_sdk.commands.common.content_constant_paths import NATIVE_IMAGE_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.singleton import PydanticSingleton
from demisto_sdk.commands.common.tools import extract_docker_image_from_text


class NativeImage(BaseModel):
    supported_docker_images: List[str]
    docker_ref: Optional[str]


class IgnoredContentItem(BaseModel):
    id: str
    reason: str
    ignored_native_images: List[str]


def _extract_native_image_version_for_server(native_image: str) -> str:
    return native_image.replace("native:", "")


class NativeImageConfig(PydanticSingleton, BaseModel):
    native_images: Dict[str, NativeImage]
    ignored_content_items: List[IgnoredContentItem]
    flags_versions_mapping: Dict[str, str] = {}
    docker_images_to_native_images_mapping: Dict[str, List] = {}

    @classmethod
    def get_instance_from(cls, *args, **kwargs):
        return cls.from_path(*args, **kwargs)

    @classmethod
    def from_path(cls, native_image_config_file_path: Path = Path(NATIVE_IMAGE_PATH)):
        native_image_config = cls.parse_file(native_image_config_file_path)
        native_image_config.__docker_images_to_native_images_support()
        return native_image_config

    def __docker_images_to_native_images_support(self):
        """
        Map all the docker images from the native image configuration file into the native-images which support it.

        Examples:
           {
               "chromium": ["8.1", "8.2"],
               "tesseract": ["8.1"]
           }

           chromium docker image is supported in both 8.1.0, 8.2.0 native images
           while tesseract is only supported in 8.1.0
        """
        for native_image_name, native_image_obj in self.native_images.items():
            for supported_docker_image in native_image_obj.supported_docker_images:
                if (
                    supported_docker_image
                    not in self.docker_images_to_native_images_mapping
                ):
                    self.docker_images_to_native_images_mapping[
                        supported_docker_image
                    ] = []
                self.docker_images_to_native_images_mapping[
                    supported_docker_image
                ].append(native_image_name)

    def get_native_image_reference(self, native_image) -> Optional[str]:
        """
        Gets the docker reference of the given native image

        Args:
            native_image (str): native image (for example: 'native:8.1')

        Returns: The docker ref
        """
        if native_image_obj := self.native_images.get(native_image):
            return native_image_obj.docker_ref

        return None


class ScriptIntegrationSupportedNativeImages:

    """
    Class that defines which native images should be supported in a script/integration by the following criteria(s):

    1) if the docker-image that the integration/script uses is supported in the native image(s)
    2) if the integration/script is not ignored in the configuration file.

    Args:
        _id (str): the ID that the script/integration has.
        docker_image (str): the docker image that the integration/script uses. (dockerimage key in the yml).
    """

    NATIVE_DEV = "native:dev"
    NATIVE_CANDIDATE = "native:candidate"

    def __init__(
        self,
        _id: str,
        native_image_config: NativeImageConfig,
        docker_image: Optional[str] = None,
    ):
        self.id = _id
        self.docker_image = (
            extract_docker_image_from_text(text=docker_image, with_no_tag=True)
            if docker_image
            else docker_image
        )
        self.native_image_config = native_image_config

    def __docker_image_to_native_images_support(self) -> List[str]:
        """
        Get the mapping the script/integration to the native-images which support it.
        """
        return (
            self.native_image_config.docker_images_to_native_images_mapping.get(
                self.docker_image
            )
            or []
        )

    def __get_ignored_native_images(self):
        """
        Get a list of native images which should be ignored for an integration/script.
        """
        ignored_content_items = self.native_image_config.ignored_content_items or []
        for ignored_content_item in ignored_content_items:
            if self.id == ignored_content_item.id:
                ignored_native_images = ignored_content_item.ignored_native_images
                reason = ignored_content_item.reason
                logger.debug(
                    f"content item ID: {self.id} cannot run with these native "
                    f"images: {ignored_native_images}, reason: {reason}"
                )
                return ignored_native_images
        return []

    def get_supported_native_image_versions(
        self, get_raw_version: bool = False, only_production_tags: bool = True
    ) -> List[str]:
        """
        Get the native-images that the integration/script supports. Disregards native-images that should be ignored.

        Args:
            get_raw_version (bool): whether to extract the raw server version from the native image name, for example:
                                    'native:8.2' will become '8.2' for each one of the native-images that are supported.
            only_production_tags (bool): whether to ignore the latest native image.
        """
        if native_images := self.__docker_image_to_native_images_support():
            # in case there is a script/integration that should be ignored on a specific native image,
            # the native image(s) which doesn't support it will be removed.
            ignored_native_images = self.__get_ignored_native_images()
            native_images = [
                native_image
                for native_image in native_images
                if native_image not in ignored_native_images
            ]

            if only_production_tags:
                if self.NATIVE_DEV in native_images:
                    native_images.remove(self.NATIVE_DEV)
                if self.NATIVE_CANDIDATE in native_images:
                    native_images.remove(self.NATIVE_CANDIDATE)

            if get_raw_version:
                return list(
                    map(_extract_native_image_version_for_server, native_images)
                )
            return native_images
        return []
