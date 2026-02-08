from functools import cached_property
from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase
from demisto_sdk.commands.content_graph.parsers.related_files import (
    SystemInstructionsRelatedFile,
)
from demisto_sdk.commands.prepare_content.agentix_agent_unifier import (
    AgentixAgentUnifier,
)


class AgentixAgent(AgentixBase, content_type=ContentType.AGENTIX_AGENT):
    color: str
    visibility: str
    actionids: list[str] = []
    systeminstructions: str = ""
    conversationstarters: list[str] = []
    builtinactions: list[str] = []
    autoenablenewactions: bool = False
    roles: list[str] = []
    sharedwithroles: list[str] = []

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "color" in _dict and path.suffix == ".yml":
            return True
        return False

    @cached_property
    def system_instructions_file(self) -> SystemInstructionsRelatedFile:
        """Get the system instructions related file."""
        return SystemInstructionsRelatedFile(self.path, git_sha=self.git_sha)

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.PLATFORM,
        **kwargs,
    ) -> dict:
        """
        Prepare the AgentixAgent for upload by unifying system instructions.

        This method merges the system instructions from the separate file
        into the YAML data during content creation.

        Args:
            current_marketplace: Target marketplace (default: PLATFORM)
            **kwargs: Additional arguments

        Returns:
            Unified YAML dict with systeminstructions field populated from file
        """
        data = super().prepare_for_upload(current_marketplace)
        data = AgentixAgentUnifier.unify(self.path, data, current_marketplace)
        return data
