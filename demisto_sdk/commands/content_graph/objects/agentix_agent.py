from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixAgent(AgentixBase, content_type=ContentType.AGENTIX_AGENT):
    color: str
    actionids: list[str]
    systeminstructions: str = ""
    conversationstarters: list[str] = []
    autoenablenewactions: bool = False

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "color" in _dict and path.suffix == ".yml":
            return True
        return False
