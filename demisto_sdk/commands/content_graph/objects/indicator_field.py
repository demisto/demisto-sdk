from typing import Set

from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorField(ContentItem, content_type=ContentType.INDICATOR_FIELD):
    cli_name: str = Field(alias='cliName')
    type: str
    associated_to_all: bool = Field(alias='associatedToAll')

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'type', 'description'}
