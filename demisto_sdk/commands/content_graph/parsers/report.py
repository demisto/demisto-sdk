from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class ReportParser(JSONContentItemParser, content_type=ContentType.REPORT):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)

        self.connect_to_dependencies()

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }

    def connect_to_dependencies(self) -> None:
        """Collects scripts used in the report as optional dependencies."""
        for layout in self.json_data.get("dashboard", {}).get("layout", []):
            widget_data = layout.get("widget")
            if widget_data.get("dataType") == "scripts":
                if script_name := widget_data.get("query"):
                    self.add_dependency_by_id(
                        script_name, ContentType.SCRIPT, is_mandatory=False
                    )
