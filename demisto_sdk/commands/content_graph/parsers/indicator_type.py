from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.indicator_type import (
    StrictIndicatorType,
)


class IndicatorTypeParser(
    JSONContentItemParser, content_type=ContentType.INDICATOR_TYPE
):
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
        self.regex = self.json_data.get("regex")
        self.reputation_script_name = self.json_data.get("reputationScriptName") or ""
        self.enhancement_script_names = self.json_data.get("enhancementScriptNames")

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {"name": "details", "description": "details", "expiration": "expiration"}
        )
        return super().field_mapping

    @property
    def expiration(self):
        return get_value(self.json_data, self.field_mapping.get("expiration", ""))

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
        """Collects scripts and the reputation command used as optional dependencies,
        and the layout as a mandatory dependency.
        """
        for field in ["reputationScriptName", "enhancementScriptNames"]:
            associated_scripts = self.json_data.get(field)
            if associated_scripts and associated_scripts != "null":
                associated_scripts = (
                    [associated_scripts]
                    if not isinstance(associated_scripts, list)
                    else associated_scripts
                )
                for script in associated_scripts:
                    self.add_dependency_by_id(
                        script, ContentType.SCRIPT, is_mandatory=False
                    )

        if reputation_command := self.json_data.get("reputationCommand"):
            self.add_dependency_by_id(
                reputation_command, ContentType.COMMAND, is_mandatory=False
            )

        if layout := self.json_data.get("layout"):
            self.add_dependency_by_id(layout, ContentType.LAYOUT, is_mandatory=False)

    @property
    def strict_object(self):
        return StrictIndicatorType
