from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import AgentixBaseParser
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import AgentixActionArgument, AgentixActionOutput, \
    AgentixAction


class AgentixActionParser(AgentixBaseParser, content_type=ContentType.AGENTIX_ACTION):
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
        self.few_shots: Optional[str] = self.yml_data.get("fewShots")
        self.agent_id: str = self.yml_data.get("agentId")
        self.content_item_id: str = self.yml_data.get("contentItemId")
        self.content_item_type: str = self.yml_data.get("contentItemType")
        self.content_item_version: str = self.yml_data.get("contentItemVersion")
        self.content_item_pack_version: str = self.yml_data.get("contentItemPackVersion")

    @property
    def strict_object(self):
        return AgentixAction

    @property
    def args(self) -> list[AgentixActionArgument]:
        return self.yml_data.get("args", [])

    @property
    def outputs(self) -> list[AgentixActionOutput]:
        return self.yml_data.get("outputs", [])
