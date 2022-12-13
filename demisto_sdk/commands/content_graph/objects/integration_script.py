import logging
from typing import Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.integration_script_unifier import IntegrationScriptUnifier

yaml = YAML_Handler()

logger = logging.getLogger("demisto-sdk")


class IntegrationScript(ContentItem):
    type: str
    docker_image: Optional[str]
    description: Optional[str]
    is_unified: bool = Field(False, exclude=True)

    def prepare_for_upload(self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs) -> dict:
        if not kwargs.get('unify_only'):
            data = super().prepare_for_upload(marketplace)
        else:
            data = self.data
        data = IntegrationScriptUnifier.unify(self.path, data, marketplace, **kwargs)
        return data
