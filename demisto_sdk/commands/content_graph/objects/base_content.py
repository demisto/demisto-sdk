from pydantic import BaseModel, Field
from typing import List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContent(BaseModel):
    node_id: str
    item_id: str = Field(None, alias='id')
    content_type: ContentTypes
    deprecated: bool
    marketplaces: List[MarketplaceVersions]

    def __post_init__(self):
        self.node_id = self.node_id or f'{self.content_type}:{self.item_id}'
