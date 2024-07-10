from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class CorrelationRuleParser(
    YAMLContentItemParser, content_type=ContentType.CORRELATION_RULE
):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "global_rule_id",
                "execution_mode": "execution_mode",
                "search_window": "search_window",
            }
        )
        return super().field_mapping

    @property
    def execution_mode(self):
        return get_value(
            self.yml_data, self.field_mapping.get("execution_mode", ""), None
        )

    @property
    def search_window(self):
        return get_value(
            self.yml_data, self.field_mapping.get("search_window", ""), None
        )

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}
