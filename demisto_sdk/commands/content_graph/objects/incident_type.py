from dataclasses import Field
from typing import List
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentType(ContentItem):
    playbook: str
    hours: int
    days: int
    weeks: int
    closure_script: str = Field(alias='closureScript')
    reputation_script_name: str = Field(alias='reputationScriptName')
    enhancement_script_names: List[str] = Field(alias='enhancementScriptNames')
