from typing import Optional, Set
from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Widget(ContentItem):
    widget_type: str = Field(alias='widgetType')
    data_type: Optional[str] = Field(alias='dataType')

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'dataType', 'widgetType'}
