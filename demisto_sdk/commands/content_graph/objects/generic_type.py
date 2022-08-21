from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericType(ContentItem):
    description: str = Field(alias='details')
    definition_id: str = Field(alias='definitionId')
