from tempfile import NamedTemporaryFile
from typing import Optional, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorIncidentField(ContentItem):
    cli_name: str = Field(alias="cliName")
    object_id: str = Field(alias="id")
    field_type: str = Field(alias="type")
    select_values: list = Field(None, alias="selectValues")
    content: bool = Field(None, exclude=True)
    system: bool = Field(None, exclude=True)
    group: int = Field(None, exclude=True)
    unsearchable: Optional[bool] = Field(None, exclude=True)
    version: Optional[int] = 0
    required: bool = Field(None, alias="required")
    associated_types: list = Field(None, alias="associatedTypes")

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

    def metadata_fields(self) -> Set[str]:
        return super().metadata_fields().union({"field_type"})
