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
