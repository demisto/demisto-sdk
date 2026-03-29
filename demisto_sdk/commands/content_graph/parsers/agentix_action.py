from functools import cached_property
from pathlib import Path
from typing import Any, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import AgentixBaseParser
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import (
    AgentixAction,
    ScriptConfig,
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
        # Detect script action: script: sub-key is a dict
        script_data = self.yml_data.get("script") or {}
        if isinstance(script_data, dict) and script_data:
            self.script_config: Optional[ScriptConfig] = ScriptConfig(**script_data)
            self.internal_script: bool = script_data.get("internal", False)
        else:
            self.script_config = None
            self.internal_script = False

        # Fill underlying_content_item_* — always required on the object
        underlying = self.yml_data.get("underlyingcontentitem") or {}
        if underlying:
            self.underlying_content_item_id: str = underlying.get("id", "")
            self.underlying_content_item_name: str = underlying.get("name", "")
            self.underlying_content_item_type: str = underlying.get("type", "")
            self.underlying_content_item_command: str = underlying.get("command", "")
            self.underlying_content_item_version: int = underlying.get("version", -1)
        else:
            # Script action: fill with defaults derived from the action itself
            self.underlying_content_item_id = self.object_id or ""
            self.underlying_content_item_name = self.object_id or ""
            self.underlying_content_item_type = "script"
            self.underlying_content_item_command = ""
            self.underlying_content_item_version = -1

        self.requires_user_approval: Optional[bool] = self.yml_data.get(
            "requiresuserapproval"
        )
        self.is_test: bool = False
        self.connect_to_dependencies()

    @property
    def is_script_action(self) -> bool:
        """True when this action has a script: sub-key (dict) in the YAML."""
        return self.script_config is not None

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

    def connect_to_dependencies(self) -> None:
        """Create USES relationship to the underlying content item."""
        if self.is_script_action:
            # Script action: no dependency (generated script doesn't exist in source graph)
            return
        if self.underlying_content_item_type == "command":
            if self.underlying_content_item_command:
                self.add_command_or_script_dependency(
                    self.underlying_content_item_command, is_mandatory=True
                )
        elif self.underlying_content_item_type == "script":
            self.add_dependency_by_id(
                self.underlying_content_item_id, ContentType.SCRIPT, is_mandatory=True
            )
        elif self.underlying_content_item_type == "playbook":
            self.add_dependency_by_id(
                self.underlying_content_item_id,
                ContentType.PLAYBOOK,
                is_mandatory=True,
            )
