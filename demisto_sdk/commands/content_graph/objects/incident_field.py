from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentField(ContentItem):
    cli_name: str = Field(alias='cliName')
    field_type: str = Field(alias='type')
    associated_to_all: bool = Field(False, alias='associatedToAll')
