import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.content_graph_commands import \
    marshal_content_graph
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import Repository
from demisto_sdk.commands.content_graph.objects.pack import Pack

from demisto_sdk.commands.content_graph.common import ContentType, Relationship

USE_DOCKER = not os.getenv('CI', False)


class PackDependencies:
    def __init__(
        self,
        content_graph: ContentGraphInterface,
        marketplace: MarketplaceVersions,
        output_path: Path,
    ) -> None:
        self.content_graph = content_graph
        self.marketplace = marketplace
        self.output_path = Path(output_path)

    def run(self) -> None:
        self.content_graph.create_pack_dependencies()
        with self.output_path.open('w') as f:
            json.dump(self._get_packs_dependencies(), f, indent=4)

    def _get_packs_dependencies(self) -> Dict[str, Any]:
        all_level_dependencies: List[Tuple[Pack, dict, List[Pack]]] = self.content_graph.get_connected_nodes_by_relationship_type(
            marketplace=self.marketplace,
            relationship_type=Relationship.DEPENDS_ON,
            content_type_from=ContentType.PACK,
            content_type_to=ContentType.PACK,
            recursive=True,
        )
        first_level_dependencies: List[Tuple[Pack, dict, List[Pack]]] = self.content_graph.get_connected_nodes_by_relationship_type(
            marketplace=self.marketplace,
            relationship_type=Relationship.DEPENDS_ON,
            content_type_from=ContentType.PACK,
            content_type_to=ContentType.PACK,
            recursive=False,
        )
        first_level_dependencies_mapping = {pack.name: depends_packs for pack, _, depends_packs in first_level_dependencies}
        dependencies_mapping = {}
        for pack, rel, depends_packs in all_level_dependencies:
            first_level_packs = first_level_dependencies_mapping[pack.name]
            dependencies_mapping[pack.name]['dependencies'] = [pack.name for pack in first_level_packs]
            dependencies_mapping[pack.name]['allLevelDependencies'] = [pack.name for pack in depends_packs]
            dependencies_mapping[pack.name]['path'] = Path(*pack.path.parts[-2:]).as_posix()
            first_level_pack_ids = [pack.name for pack in first_level_packs]
            displayed_images = []
            for pack_first_level_id in first_level_pack_ids:
                displayed_images.extend(
                    [integration.object_id for integration in pack.content_items.integration]
                )
            all_level_dependencies[pack_id]['displayedImages'] = displayed_images

        return dependencies_mapping
