from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class GenericFieldParser(JSONContentItemParser, content_type=ContentType.GENERIC_FIELD):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
        self.definition_id = self.json_data.get("definitionId")
        self.field_type = self.json_data.get("type") or ""

        self.connect_to_dependencies()

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }

    def connect_to_dependencies(self) -> None:
        """Collects the generic types associated to the generic field as optional dependencies."""
        for associated_type in set(self.json_data.get("associatedTypes") or []):
            self.add_dependency_by_name(
                associated_type, ContentType.GENERIC_TYPE, is_mandatory=False
            )

        for system_associated_type in set(
            self.json_data.get("systemAssociatedTypes") or []
        ):
            self.add_dependency_by_name(
                system_associated_type, ContentType.GENERIC_TYPE, is_mandatory=False
            )
