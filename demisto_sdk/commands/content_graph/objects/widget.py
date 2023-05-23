from typing import Callable, Optional, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Widget(ContentItem, content_type=ContentType.WIDGET):  # type: ignore[call-arg]
    widget_type: str = Field(alias="widgetType")
    data_type: Optional[str] = Field(alias="dataType")

    def metadata_fields(self) -> Set[str]:
        return {"name", "data_type", "widget_type"}

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_widget
