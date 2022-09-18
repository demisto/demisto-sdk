from typing import Set
from pydantic import Field
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Job(ContentItem):
    description: str = Field(alias='details')

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'details'}
