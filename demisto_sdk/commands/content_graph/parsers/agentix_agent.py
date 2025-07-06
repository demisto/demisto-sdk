from functools import cached_property
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import AgentixBaseParser
from demisto_sdk.commands.content_graph.strict_objects.agentix_agent import AgentixAgent


class AgentixAgentParser(AgentixBaseParser, content_type=ContentType.AGENTIX_AGENT):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        self.color: str = self.yml_data.get("color")  # type: ignore

    @cached_property
    def field_mapping(self):
        super().field_mapping.update({"display": "display"})
        return super().field_mapping

    @property
    def strict_object(self):
        return AgentixAgent
