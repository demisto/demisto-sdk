from pathlib import Path

from demisto_sdk.commands.common.constants import COLLECTIONS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Collection(ContentItem, content_type=ContentType.COLLECTION):  # type: ignore[call-arg]
    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            COLLECTIONS_DIR in path.parts
            and "commonfields" in _dict
            and "script" not in _dict  # not an integration or script
            and "color" not in _dict  # not an AgentixAgent
            and "underlyingcontentitem" not in _dict  # not an AgentixAction
            and path.suffix == ".yml"
        ):
            return True
        return False
