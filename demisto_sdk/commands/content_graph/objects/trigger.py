from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class Trigger(ContentItemXSIAM, content_type=ContentType.TRIGGER):  # type: ignore[call-arg]
    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "trigger_id" in _dict and path.suffix == ".json":
            return True
        return False
