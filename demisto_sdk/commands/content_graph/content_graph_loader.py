from typing import Dict, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_content_path
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import Repository


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
        packs: List[Pack] = self.content_graph.search_nodes(self.marketplace, content_type=ContentType.PACK)
        id_to_obj: Dict[int, BaseContent] = {}
        for pack in packs:
            id_to_obj[pack.element_id] = pack
            for content_item in pack.content_items:
                id_to_obj[content_item.element_id] = content_item
        self.content_graph._id_to_obj = id_to_obj
        return Repository(path=get_content_path(), packs=packs)
