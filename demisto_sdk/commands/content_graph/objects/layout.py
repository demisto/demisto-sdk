from pydantic import Field
from typing import List, Optional, Set
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Layout(ContentItem):
    kind: Optional[str]
    tabs: Optional[List[str]]
    definition_id: Optional[str] = Field(alias='definitionId')
    group: str
    edit: bool
    indicators_details: bool
    indicators_quick_view: bool
    quick_view: bool
    close: bool
    details: bool
    details_v2: bool
    mobile: bool

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'description'}
