from pydantic import Field
from typing import List, Optional, Set

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorType(ContentItem):
    description: str = Field(alias='details')
    regex: str
    reputation_script_name: Optional[str] = Field(alias='reputationScriptName')
    enhancement_script_names: Optional[List[str]] = Field(alias='enhancementScriptNames')

    def included_in_metadata(self) -> Set[str]:
        return {'details', 'reputationScriptName', 'enhancementScriptNames'}
