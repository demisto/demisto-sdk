from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, RelationshipData
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
import demisto_sdk.commands.content_graph.objects.base_content as base_content


class PackMetadata(BaseModel):
    name: str
    description: str
    created: str
    updated: str
    support: str
    email: str
    url: str
    author: str
    certification: str
    hidden: bool
    server_min_version: str = Field(alias='serverMinVersion')
    current_version: str = Field(alias='currentVersion')
    tags: List[str]
    categories: List[str]
    use_cases: List[str] = Field(alias='useCases')
    keywords: List[str]
    price: Optional[int] = None
    premium: Optional[bool] = None
    vendor_id: Optional[str] = Field(None, alias='vendorId')
    vendor_name: Optional[str] = Field(None, alias='vendorName')
    preview_only: Optional[bool] = Field(None, alias='previewOnly')

    class Config:
        arbitrary_types_allowed = True


class Pack(base_content.BaseContent, PackMetadata):
    path: Path
    object_id: str
    content_type: ContentTypes = ContentTypes.PACK
    node_id: str
    content_items: Dict[ContentTypes, List[ContentItem]] = Field(alias='contentItems')
    relationships: Dict[Rel, List[RelationshipData]] = Field({}, exclude=True)


