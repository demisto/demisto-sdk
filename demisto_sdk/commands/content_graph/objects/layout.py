from pydantic import Field
from typing import List
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Layout(ContentItem):
    kind: str
    description: str
    tabs: List[str]
    definition_id: str = Field(alias='definitionId')
    group: str
    edit: bool
    indicators_details: bool
    indicators_quick_view: bool
    quick_view: bool
    close: bool
    details: bool
    details_v2: bool
    mobile: bool
