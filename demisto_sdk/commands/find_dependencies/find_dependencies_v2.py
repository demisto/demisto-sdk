import os
from typing import Any, Dict
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface


USE_DOCKER = not os.getenv('CI', False)


class PackDependencies:
    def __init__(self, marketplace: MarketplaceVersions, content_graph: ContentGraphInterface) -> None:
        self.marketplace = marketplace
        self.content_graph = content_graph

    def run(self) -> dict:
        self.content_graph.create_pack_dependencies()
        return self._get_packs_dependencies()

    def _get_packs_dependencies(self) -> Dict[str, Any]:
        first_level_dependencies = self.content_graph.get_first_level_dependencies(self.marketplace)
        for pack_id in first_level_dependencies:
            first_level_dependencies[pack_id]['displayedImages'] = list(first_level_dependencies[pack_id].keys())
        return first_level_dependencies
