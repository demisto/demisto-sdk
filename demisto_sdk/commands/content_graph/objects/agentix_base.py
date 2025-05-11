from typing import Optional

from pydantic import Field
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class AgentixBase(ContentItem):
    is_enabled: bool = Field(..., alias="isEnabled")  # TODO - should be removed?
    tags: Optional[list[str]]
    category: Optional[str] = Field(..., alias="category")
    version: Optional[int] = 0
    description: str
