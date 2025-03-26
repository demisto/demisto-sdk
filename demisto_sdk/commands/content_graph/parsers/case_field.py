from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.case_field import StrictCaseField


class CaseFieldParser(JSONContentItemParser, content_type=ContentType.CASE_FIELD):
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
        self.field_type = self.json_data.get("type")
        self.associated_to_all = self.json_data.get("associatedToAll")
        self.content = self.json_data.get("content")
        self.system = self.json_data.get("system")
        self.group = self.json_data.get("group")

    @cached_property
    def field_mapping(self):
        super().field_mapping.update({"object_id": "id", "cli_name": "cliName"})
        return super().field_mapping

    @property
    def cli_name(self) -> Optional[str]:
        return get_value(self.json_data, self.field_mapping.get("cli_name", ""))

    @property
    def object_id(self) -> Optional[str]:
        id = get_value(self.json_data, self.field_mapping.get("object_id", ""))
        return (id.lower().replace("_", "").replace("-", ""))[len("case") :]

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2, MarketplaceVersions.PLATFORM}

    @property
    def strict_object(self):
        return StrictCaseField
