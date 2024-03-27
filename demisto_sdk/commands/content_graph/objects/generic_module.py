from pathlib import Path
from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericModule(ContentItem, content_type=ContentType.GENERIC_MODULE):  # type: ignore[call-arg]
    definition_ids: Optional[List[str]] = Field(alias="definitionIds")
    version: Optional[int] = 0

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "definitionIds" in _dict and "views" in _dict and path.suffix == ".json":
            return True
        return False
