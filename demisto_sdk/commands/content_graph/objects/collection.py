from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Collection(ContentItem, content_type=ContentType.COLLECTION):  # type: ignore[call-arg]
    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            "layout" not in _dict  # not a layout
            and "commonfields" not in _dict  # not an integration or script
            and "rules" not in _dict  # not a modeling rule or parsing rule
            and "tasks" not in _dict  # not a playbook
            and "supportedModules" in _dict
            and "id" in _dict
            and "name" in _dict
            and path.suffix == ".yml"
        ):
            return True
        return False
