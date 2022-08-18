from pydantic import Field
from typing import List, Optional
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentType(ContentItem):
    playbook: Optional[str]
    hours: int
    days: int
    weeks: int
    closure_script: Optional[str] = Field(alias='closureScript')
    reputation_script_name: Optional[str] = Field(alias='reputationScriptName')
    enhancement_script_names: Optional[List[str]] = Field(alias='enhancementScriptNames')
