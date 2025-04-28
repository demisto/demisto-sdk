from demisto_sdk.commands.content_graph.parsers import BaseScriptParser

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.agentix_base import AgentixBaseParser
from demisto_sdk.commands.content_graph.strict_objects.agentix_agent import AgentixAgent

class AgentixAITaskParser(BaseScriptParser, content_type=ContentType.AGENTIX_AI_TASK):
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
        self.is_llm: bool = self.yml_data.get("isLLM")
        self.pre_script: str = self.yml_data.get("preScript")
        self.post_script: str = self.yml_data.get("postScript")
        self.prompt: str = self.yml_data.get("prompt")
        self.few_shots: str = self.yml_data.get("fewShots")

    @property
    def strict_object(self):
        return AgentixAITask

    @property
    def display_name(self) -> Optional[str]:
        return get_value(self.yml_data, "name")