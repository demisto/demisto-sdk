from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorField(ContentItem):
    cli_name: str = Field(alias='cliName')
    type: str
    associated_to_all: bool = Field(alias='associatedToAll')
