from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Mapper(ContentItem):
    type: Optional[str]
    definition_id: Optional[str] = Field(alias='definitionId')  # TODO decide if this should be optional or not
