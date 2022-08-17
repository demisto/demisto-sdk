from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Mapper(ContentItem):
    type: str
    definition_id: str = Field(alias='definitionId')
    description: str
