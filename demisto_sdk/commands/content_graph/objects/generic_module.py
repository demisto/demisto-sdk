from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericModule(ContentItem):
    definition_ids: Optional[List[str]] = Field(alias='definitionIds')
