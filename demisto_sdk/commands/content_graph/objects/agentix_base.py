from datetime import datetime
from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class AgentixBase(BaseContent):
    is_enabled: bool = Field(..., alias="isEnabled")
    pack_id1: str = Field(..., alias="packID")
    pack_name1: str = Field(..., alias="packName")
    tags: Optional[list[str]]
    is_system: bool = Field(..., alias="isSystem")
    is_locked: bool = Field(..., alias="isLocked")
    is_detached: bool = Field(..., alias="isDetached")
    modified: Optional[datetime]
    modified_by: Optional[str] = Field(..., alias="modifiedBy")
    category: Optional[str] = Field(..., alias="modifiedBy")
    _id: str = Field(..., alias="id")
    version: str
    display: str = Field(..., alias="name")
    description: str
