from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
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
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.path = self.get_path_with_suffix(".json") if not git_sha else self.path
        self.original_json_data: Dict[str, Any] = self.json_data
        if not isinstance(self.json_data, dict):
            raise InvalidContentItemException(
                f"The content of {self.path} must be in a JSON dictionary format"
            )

        if self.should_skip_parsing():
            raise NotAContentItemException

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
            DEFAULT_CONTENT_ITEM_FROM_VERSION,
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

    @cached_property
    def json_data(self) -> Dict[str, Any]:
        return get_json(str(self.path), git_sha=self.git_sha)

    @property
    def version(self) -> int:
        return get_value(self.json_data, self.field_mapping.get("version", ""), 0)
