from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class IncidentTypeParser(JSONContentItemParser, content_type=ContentType.INCIDENT_TYPE):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.playbook = self.json_data.get("playbookId")
        self.hours = self.json_data.get("hours")
        self.days = self.json_data.get("days")
        self.weeks = self.json_data.get("weeks")
        self.closure_script = self.json_data.get("closureScript") or None

        self.connect_to_dependencies()

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XPANSE,
        }

    def connect_to_dependencies(self) -> None:
        """Collects the script, playbook and layout used by the incident type as mandatory dependencies."""
        if pre_processing_script := self.json_data.get("preProcessingScript"):
            self.add_dependency_by_id(pre_processing_script, ContentType.SCRIPT)

        if playbook := self.json_data.get("playbookId"):
            self.add_dependency_by_id(playbook, ContentType.PLAYBOOK)

        if layout := self.json_data.get("layout"):
            self.add_dependency_by_id(layout, ContentType.LAYOUT, is_mandatory=False)
