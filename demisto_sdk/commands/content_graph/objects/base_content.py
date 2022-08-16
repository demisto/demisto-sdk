from abc import abstractmethod, ABC
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContent(ABC, BaseModel):
    # parsing_object: bool = Field(False, exclude=True)
    object_id: str = Field('', alias='id')
    content_type: ContentTypes = ContentTypes.BASE_CONTENT
    deprecated: bool = False
    marketplaces: List[MarketplaceVersions] = []
    node_id: str = ''
    
    # def __init__(self, **data) -> None:
    #     super().__init__(**data)
    #     self.parsing_object = self.node_id == ''

    @validator("node_id", always=True)
    def set_node_id(cls, v, values, **kwargs) -> str:
        """
        Set node id by the content_type and id
        """
        return v or f'{values.get("content_type")}:{values.get("id")}'
    
    class Config:
        arbitrary_types_allowed = True
        orm_mode = True
        allow_population_by_field_name = True
