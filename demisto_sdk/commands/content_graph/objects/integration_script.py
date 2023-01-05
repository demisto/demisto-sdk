import logging
from pathlib import Path
from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    NATIVE_IMAGE_FILE_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.native_image import (
    ScriptIntegrationSupportedNativeImages,
    file_to_native_image_config,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)

yaml = YAML_Handler()

logger = logging.getLogger("demisto-sdk")


class IntegrationScript(ContentItem):
    type: str
    docker_image: Optional[str]
    description: Optional[str]
    is_unified: bool = Field(False, exclude=True)

    def prepare_for_upload(
        self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs
    ) -> dict:
        if not kwargs.get("unify_only"):
            data = super().prepare_for_upload(marketplace)
        else:
            data = self.data

        data = IntegrationScriptUnifier.unify(self.path, data, marketplace, **kwargs)
        return data

    def get_supported_native_images(
        self, marketplace: MarketplaceVersions, ignore_native_image: bool = False
    ) -> List[str]:
        if marketplace == MarketplaceVersions.XSOAR and not ignore_native_image:
            if not Path(f"Tests/{NATIVE_IMAGE_FILE_NAME}").exists():
                logger.debug(f"The {NATIVE_IMAGE_FILE_NAME} file could not be found.")
                return []
            return ScriptIntegrationSupportedNativeImages(
                _id=self.object_id,
                docker_image=self.docker_image,
                native_image_config=file_to_native_image_config(),
            ).get_supported_native_image_versions(get_raw_version=True)
        return []
