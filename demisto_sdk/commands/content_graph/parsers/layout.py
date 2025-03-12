from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.content_item import (
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.layout import StrictLayout


class LayoutParser(JSONContentItemParser, content_type=ContentType.LAYOUT):
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
        if "group" not in self.json_data:
            logger.debug(f"{path}: Not a layout container, skipping.")
            raise NotAContentItemException

        self.kind = self.json_data.get("kind")
        self.tabs = self.json_data.get("tabs")
        self.definition_id = self.json_data.get("definitionId")
        self.group = self.json_data.get("group") or (
            "incident" if self.definition_id == "ThreatIntelReport" else ""
        )

        self.edit: bool = bool(self.json_data.get("edit"))
        self.indicators_details: bool = bool(self.json_data.get("indicatorsDetails"))
        self.indicators_quick_view: bool = bool(
            self.json_data.get("indicatorsQuickView")
        )
        self.quick_view: bool = bool(self.json_data.get("quickView"))
        self.close: bool = bool(self.json_data.get("close"))
        self.details: bool = bool(self.json_data.get("details"))
        self.details_v2: bool = bool(self.json_data.get("detailsV2"))
        self.mobile: bool = bool(self.json_data.get("mobile"))

        self.connect_to_dependencies()

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
            MarketplaceVersions.PLATFORM,
        }

    def connect_to_dependencies(self) -> None:
        """Collects the incident/indicator fields used as optional dependencies."""
        if self.group == "incident":
            dependency_field_type = ContentType.INCIDENT_FIELD
        elif self.group == "indicator":
            dependency_field_type = ContentType.INDICATOR_FIELD
        elif self.group == "case":
            dependency_field_type = ContentType.CASE_FIELD

        else:
            raise ValueError(
                f'{self.node_id}: Unknown group "{self.group}" - Expected "incident", "indicator" or "case".'
            )

        for field in self.get_field_ids_recursively():
            if field:
                self.add_dependency_by_id(
                    field, dependency_field_type, is_mandatory=False
                )

    def get_field_ids_recursively(self) -> Set[str]:
        """Recursively iterates over the layout json data to extract all fieldId items.

        Returns:
            A set of the field IDs.
        """
        values: Set[str] = set()

        def get_values(current_object):
            if isinstance(current_object, list):
                for item in current_object:
                    get_values(item)

            elif isinstance(current_object, dict):
                for key, value in current_object.items():
                    if key == "fieldId" and isinstance(value, str):
                        values.add(
                            value.replace("incident_", "")
                            .replace("indicator_", "")
                            .replace("case_", "")
                        )
                    else:
                        get_values(value)

        get_values(self.json_data)
        return values

    @property
    def strict_object(self):
        return StrictLayout
