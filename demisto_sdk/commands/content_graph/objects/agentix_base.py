from typing import Optional

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class AgentixBase(ContentItem):
    tags: Optional[list[str]] = None
    category: Optional[str] = None
    version: int = -1
    description: str
    display_name: str
    disabled: bool = False
