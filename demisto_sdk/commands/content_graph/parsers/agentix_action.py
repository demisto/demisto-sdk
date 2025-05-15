from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import AgentixBaseParser
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import (
    AgentixAction,
    AgentixActionArgument,
    AgentixActionOutput,
)


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
        self.underlying_content_item_id: str = self.yml_data.get("underlyingContentItemId")
        self.underlying_content_item_name: str = self.yml_data.get("underlyingContentItemName")
        self.underlying_content_item_type: int = self.yml_data.get("underlyingContentItemType")
        self.underlying_content_item_version: int = self.yml_data.get("underlyingContentItemVersion")
        self.underlying_content_item_pack_version: str = self.yml_data.get("underlyingContentItemPackVersion")
        self.requires_user_approval: bool = self.yml_data.get("requiresUserApproval")

    @property
    def strict_object(self):
        return AgentixAction

    @property
    def args(self) -> list[AgentixActionArgument]:
        return self.yml_data.get("args", [])

    @property
    def outputs(self) -> list[AgentixActionOutput]:
        return self.yml_data.get("outputs", [])
