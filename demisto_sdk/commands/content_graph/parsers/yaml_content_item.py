import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_yaml, get_yml_paths_in_dir
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    NotAContentItemException,
)

logger = logging.getLogger("demisto-sdk")


class YAMLContentItemParser(ContentItemParser):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.yml_data: Dict[str, Any] = self.get_yaml()

        if self.should_skip_parsing():
            raise NotAContentItemException

    @property
    def name(self) -> Optional[str]:
        return self.yml_data.get("name")

    @property
    def display_name(self) -> Optional[str]:
        return self.name or self.object_id

    @property
    def deprecated(self) -> bool:
        return self.yml_data.get("deprecated", False)

    @property
    def description(self) -> Optional[str]:
        description = self.yml_data.get("description", "")
        description = description.replace("\\ ", " ")  # removes unwanted backslashes
        description = description.replace("\\\n", " ")  # removes unwanted backslashes
        description = " ".join(
            description.split()
        )  # substitutes multiple spaces into one
        return description

    @property
    def fromversion(self) -> str:
        return self.yml_data.get("fromversion") or DEFAULT_CONTENT_ITEM_FROM_VERSION

    @property
    def toversion(self) -> str:
        return self.yml_data.get("toversion") or DEFAULT_CONTENT_ITEM_TO_VERSION

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        if file_marketplaces := [
            MarketplaceVersions(mp) for mp in self.yml_data.get("marketplaces", [])
        ]:
            return file_marketplaces
        return sorted(set(self.pack_marketplaces) & self.supported_marketplaces)

    def connect_to_tests(self) -> None:
        """Iterates over the test playbooks registered to this content item,
        and creates a TESTED_BY relationship between the content item to each of them.
        """
        tests_playbooks: List[str] = self.yml_data.get("tests", [])
        for test_playbook_id in tests_playbooks:
            if "no test" not in test_playbook_id.lower():
                self.add_relationship(
                    RelationshipType.TESTED_BY,
                    target=test_playbook_id,
                    target_type=ContentType.TEST_PLAYBOOK,
                )

    def get_yaml(self) -> Dict[str, Union[str, List[str]]]:
        if not self.path.is_dir():
            yaml_path = self.path.as_posix()
        else:
            _, yaml_path = get_yml_paths_in_dir(self.path.as_posix())
        if not yaml_path:
            raise NotAContentItemException

        self.path = Path(yaml_path)
        return get_yaml(self.path.as_posix())
