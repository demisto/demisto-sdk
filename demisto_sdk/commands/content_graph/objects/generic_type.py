from typing import Optional, Set
from pydantic import Field
from demisto_sdk.commands.content_graph.common import ContentType

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericType(ContentItem, content_type=ContentType.GENERIC_TYPE):
    definition_id: Optional[str] = Field(alias='definitionId')

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'details'}

# TODO no generic_field, no pre-proccess rule
