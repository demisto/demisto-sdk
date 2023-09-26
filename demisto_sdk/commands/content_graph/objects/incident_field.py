from typing import Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.indicator_incident_field import (
    IndicatorIncidentField,
)

json = JSON_Handler()


class IncidentField(IndicatorIncidentField, content_type=ContentType.INCIDENT_FIELD):  # type: ignore[call-arg]
    associated_to_all: bool = Field(False, alias="associatedToAll")

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        summary["id"] = f"incident_{self.object_id}"
        return summary
