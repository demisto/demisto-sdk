from typing import Optional, Set

from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Widget(ContentItem, content_type=ContentType.WIDGET):  # type: ignore[call-arg]
    data_type: Optional[str] = Field(alias="dataType")
    widget_type: str = Field(alias="widgetType")

    def metadata_fields(self) -> Set[str]:
        return {"object_id", "name", "data_type", "widget_type", "fromversion", "toversion"}
