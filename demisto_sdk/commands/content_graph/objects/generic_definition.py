from pathlib import Path
from typing import Optional

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericDefinition(ContentItem, content_type=ContentType.GENERIC_DEFINITION):  # type: ignore[call-arg]
    version: Optional[int] = 0

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "auditable" in _dict and path.suffix == ".json":
            return True
        return False
