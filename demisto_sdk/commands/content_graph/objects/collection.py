from pathlib import Path
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Collection(ContentItem, content_type=ContentType.COLLECTION):  # type: ignore[call-arg]
    display_name: str = Field("", alias="display")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            "display" in _dict
            and "supportedModules" in _dict
            and path.suffix == ".yml"
        ):
            return True
        return False
