import json
import os
from typing import Any, Dict
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.common.tools import (
    print_error,
    print_success,
    print_warning
)

from demisto_sdk.commands.content_graph.content_graph_commands import load_content_graph
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface


USE_DOCKER = not os.getenv('CI', False)


class PackDependencies:
    def __init__(self, marketplace: MarketplaceVersions, content_graph: ContentGraphInterface) -> None:
        self.marketplace = marketplace
        self.content_graph = content_graph

    def run(self) -> dict:
        self.content_graph.create_pack_dependencies()
        return self.get_packs_dependencies()
        # self.write_output(pack_dependencies_result)

    def get_packs_dependencies(self) -> Dict[str, Any]:
        all_level_dependencies = self.content_graph.get_all_level_dependencies(self.marketplace)
        first_level_dependencies = self.content_graph.get_first_level_dependencies(self.marketplace)
        for pack_id in all_level_dependencies:
            all_level_dependencies[pack_id]['dependencies'] = first_level_dependencies[pack_id]
            all_level_dependencies[pack_id]['displayedImages'] = list(first_level_dependencies[pack_id].keys())
        return all_level_dependencies

