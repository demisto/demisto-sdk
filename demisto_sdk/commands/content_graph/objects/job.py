from typing import Set
from pydantic import Field
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Job(ContentItem, content_type=ContentType.JOB):
    description: str = Field(alias='details')

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'details'}
