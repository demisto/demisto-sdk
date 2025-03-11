from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.trigger import StrictTrigger


class TriggerParser(JSONContentItemParser, content_type=ContentType.TRIGGER):
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
        self.connect_to_dependencies()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {"object_id": "trigger_id", "name": "trigger_name"}
        )
        return super().field_mapping

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.PLATFORM,
        }

    def connect_to_dependencies(self) -> None:
        """Collects the playbook used in the trigger as a mandatory dependency."""
        if playbook := self.json_data.get("playbook_id"):
            self.add_dependency_by_id(playbook, ContentType.PLAYBOOK)

    @property
    def strict_object(self):
        return StrictTrigger
