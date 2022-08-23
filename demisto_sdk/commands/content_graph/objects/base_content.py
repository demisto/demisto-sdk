from abc import ABC, abstractmethod
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContent(ABC, BaseModel):
    object_id: str = Field(alias='id')
    content_type: ContentTypes
    marketplaces: List[MarketplaceVersions]
    node_id: str

    class Config:
        arbitrary_types_allowed = True
        orm_mode = True
        allow_population_by_field_name = True

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.json())

    @abstractmethod
    def dump(self, path: Path) -> None:
        pass
