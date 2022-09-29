from typing import Any, Dict, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_content_path
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import Repository
from demisto_sdk.commands.content_graph.objects.pack import Pack


class ContentGraphLoader:

    def __init__(self, marketplace: MarketplaceVersions, content_graph: ContentGraphInterface) -> None:
        """ Initiates a ContentGraphLoader class instance.

        Args:
            marketplace (MarketplaceVersions): The marketplace version.
            content_graph (ContentGraphInterface): The content graph interface object.
        """
        self.marketplace = marketplace
        self.content_graph = content_graph

    def load(self) -> Repository:
        packs: List[Pack] = []
        integrations_to_commands = self.content_graph.get_all_integrations_with_commands()
        for result in self.content_graph.get_packs_content_items(self.marketplace):
            content_items = result['content_items']
            pack = result['pack']
            content_items_dct: Dict[str, Any] = {}
            for content_item in content_items:
                content_item_id = content_item['object_id']
                if (content_type := content_item['content_type']) == ContentType.INTEGRATION:
                    content_item['commands'] = integrations_to_commands.get(content_item_id, [])
                content_items_dct.setdefault(content_type, []).append(content_item)
            pack['content_items'] = content_items_dct
            packs.append(Pack.parse_obj(pack))
        return Repository(path=get_content_path(), packs=packs)
