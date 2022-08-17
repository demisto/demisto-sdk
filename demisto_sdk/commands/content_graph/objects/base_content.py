from abc import abstractmethod, ABC
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContent(ABC, BaseModel):
    object_id: str = Field(alias='id')
    content_type: ContentTypes
    marketplaces: List[MarketplaceVersions] = []
    node_id: str    
    class Config:
        arbitrary_types_allowed = True
        orm_mode = True
        allow_population_by_field_name = True
