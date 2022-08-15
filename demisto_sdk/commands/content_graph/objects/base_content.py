from pydantic import BaseModel, Field
from typing import List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContent(BaseModel):
    should_parse_object: bool = False
    node_id: str = ''
    object_id: str = Field('', alias='id')
    content_type: ContentTypes = ContentTypes.BASE_CONTENT
    deprecated: bool = False
    marketplaces: List[MarketplaceVersions] = []

    def __post_init__(self):
        self.should_parse_object = self.node_id == ''

    def get_node_id(self) -> str:
        if not self.content_type or not self.object_id:
            raise ValueError(
                f'Missing content type ("{self.content_type}") or object ID ("{self.object_id}")'
            )
        return f'{self.content_type}:{self.object_id}'
