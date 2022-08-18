from pydantic import Field
from typing import List, Optional

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorType(ContentItem):
    description: str = Field(alias='details')
    regex: str
    reputation_script_names: Optional[str] = Field(alias='reputationScriptName')  # TODO change to `name`
    enhancement_script_names: Optional[List[str]] = Field(alias='enhancementScriptNames')
