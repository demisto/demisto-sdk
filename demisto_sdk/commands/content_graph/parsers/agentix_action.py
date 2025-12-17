from functools import cached_property
from pathlib import Path
from typing import Any, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
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
        
        # Log detailed information for debugging
        logger.info(f"[AgentixAction Debug] Parsing from path: {path}")
        logger.info(f"[AgentixAction Debug] Resolved YAML path: {self.path}")
        logger.info(f"[AgentixAction Debug] File exists: {self.path.exists()}")
        logger.info(f"[AgentixAction Debug] File is file: {self.path.is_file()}")
        if self.path.exists():
            logger.info(f"[AgentixAction Debug] File size: {self.path.stat().st_size} bytes")
        logger.info(f"[AgentixAction Debug] yml_data type: {type(self.yml_data)}")
        logger.info(f"[AgentixAction Debug] yml_data value: {self.yml_data}")
        logger.info(f"[AgentixAction Debug] yml_data keys: {list(self.yml_data.keys()) if isinstance(self.yml_data, dict) else 'Not a dict'}")
        
        underlying_content_item = self.yml_data.get("underlyingcontentitem")
        if underlying_content_item is None:
            logger.error(
                f"Missing 'underlyingcontentitem' field in {path}. "
                f"Available fields: {list(self.yml_data.keys()) if isinstance(self.yml_data, dict) else self.yml_data}"
            )
            raise ValueError(
                f"AgentixAction at {path} is missing required 'underlyingcontentitem' field. "
                f"File path: {self.path}, exists: {self.path.exists()}"
            )
        
        logger.info(f"[AgentixAction Debug] underlyingcontentitem keys: {list(underlying_content_item.keys())}")
        
        self.underlying_content_item_id: str = underlying_content_item.get("id")  # type: ignore
        self.underlying_content_item_name: str = underlying_content_item.get("name")  # type: ignore
        self.underlying_content_item_type: str = underlying_content_item.get("type")  # type: ignore
        self.underlying_content_item_command: str = underlying_content_item.get("command")  # type: ignore
        self.underlying_content_item_version: int = underlying_content_item.get("version")  # type: ignore
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
