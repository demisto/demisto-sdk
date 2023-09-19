from tempfile import NamedTemporaryFile

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

json = JSON_Handler()


class IndicatorIncidentField(ContentItem):
    cli_name: str = Field(alias="cliName")
    associated_to_all: bool = Field(alias="associatedToAll")

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
