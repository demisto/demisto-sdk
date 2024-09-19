from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.layout import Layout


class CaseLayout(Layout, content_type=ContentType.CASE_LAYOUT):  # type: ignore[call-arg]
    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "group" in _dict and Path(path).suffix == ".json":
            if "cliName" not in _dict:
                if _dict["group"] == "case":
                    return True
        return False
