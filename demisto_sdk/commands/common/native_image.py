import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import extract_docker_image_from_text, get_dict_from_file

json = JSON_Handler()
logger = logging.getLogger('demisto-sdk')


class NativeImage(BaseModel):
    supported_docker_images: List[str]
    docker_ref: str


class IgnoredContentItem(BaseModel):
    id: str
    reason: str
    ignored_native_images: List[str]


class NativeImageConfig(BaseModel):
    native_images: Dict[str, NativeImage]
    ignored_content_items: List[IgnoredContentItem]


def load_native_image_config(native_image_config_file_path: Optional[str] = None) -> Dict:
    if not native_image_config_file_path:
        native_image_config_file_path = 'Tests/docker_native_image_config.json'

    native_image_config_content, _ = get_dict_from_file(native_image_config_file_path)
    return native_image_config_content


def file_to_native_image_config(native_image_config_file_path: Optional[str] = None) -> NativeImageConfig:
    return NativeImageConfig.parse_obj(load_native_image_config(native_image_config_file_path))


def extract_native_image_version_for_server(native_image: str) -> str:
    return native_image.replace('native:', '')


def docker_images_to_native_images_support(native_images: Dict[str, NativeImage]) -> Dict[str, List[str]]:
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
    docker_images_to_native_images_mapping: Dict = {}

    for native_image_name, native_image in native_images.items():
        for supported_docker_image in native_image.supported_docker_images:
            if supported_docker_image not in docker_images_to_native_images_mapping:
                docker_images_to_native_images_mapping[supported_docker_image] = []
            docker_images_to_native_images_mapping[supported_docker_image].append(
                extract_native_image_version_for_server(native_image_name)
            )

    return docker_images_to_native_images_mapping


class NativeImageSupportedVersions:

    """
    Class that defines which native images should be supported in a script/integration by the following criteria(s):

    1) if the docker-image that the integration/script uses is supported in the native image(s)
    2) if the integration/script is not ignored in the configuration file.

    Args:
        _id (str): the ID that the script/integration has.
        docker_image (str): the docker image that the integration/script uses. (dockerimage key in the yml).
        native_image_config_file_path (str): a path to the native image configuration file, if not provided
            will assume the running path is the content repo root.
    """

    def __init__(
        self,
        _id: str,
        docker_image: Optional[str],
        native_image_config: Optional[NativeImageConfig] = None,
        native_image_config_file_path: Optional[str] = None
    ):
        self.id = _id
        self.docker_image = extract_docker_image_from_text(
            text=docker_image, with_no_tag=True
        ) if docker_image else docker_image
        self.native_image_config = native_image_config or file_to_native_image_config(native_image_config_file_path)

    def image_to_native_images_support(
        self, docker_images_to_native_images_mapping: Optional[Dict[str, List[str]]] = None
    ) -> List[str]:
        """
        Get the mapping the script/integration to the native-images which support it.

        Args:
            docker_images_to_native_images_mapping (dict): a mapping between docker images to
                the native-images in which they are supported.
        """
        if docker_images_to_native_images_mapping:
            return docker_images_to_native_images_mapping.get(self.docker_image) or []

        return docker_images_to_native_images_support(
            self.native_image_config.native_images
        ).get(self.docker_image) or []

    def get_ignored_native_images(self):
        """
        Get a list of native images which should be ignored for an integration/script.
        """
        ignored_content_items = self.native_image_config.ignored_content_items or []
        for ignored_content_item in ignored_content_items:
            if self.id == ignored_content_item.id:
                ignored_native_images = ignored_content_item.ignored_native_images
                reason = ignored_content_item.reason
                logger.debug(
                    f'content item ID: {self.id} cannot run with these native '
                    f'images: {ignored_native_images}, reason: {reason}'
                )
                return [extract_native_image_version_for_server(native_image) for native_image in ignored_native_images]
        return []

    def get_supported_native_image_versions(
        self, docker_images_to_native_images_mapping: Optional[Dict[str, List[str]]] = None
    ) -> List[str]:
        """
        Get the native-images that the integration/script supports. Disregards native-images that are supported which
        should be ignored.
        """
        if native_images := self.image_to_native_images_support(docker_images_to_native_images_mapping):
            # in case there is a script/integration that should be ignored on a specific native image,
            # the native image(s) which doesn't support him will be removed.
            ignored_native_images = self.get_ignored_native_images()
            return [native_image for native_image in native_images if native_image not in ignored_native_images]
        return []
