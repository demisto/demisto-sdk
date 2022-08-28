from pydantic import Field
from typing import List, Optional, Set

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentType(ContentItem):
    playbook: Optional[str]
    hours: int
    days: int
    weeks: int
    closure_script: Optional[str] = Field(alias='closureScript')

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'playbook', 'closureScript', 'hours', 'days', 'week'}
