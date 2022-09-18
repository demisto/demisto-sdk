import logging
from pathlib import Path
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.unify.integration_script_unifier import IntegrationScriptUnifier

logger = logging.getLogger('demisto-sdk')


class IntegrationScript(ContentItem):
    type: str
    docker_image: str
    description: str

    def dump(self, dir: Path, marketplace: MarketplaceVersions) -> None:
        # demisto-sdk unify self.path -> path
        dir.mkdir(exist_ok=True, parents=True)
        try:
            IntegrationScriptUnifier(input=self.path.parent, output=str(dir), marketplace=marketplace).unify()
        except Exception as e:
            logger.info(f'Failed to unify {self.path} to {dir}, probably already unified')
            logger.debug(e)
            super().dump(dir, marketplace)
