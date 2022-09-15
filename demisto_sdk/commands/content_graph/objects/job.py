from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Job(ContentItem):
    description: str = Field(alias='details')
