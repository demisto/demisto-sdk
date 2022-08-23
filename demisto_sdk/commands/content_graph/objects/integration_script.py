from pathlib import Path
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.unify.integration_script_unifier import IntegrationScriptUnifier


class IntegrationScript(ContentItem):
    type: str
    docker_image: str
    description: str
    
    def dump(self, dir: Path, marketplace: MarketplaceVersions) -> None:
        # demisto-sdk unify self.path -> path
        dir.mkdir(exist_ok=True, parents=True)
        IntegrationScriptUnifier(input=self.path, output=dir / super().normalize_file_name(self.path.name), marketplace=marketplace).unify()
