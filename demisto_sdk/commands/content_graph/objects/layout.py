import re
from logging import getLogger
from typing import List, Optional, Set

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

logger = getLogger("demisto-sdk")
incident_regex = re.compile("\bincident[\bs\\s]", flags=re.IGNORECASE)


class Layout(ContentItem, content_type=ContentType.LAYOUT):  # type: ignore[call-arg]
    kind: Optional[str]
    tabs: Optional[List[str]]
    definition_id: Optional[str] = Field(alias="definitionId")
    group: str
    edit: bool
    indicators_details: bool
    indicators_quick_view: bool
    quick_view: bool
    close: bool
    details: bool
    details_v2: bool
    mobile: bool

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def prepare_for_upload(
        self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs
    ) -> dict:
        data = super().prepare_for_upload(marketplace, **kwargs)
        data["fromServerVersion"] = self.fromversion
        data["toServerVersion"] = self.toversion

        if marketplace == MarketplaceVersions.MarketplaceV2:
            # replaces the word `Incident` with `Alert`, in all places where and _x2 field was not manually specified
            data = replace_incidents_alerts(data)

        return data


def replace_incidents_alerts(data: dict) -> dict:
    """
    XSOAR Incidents are XSIAM Alerts. This replaces them recursively, matching the original case (lower, UPPER, Title)
    """

    def _replace_string(string: str) -> str:
        if not incident_regex.match(string):
            # the word `incident` doesn't appear at all, in any casese
            return string

        for incident_case, alert_case in {
            "incident": "alert",
            "Incident": "Alert",
            "INCIDENT": "ALERT",
        }.items():
            if incident_case in string:
                string = string.replace(incident_case, alert_case)
        return string

    for key, value in data.items():
        if isinstance(value, dict):
            data[key] = replace_incidents_alerts(value)
        elif isinstance(value, list):
            data[key] = list(map(replace_incidents_alerts, value))
        elif isinstance(value, str):
            data[key] = _replace_string(value)

    return data
