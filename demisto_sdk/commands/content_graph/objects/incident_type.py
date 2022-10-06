from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentType(ContentItem):
    playbook: Optional[str]
    hours: int
    days: int
    weeks: int
    closure_script: Optional[str] = Field(alias='closureScript')
