from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.collection import (
    StrictCollection,
)


class CollectionParser(YAMLContentItemParser, content_type=ContentType.COLLECTION):
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

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "display": "display",
            }
        )
        return super().field_mapping

    @property
    def display_name(self) -> Optional[str]:
        return (
            get_value(self.json_data, self.field_mapping.get("display", ""))
            or self.name
            or self.object_id
        )

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.PLATFORM,
        }

    @property
    def strict_object(self):
        return StrictCollection
