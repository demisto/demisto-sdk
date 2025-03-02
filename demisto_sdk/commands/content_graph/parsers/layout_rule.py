from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.layout_rule import (
    StrictLayoutRule,
)


class LayoutRuleParser(JSONContentItemParser, content_type=ContentType.LAYOUT_RULE):
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
            {
                "object_id": "rule_id",
                "name": "rule_name",
                "layout_id": "layout_id",
            }
        )
        return super().field_mapping

    @property
    def layout_id(self) -> Optional[str]:
        return get_value(self.json_data, self.field_mapping.get("layout_id", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2, MarketplaceVersions.PLATFORM}

    def connect_to_dependencies(self) -> None:
        """Collects t he playbook used in the trigger as a mandatory dependency."""
        if layout := self.json_data.get("layout_id"):
            self.add_dependency_by_id(layout, ContentType.LAYOUT)

    @property
    def strict_object(self):
        return StrictLayoutRule
