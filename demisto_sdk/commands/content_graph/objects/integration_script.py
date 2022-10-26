import logging
from pathlib import Path
from typing import Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier

yaml = YAML_Handler()

logger = logging.getLogger("demisto-sdk")


class IntegrationScript(ContentItem):
    type: str
    docker_image: Optional[str]
    description: Optional[str]
    is_unified: bool = Field(False, exclude=True)

    def dump(self, dir: Path, marketplace: MarketplaceVersions) -> None:
        if self.is_unified:
            super().dump(dir, marketplace)
            return
        dir.mkdir(exist_ok=True, parents=True)
        try:
            IntegrationScriptUnifier(
                input=str(self.path.parent), output=str(dir), marketplace=marketplace
            ).unify()
        except Exception as e:
            logger.debug(
                f"Failed to unify {self.path} to {dir}, probably already unified. Error message: {e}"
            )
            super().dump(dir, marketplace)
