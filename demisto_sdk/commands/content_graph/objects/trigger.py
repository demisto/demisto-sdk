from pathlib import Path

from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class Trigger(ContentItemXSIAM, content_type=ContentType.TRIGGER):  # type: ignore[call-arg]
    automation_type: str = Field(default=None)
    automation_id: str = Field(default=None)
    grouping_element: Optional[str] = Field(None)
    is_auto_enabled: bool = Field(False)

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "trigger_id" in _dict and path.suffix == ".json":
            return True
        return False
