import json
from abc import ABC
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType


class BaseContent(ABC, BaseModel):
    object_id: str = Field(alias='id')
    content_type: ContentType
    marketplaces: List[MarketplaceVersions]
    node_id: str

    class Config:
        arbitrary_types_allowed = True  # allows having custom classes for properties in model
        orm_mode = True  # allows using from_orm() method
        allow_population_by_field_name = True  # when loading from orm, ignores the aliases and uses the property name

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.json())
