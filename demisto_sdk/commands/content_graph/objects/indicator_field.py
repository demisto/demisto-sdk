from typing import Optional, Set

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.indicator_incident_field import (
    IndicatorIncidentField,
)


class IndicatorField(IndicatorIncidentField, content_type=ContentType.INDICATOR_FIELD):  # type: ignore[call-arg]
    type: str
    associated_to_all: bool = Field(alias="associatedToAll")

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        summary["id"] = f"indicator_{self.object_id}"
        return summary

    def metadata_fields(self) -> Set[str]:
        return super().metadata_fields().union({"type"})
