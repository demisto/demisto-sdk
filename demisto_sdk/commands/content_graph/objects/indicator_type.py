from pydantic import Field
from typing import List

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorType(ContentItem):
    description: str = Field(alias='details')
    regex: str
    reputation_script_names: List[str] = Field(alias='reputationScriptName')
    enhancement_script_names: List[str] = Field(alias='enhancementScriptNames')
