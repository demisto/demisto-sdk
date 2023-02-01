from typing import List, Optional, Set

from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IndicatorType(ContentItem, content_type=ContentType.INDICATOR_TYPE):  # type: ignore[call-arg]
    description: str = Field(alias="details")
    regex: Optional[str]
    reputation_script_name: Optional[str] = Field(alias="reputationScriptName")
    enhancement_script_names: Optional[List[str]] = Field(
        alias="enhancementScriptNames"
    )

    def metadata_fields(self) -> Set[str]:
        return {"details", "reputation_script_name", "enhancement_script_names"}
