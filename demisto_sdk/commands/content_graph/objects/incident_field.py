from tempfile import NamedTemporaryFile
from typing import Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

json = JSON_Handler()


class IncidentField(ContentItem, content_type=ContentType.INCIDENT_FIELD):  # type: ignore[call-arg]
    cli_name: str = Field(alias="cliName")
    field_type: str = Field(alias="type")
    associated_to_all: bool = Field(False, alias="associatedToAll")

    def metadata_fields(self) -> Set[str]:
        return {"name", "field_type", "description"}

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        with NamedTemporaryFile(suffix=".json", mode="r+") as file:
            json.dump(
                # Wrapping the data as the server expects to receive it
                {"incidentFields": [self.prepare_for_upload(marketplace=marketplace)]},
                file,
            )
            file.flush()
            file.seek(0)
            return client.import_incident_fields(file=file.name)
