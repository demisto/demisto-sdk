from pathlib import Path
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixAgent(AgentixBase):
    color: str

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        pass