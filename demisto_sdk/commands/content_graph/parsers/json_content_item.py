from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_files_in_dir, get_json
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    InvalidContentItemException,
    NotAContentItemException,
)


class JSONContentItemParser(ContentItemParser):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.json_data: Dict[str, Any] = self.get_json()
        self.original_json_data: Dict[str, Any] = self.get_json()
        if not isinstance(self.json_data, dict):
            raise InvalidContentItemException(
                f"The content of {self.path} must be in a JSON dictionary format"
            )

        if self.should_skip_parsing():
            raise NotAContentItemException

    @property
    def object_id(self) -> Optional[str]:
        return self.json_data.get("id")

    @property
    def name(self) -> Optional[str]:
        return self.json_data.get("name")

    @property
    def display_name(self) -> Optional[str]:
        return self.name or self.object_id

    @property
    def deprecated(self) -> bool:
        return self.json_data.get("deprecated", False)

    @property
    def description(self) -> Optional[str]:
        return self.json_data.get("description") or ""

    @property
    def fromversion(self) -> str:
        return self.json_data.get("fromVersion") or DEFAULT_CONTENT_ITEM_FROM_VERSION

    @property
    def toversion(self) -> str:
        return self.json_data.get("toVersion") or DEFAULT_CONTENT_ITEM_TO_VERSION

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        return self.get_marketplaces(self.json_data)

    def get_json(self) -> Dict[str, Any]:
        if self.path.is_dir():
            json_files_in_dir = get_files_in_dir(self.path.as_posix(), ["json"], False)
            if len(json_files_in_dir) != 1:
                raise NotAContentItemException(
                    f"Directory {self.path} must have a single JSON file."
                )
            self.path = Path(json_files_in_dir[0])
        return get_json(self.path.as_posix())
