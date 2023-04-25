from typing import Callable, List, Optional, Set

import demisto_client
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

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_reputation_handler  # TODO check file name
