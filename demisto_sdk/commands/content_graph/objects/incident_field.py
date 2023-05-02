from typing import Callable, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentField(ContentItem, content_type=ContentType.INCIDENT_FIELD):  # type: ignore[call-arg]
    cli_name: str = Field(alias="cliName")
    field_type: str = Field(alias="type")
    associated_to_all: bool = Field(False, alias="associatedToAll")

    def metadata_fields(self) -> Set[str]:
        return {"name", "field_type", "description"}

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_incident_fields

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        dump_into_list: bool = False,
    ) -> None:
        # sets dump_into_list = True
        return super()._upload(client, marketplace, dump_into_list=True)
