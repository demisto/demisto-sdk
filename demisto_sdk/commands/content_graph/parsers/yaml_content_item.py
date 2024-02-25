import re
from functools import cached_property
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_value, get_yaml
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    InvalidContentItemException,
    NotAContentItemException,
)


class YAMLContentItemParser(ContentItemParser):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha)
        self.path = (
            self.get_path_with_suffix(".yml")
            if not git_sha
            else self.path / f"{self.path.name}.yml"
            if not self.path.suffix == ".yml"
            else self.path
        )  # If git_sha is given then we know we're running on the old_content_object copy and we can assume that the file_path is either the actual item path or the path to the item's dir.

        if not isinstance(self.yml_data, dict):
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
                "description": "description",
                "fromversion": "fromversion",
                "toversion": "toversion",
                "version": "version",
            }
        )
        return super().field_mapping

    @property
    def object_id(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("object_id", ""))

    @property
    def name(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("name", ""))

    @property
    def display_name(self) -> Optional[str]:
        return self.name or self.object_id

    @property
    def deprecated(self) -> bool:
        return get_value(self.yml_data, self.field_mapping.get("deprecated", ""), False)

    @property
    def description(self) -> Optional[str]:
        description = get_value(
            self.yml_data, self.field_mapping.get("description", ""), ""
        )
        description = description.replace("\\ ", " ")  # removes unwanted backslashes
        description = description.replace("\\\n", " ")  # removes unwanted backslashes
        description = re.sub(
            r"(?<=\S) +", " ", description
        )  # substitutes multiple spaces into one
        return description

    @property
    def fromversion(self) -> str:
        return get_value(
            self.yml_data,
            self.field_mapping.get("fromversion", ""),
            DEFAULT_CONTENT_ITEM_FROM_VERSION,
        )

    @property
    def toversion(self) -> str:
        return (
            get_value(
                self.yml_data,
                self.field_mapping.get("toversion", ""),
            )
            or DEFAULT_CONTENT_ITEM_TO_VERSION
        )

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        return self.get_marketplaces(self.yml_data)

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

    @cached_property
    def yml_data(self) -> dict:
        return get_yaml(str(self.path), git_sha=self.git_sha)

    @property
    def version(self) -> int:
        return get_value(self.yml_data, self.field_mapping.get("version", ""), 0)
