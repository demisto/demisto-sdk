import logging
from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript

logger = logging.getLogger('demisto-sdk')


class Script(IntegrationScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    tags: List[str]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description", "tags"}

    def dump(self, dir: Path, marketplace: MarketplaceVersions) -> None:
        if self.is_test:
            return
        return super().dump(dir, marketplace)

    def prepare_for_upload(self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs) -> dict:
        data = super().prepare_for_upload(marketplace, **kwargs)

        if supported_native_images := self.get_supported_native_images(
            marketplace=marketplace,
            native_image_config_file_path=kwargs.get('native_image_config_file_path'),
            ignore_native_image=kwargs.get('ignore_native_image') or False
        ):
            data['nativeImage'] = supported_native_images

        return data
