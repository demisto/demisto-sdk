import json
import os
from pathlib import Path
from typing import Any, Dict

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface

USE_DOCKER = not os.getenv('CI', False)


class PackDependencies:
    def __init__(self, content_graph: ContentGraphInterface, marketplace: MarketplaceVersions, output_path: Path) -> None:
        self.content_graph = content_graph
        self.marketplace = marketplace
        self.output_path = Path(output_path)

    def run(self) -> None:
        self.content_graph.create_pack_dependencies()
        with self.output_path.open('w') as f:
            json.dump(self._get_packs_dependencies(), f, indent=4)

    def _get_packs_dependencies(self) -> Dict[str, Any]:
        all_level_dependencies = self.content_graph.get_all_level_dependencies(self.marketplace)
        first_level_dependencies = self.content_graph.get_first_level_dependencies(self.marketplace)
        packs = {pack.object_id: pack for pack in self.content_graph.get_packs(self.marketplace)}
        for pack_id in all_level_dependencies:
            all_level_dependencies[pack_id]['dependencies'] = first_level_dependencies[pack_id]
            all_level_dependencies[pack_id]['displayedImages'] = [
                integration.object_id for integration in packs[first_level_dependencies[pack_id]].content_items.integration
            ]
        return all_level_dependencies
