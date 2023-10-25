from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class CorrelationRuleParser(
    YAMLContentItemParser, content_type=ContentType.CORRELATION_RULE
):

    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions], git_sha: Optional[str] = None
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
    
    @property
    def mapping(self):
        return super().mapping | {"object_id": "global_rule_id"}

    @property
    def object_id(self) -> str:
        return get(self.yml_data, self.mapping.get("object_id", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}
