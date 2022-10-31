from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import \
    JSONContentItemParser


class DashboardParser(JSONContentItemParser, content_type=ContentType.DASHBOARD):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)

        self.connect_to_dependencies()

    def connect_to_dependencies(self) -> None:
        """Collects the scripts used in the dashboard as optional dependencies."""
        for layout in self.json_data.get("layout", []):
            widget_data = layout.get("widget")
            if widget_data.get("dataType") == "scripts":
                if script_name := widget_data.get("query"):
                    self.add_dependency_by_id(
                        script_name, ContentType.SCRIPT, is_mandatory=False
                    )
