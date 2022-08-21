from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import Repository


class ContentGraphLoader:

    def __init__(self, marketplace: MarketplaceVersions, content_graph: ContentGraphInterface) -> None:
        """_summary_

        Args:
            marketplace (MarketplaceVersions): _description_
            content_graph (ContentGraphInterface): _description_
        """
        self.marketplace = marketplace
        self.content_graph = content_graph

    def load(self) -> Repository:

        packs = []
        for pack_dict in self.content_graph.get_packs_content_items(self.marketplace):
            content_items = pack_dict.pop('content_items')
            content_items_dct = {}
            for content_item in content_items:
                content_items_dct.setdefault(content_item['content_type'], []).append(content_item)
            pack_dict['contentItems'] = content_items_dct
            packs.append(Pack(**pack_dict))
            
        return Repository(packs=packs)
                