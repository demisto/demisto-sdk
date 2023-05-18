from typing import Callable, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorField(ContentItem, content_type=ContentType.INDICATOR_FIELD):  # type: ignore[call-arg]
    cli_name: str = Field(alias="cliName")
    type: str
    associated_to_all: bool = Field(alias="associatedToAll")

    def metadata_fields(self) -> Set[str]:
        return {"name", "type", "description"}

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_incident_fields
