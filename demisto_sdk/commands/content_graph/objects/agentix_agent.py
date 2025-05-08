from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixAgent(AgentixBase, content_type=ContentType.AGENTIX_AGENT):
    color: str

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        pass