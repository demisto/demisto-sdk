from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.dashboard import StrictDashboard


class DashboardParser(JSONContentItemParser, content_type=ContentType.DASHBOARD):
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

    @property
    def strict_object(self):
        return StrictDashboard

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }

    def connect_to_dependencies(self) -> None:
        """Collects the scripts used in the dashboard as optional dependencies."""
        for layout in self.json_data.get("layout", []):
            widget_data = layout.get("widget")
            if widget_data.get("dataType") == "scripts":
                if script_name := widget_data.get("query"):
                    self.add_dependency_by_id(
                        script_name, ContentType.SCRIPT, is_mandatory=False
                    )

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "layout": "layout",
            }
        )
        return super().field_mapping

    @property
    def data_dict(self):
        return self.json_data

    @property
    def layout(self):
        return self.json_data.get("layout", [])
