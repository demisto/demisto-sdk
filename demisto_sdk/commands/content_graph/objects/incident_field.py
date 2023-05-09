from typing import Set

from pydantic import Field
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentField(ContentItem, content_type=ContentType.INCIDENT_FIELD):  # type: ignore[call-arg]
    cli_name: str = Field(alias="cliName")
    field_type: str = Field(alias="type")
    associated_to_all: bool = Field(False, alias="associatedToAll")

    def summary(self, marketplace: MarketplaceVersions | None = None) -> dict:
        summary = super().summary(marketplace)
        summary["id"] = f"incident_{self.object_id}"
        return summary

    def metadata_fields(self) -> Set[str]:
        return {"object_id", "name", "field_type", "description", "fromversion", "toversion"}
