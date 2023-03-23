from typing import List, Optional, Set

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.preparers.replace_layout_incident_alert import (
    replace_layout_incident_alert,
)


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
        # marketplace is the marketplace for which the content is prepared.
        data = super().prepare_for_upload(marketplace, **kwargs)
        data = self._fix_from_and_to_server_version(data)

        if (
            marketplace == MarketplaceVersions.MarketplaceV2
            and self.group == "indicator"
        ):
            data = replace_layout_incident_alert(data)

        return data

    def _fix_from_and_to_server_version(self, data: dict) -> dict:
        # On Layouts, we manually add the `fromServerVersion`, `toServerVersion` fields, see CIAC-5195.
        data["fromServerVersion"] = self.fromversion
        data["toServerVersion"] = self.toversion
        return data
