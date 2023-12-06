from pathlib import Path
from typing import Optional

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericDefinition(ContentItem, content_type=ContentType.GENERIC_DEFINITION):  # type: ignore[call-arg]
    @staticmethod
    def match(_dict: dict, path: Path) -> Optional[ContentType]:
        if "auditable" in _dict:
            return ContentType.GENERIC_DEFINITION
        return None
