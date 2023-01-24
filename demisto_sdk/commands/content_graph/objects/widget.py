from typing import Optional, Set

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.layout import (
    fix_widget_incident_to_alert,
)


class Widget(ContentItem, content_type=ContentType.WIDGET):  # type: ignore[call-arg]
    widget_type: str = Field(alias="widgetType")
    data_type: Optional[str] = Field(alias="dataType")

    def metadata_fields(self) -> Set[str]:
        return {"name", "data_type", "widget_type"}

    def prepare_for_upload(
        self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs
    ) -> dict:
        data = super().prepare_for_upload(marketplace, **kwargs)
        if marketplace == MarketplaceVersions.MarketplaceV2:
            data = fix_widget_incident_to_alert(data)
        return data
