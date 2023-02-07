from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Set

from demisto_sdk.commands.common.handlers import (
    JSON_Handler,
    XSOAR_Handler,
    YAML_Handler,
)

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.pack import Pack
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
    from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook

import logging

from pydantic import DirectoryPath, validator

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    MarketplaceSuffixPreparer,
)

logger = logging.getLogger("demisto-sdk")


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions]
    name: str
    fromversion: str
    toversion: str
    display_name: str
    deprecated: bool
    description: Optional[str]
    is_test: bool = False

    @validator("path", always=True)
    def validate_path(cls, v: Path) -> Path:
        if v.is_absolute():
            return v
        return CONTENT_PATH / v

    @property
    def in_pack(self) -> Optional["Pack"]:
        """
        This returns the Pack which the content item is in.

        Returns:
            Pack: Pack model.
        """
        in_pack = self.relationships_data[RelationshipType.IN_PACK]
        if not in_pack:
            return None
        return next(iter(in_pack)).content_item_to  # type: ignore[return-value]

    @property
    def uses(self) -> List["RelationshipData"]:
        """
        This returns the content items which this content item uses.
        In addition, we can tell if it's a mandatorily use or not.

        Returns:
            List[RelationshipData]:
                RelationshipData:
                    relationship_type: RelationshipType
                    source: BaseContent
                    target: BaseContent

                    # this is the attribute we're interested in when querying
                    content_item: BaseContent

                    # Whether the relationship between items is direct or not
                    is_direct: bool

                    # Whether using the command mandatorily (or optional)
                    mandatorily: bool = False

        """
        return [
            r
            for r in self.relationships_data[RelationshipType.USES]
            if r.content_item_to.database_id == r.target_id
        ]

    @property
    def tested_by(self) -> List["TestPlaybook"]:
        """
        This returns the test playbooks which the content item is tested by.

        Returns:
            List[TestPlaybook]: List of TestPlaybook models.
        """
        return [
            r.content_item_to  # type: ignore[misc]
            for r in self.relationships_data[RelationshipType.TESTED_BY]
            if r.content_item_to.database_id == r.target_id
        ]

    @property
    def handler(self) -> XSOAR_Handler:
        # we use a high value so the code lines will not break
        return (
            JSON_Handler()
            if self.path.suffix.lower() == ".json"
            else YAML_Handler(width=50_000)
        )

    @property
    def data(self) -> dict:
        with self.path.open() as f:
            return self.handler.load(f)

    def prepare_for_upload(
        self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs
    ) -> dict:
        data = self.data
        return MarketplaceSuffixPreparer.prepare(data, marketplace)

    def summary(self, marketplace: Optional[MarketplaceVersions] = None) -> dict:
        """Summary of a content item (the most important metadata fields)

        Args:
            marketplace: The marketplace to get the summary for.
        Returns:
            dict: Dictionary representation of the summary content item.
        """
        summary_res = self.dict(include=self.metadata_fields(), by_alias=True)
        if marketplace and marketplace != MarketplaceVersions.XSOAR:
            data = self.data
            if "id" in summary_res:
                summary_res["id"] = (
                    data.get("commonfields", {}).get("id_x2") or self.object_id
                )
            if "name" in summary_res:
                summary_res["name"] = data.get("name_x2") or self.name
        return summary_res

    @abstractmethod
    def metadata_fields(self) -> Set[str]:
        raise NotImplementedError("Should be implemented in subclasses")

    @property
    def normalize_name(self) -> str:
        """
        This will add the server prefix of the content item to its name
        In addition it will remove the existing server_names of the name.

        Args:
            name (str): content item name.
        Returns:
            str: The normalized name.
        """
        name = self.path.name
        server_names = ContentType.server_names()
        for _ in range(2):
            # we iterate twice to handle cases of doubled prefixes like `classifier-mapper-`
            for prefix in server_names:
                try:
                    name = name.removeprefix(f"{prefix}-")  # type: ignore[attr-defined]
                except AttributeError:
                    # not supported in python 3.8
                    name = (
                        name[: len(prefix) + 1]
                        if name.startswith(f"{prefix}-")
                        else name
                    )
        normalized = f"{self.content_type.server_name}-{name}"
        logger.debug(f"Normalized file name from {name} to {normalized}")
        return normalized

    def dump(self, dir: DirectoryPath, _: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        data = self.prepare_for_upload()
        with (dir / self.normalize_name).open("w") as f:
            self.handler.dump(data, f)

    def to_id_set_entity(self) -> dict:
        """
        Transform the model to content item id_set.
        This is temporarily until the content graph is fully merged.

        Returns:
            dict: id_set entiity
        """
        id_set_entity = self.dict()
        id_set_entity["file_path"] = str(self.path)
        id_set_entity["pack"] = self.in_pack.object_id  # type: ignore[union-attr]
        return id_set_entity
