from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
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
        self.color: str = self.yml_data.get("color")

    @property
    def strict_object(self):
        return AgentixAgent

    @property
    def display_name(self) -> Optional[str]:
        return get_value(self.yml_data, "name")
