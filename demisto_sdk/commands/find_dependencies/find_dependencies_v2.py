import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.content_graph_commands import \
    marshal_content_graph
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import Repository

USE_DOCKER = not os.getenv('CI', False)


class PackDependencies:
    def __init__(
        self,
        content_graph: ContentGraphInterface,
        marketplace: MarketplaceVersions,
        output_path: Path,
        repository: Optional[Repository] = None
    ) -> None:
        self.content_graph = content_graph
        self.marketplace = marketplace
        self.output_path = Path(output_path)
        if not repository:
            repository = marshal_content_graph(content_graph, marketplace)
        self.repository = repository

    def run(self) -> None:
        self.content_graph.create_pack_dependencies()
        with self.output_path.open('w') as f:
            json.dump(self._get_packs_dependencies(), f, indent=4)

    def _get_packs_dependencies(self) -> Dict[str, Any]:
        all_level_dependencies = self.content_graph.get_all_level_dependencies(self.marketplace)
        first_level_dependencies = self.content_graph.get_first_level_dependencies(self.marketplace)
        packs = {pack.name: pack for pack in self.repository.packs}
        for pack_id in all_level_dependencies:
            first_level_packs = first_level_dependencies[pack_id]
            all_level_dependencies[pack_id]['dependencies'] = first_level_packs
            first_level_pack_ids = list(first_level_packs.keys())
            displayed_images = []
            for pack_first_level_id in first_level_pack_ids:
                if pack_first_level_id not in packs:
                    continue
                displayed_images.extend(
                    [integration.object_id for integration in packs[pack_first_level_id].content_items.integration]
                )
            all_level_dependencies[pack_id]['displayedImages'] = displayed_images

        return all_level_dependencies
