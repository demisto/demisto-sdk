from pydantic import Field
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Widget(ContentItem):
    data_type: str = Field(alias='dataType')
    widget_type: str = Field(alias='widgetType')
