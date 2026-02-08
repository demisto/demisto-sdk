from functools import cached_property
from pathlib import Path
from typing import Any, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import AgentixBaseParser
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import (
    AgentixAction,
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
        self.underlying_content_item_id: str = self.yml_data.get(
            "underlyingcontentitem"
        ).get("id")  # type: ignore
        self.underlying_content_item_name: str = self.yml_data.get(
            "underlyingcontentitem"
        ).get("name")  # type: ignore
        self.underlying_content_item_type: str = self.yml_data.get(
            "underlyingcontentitem"
        ).get("type")  # type: ignore
        self.underlying_content_item_command: str = self.yml_data.get(
            "underlyingcontentitem"
        ).get("command")  # type: ignore
        self.underlying_content_item_version: int = self.yml_data.get(
            "underlyingcontentitem"
        ).get("version")  # type: ignore
        self.requires_user_approval: Optional[bool] = self.yml_data.get(
            "requiresuserapproval"
        )
        self.connect_to_dependencies()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update({"display": "display"})
        return super().field_mapping

    @property
    def strict_object(self):
        return AgentixAction

    @property
    def args(self) -> list[Any]:
        return self.yml_data.get("args", [])

    @property
    def outputs(self) -> list[Any]:
        return self.yml_data.get("outputs", [])

    @property
    def few_shots(self) -> Optional[list[str]]:
        return self.yml_data.get("fewshots", [])

    @property
    def instructions(self) -> Optional[str]:
        return self.yml_data.get("instructions")

    def connect_to_dependencies(self) -> None:
        """Create USES relationship to the underlying content item."""
        # Determine the target content type based on underlying item type
        if self.underlying_content_item_type == "command":
            # For commands, use USES_COMMAND_OR_SCRIPT with the command name
            if self.underlying_content_item_command:
                self.add_command_or_script_dependency(
                    self.underlying_content_item_command, is_mandatory=True
                )
        elif self.underlying_content_item_type == "script":
            # For scripts, use USES_BY_ID with the script ID
            self.add_dependency_by_id(
                self.underlying_content_item_id, ContentType.SCRIPT, is_mandatory=True
            )
        elif self.underlying_content_item_type == "playbook":
            # For playbooks, use USES_BY_ID with the playbook ID
            self.add_dependency_by_id(
                self.underlying_content_item_id, ContentType.PLAYBOOK, is_mandatory=True
            )
