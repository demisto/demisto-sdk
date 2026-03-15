from functools import cached_property
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import AgentixBaseParser
from demisto_sdk.commands.content_graph.strict_objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.prepare_content.agentix_agent_unifier import (
    AgentixAgentUnifier,
)


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
        self.visibility: str = self.yml_data.get("visibility")  # type: ignore
        self.actionids: list[str] = self.yml_data.get("actionids", [])
        self.conversationstarters: list[str] = self.yml_data.get(
            "conversationstarters", []
        )
        self.builtinactions: list[str] = self.yml_data.get("builtinactions", [])
        self.autoenablenewactions: bool = self.yml_data.get(
            "autoenablenewactions", False
        )
        self.roles: list[str] = self.yml_data.get("roles", [])
        self.sharedwithroles: list[str] = self.yml_data.get("sharedwithroles", [])
        self.add_action_dependencies()

    @property
    def systeminstructions(self) -> str:
        """Gets the agent system instructions.

        The system instructions are read from a separate file named
        <agent_folder_name>_systeminstructions.md in the agent's directory.

        Returns:
            str: The agent system instructions.
        """
        if not self.git_sha:
            return AgentixAgentUnifier.get_system_instructions(self.path.parent)
        else:
            return AgentixAgentUnifier.get_system_instructions_with_sha(
                self.path, self.git_sha
            )

    def add_action_dependencies(self) -> None:
        """Collects the actions used in the agent as optional dependencies."""
        if actions_ids := self.yml_data.get("actionids"):
            for id in actions_ids:
                self.add_dependency_by_id(
                    id, ContentType.AGENTIX_ACTION, is_mandatory=False
                )

    @cached_property
    def field_mapping(self):
        super().field_mapping.update({"display": "name"})
        return super().field_mapping

    @property
    def strict_object(self):
        return AgentixAgent
