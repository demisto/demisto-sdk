from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MINIMUM_XSOAR_SAAS_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_json, get_value
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    InvalidContentItemException,
    NotAContentItemException,
)


class JSONContentItemParser(ContentItemParser):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path,
            pack_marketplaces,
            pack_supported_modules=pack_supported_modules,
            git_sha=git_sha,
        )
        self.path = self.get_path_with_suffix(".json") if not git_sha else self.path
        self.original_json_data: Dict[str, Any] = self.json_data
        self.structure_errors = self.validate_structure()
        self.supportedModules: List[str] = self.json_data.get(
            "supportedModules", pack_supported_modules
        )

        if not isinstance(self.json_data, dict):
            raise InvalidContentItemException(
                f"The content of {self.path} must be in a JSON dictionary format"
            )

        if self.should_skip_parsing():
            raise NotAContentItemException

    @property
    def raw_data(self) -> dict:
        return self.json_data

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "name": "name",
                "deprecated": "deprecated",
                "object_id": "id",
                "description": "description",
                "fromversion": "fromVersion",
                "toversion": "toVersion",
                "version": "version",
            }
        )
        return super().field_mapping

    @property
    def object_id(self) -> Optional[str]:
        return get_value(self.json_data, self.field_mapping.get("object_id", ""))

    @property
    def name(self) -> Optional[str]:
        return get_value(self.json_data, self.field_mapping.get("name", ""))

    @property
    def display_name(self) -> Optional[str]:
        return self.name or self.object_id

    @property
    def deprecated(self) -> bool:
        return get_value(
            self.json_data, self.field_mapping.get("deprecated", ""), False
        )

    @property
    def description(self) -> Optional[str]:
        return get_value(self.json_data, self.field_mapping.get("description", ""), "")

    @property
    def fromversion(self) -> str:
        return get_value(
            self.json_data,
            self.field_mapping.get("fromversion", ""),
            DEFAULT_CONTENT_ITEM_FROM_VERSION
            if MarketplaceVersions.XSOAR_ON_PREM in self.supported_marketplaces
            else MINIMUM_XSOAR_SAAS_VERSION,
        )

    @property
    def toversion(self) -> str:
        return (
            get_value(
                self.json_data,
                self.field_mapping.get("toversion", ""),
            )
            or DEFAULT_CONTENT_ITEM_TO_VERSION
        )

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        return self.get_marketplaces(self.json_data)

    @property
    def support(self) -> str:
        return self.get_support(self.json_data)

    @cached_property
    def json_data(self) -> Dict[str, Any]:
        return get_json(str(self.path), git_sha=self.git_sha)

    @property
    def version(self) -> int:
        return get_value(self.json_data, self.field_mapping.get("version", ""), 0)

    @property
    def is_silent(self) -> bool:
        return get_value(self.json_data, "issilent", False)
