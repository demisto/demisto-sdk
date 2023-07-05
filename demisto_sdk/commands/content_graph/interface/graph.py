import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import requests
from pydantic import ValidationError
from requests import JSONDecodeError

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

json = JSON_Handler()


class ContentGraphInterface(ABC):
    repo_path = CONTENT_PATH  # type: ignore
    METADATA_FILE_NAME = "metadata.json"
    SCHEMA_FILE_NAME = "schema.json"

    @property
    @abstractmethod
    def import_path(self) -> Path:
        pass

    @abstractmethod
    def clean_import_dir(self) -> None:
        pass

    @abstractmethod
    def move_to_import_dir(self, imported_path: Path) -> None:
        pass

    @property
    def metadata(self) -> Optional[dict]:
        try:
            return get_file(self.import_path / self.METADATA_FILE_NAME)
        except FileNotFoundError:
            return None

    @property
    def commit(self) -> Optional[str]:
        if self.metadata:
            return self.metadata.get("commit")
        return None

    @property
    def content_parser_latest_commit(self) -> Optional[str]:
        if self.metadata:
            return self.metadata.get("content_parser_latest_commit")
        return None

    @property
    def schema(self) -> Optional[dict]:
        try:
            return get_file(self.import_path / self.SCHEMA_FILE_NAME)
        except FileNotFoundError:
            return None

    def dump_metadata(self) -> None:
        """Adds metadata to the graph."""
        metadata = {
            "commit": GitUtil().get_current_commit_hash(),
            "content_parser_latest_commit": self._get_latest_content_parser_commit_hash(),
        }
        with open(self.import_path / self.METADATA_FILE_NAME, "w") as f:
            json.dump(metadata, f)
        with open(self.import_path / self.SCHEMA_FILE_NAME, "w") as f:
            json.dump(ContentDTO.model_json_schema(), f)

    def _get_latest_content_parser_commit_hash(self) -> Optional[str]:
        try:
            return requests.get(
                "https://api.github.com/repos/demisto/demisto-sdk/commits?sha=master&path=demisto_sdk/commands/content_graph/parsers",
                verify=False,
            ).json()[0]["sha"]
        except (
            requests.exceptions.RequestException,
            IndexError,
            JSONDecodeError,
            KeyError,
        ) as e:
            logger.warning(f"Failed to get content parser commit: {e}")
            return None

    def _has_infra_graph_been_changed(self) -> bool:
        if not self.content_parser_latest_commit:
            logger.warning("The content parser commit hash is missing.")
        elif (
            self.content_parser_latest_commit
            != self._get_latest_content_parser_commit_hash()
        ):
            logger.warning("The content parser has been changed.")
            return True
        schema = self.schema
        if not self.schema:
            logger.warning("The graph schema file is missing, trying to marshal it.")
            try:
                self.marshal_graph(MarketplaceVersions.XSOAR)
                return False

            except ValidationError as e:
                logger.warning("Failed to load the content graph.")
                logger.debug(f"Validation Error: {e}")
                return True

        if schema == ContentDTO.model_json_schema():
            return False
        logger.warning("The graph infra files has been changed.")
        return True

    def zip_import_dir(self, output_file: Path) -> None:
        shutil.make_archive(str(output_file), "zip", self.import_path)

    @abstractmethod
    def create_indexes_and_constraints(self) -> None:
        pass

    @abstractmethod
    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        pass

    @abstractmethod
    def create_relationships(
        self, relationships: Dict[RelationshipType, List[Dict[str, Any]]]
    ) -> None:
        pass

    @abstractmethod
    def remove_server_items(self) -> None:
        pass

    @abstractmethod
    def import_graph(self, imported_path: Optional[Path] = None) -> bool:
        pass

    @abstractmethod
    def export_graph(self, output_path: Optional[Path] = None) -> None:
        pass

    @abstractmethod
    def get_unknown_content_uses(
        self, file_paths: List[str], raises_error: bool
    ) -> List[BaseContent]:
        pass

    @abstractmethod
    def get_duplicate_pack_display_name(
        self, file_paths: List[str]
    ) -> List[Tuple[str, List[str]]]:
        pass

    @abstractmethod
    def find_uses_paths_with_invalid_fromversion(
        self, file_paths: List[str], for_supported_versions=False
    ) -> List[BaseContent]:
        pass

    @abstractmethod
    def find_uses_paths_with_invalid_toversion(
        self, file_paths: List[str], for_supported_versions=False
    ) -> List[BaseContent]:
        pass

    @abstractmethod
    def find_uses_paths_with_invalid_marketplaces(
        self, pack_ids: List[str]
    ) -> List[BaseContent]:
        pass

    @abstractmethod
    def find_core_packs_depend_on_non_core_packs(
        self,
        pack_ids: List[str],
        marketplace: MarketplaceVersions,
        core_pack_list: List[str],
    ) -> List[BaseContent]:
        pass

    @abstractmethod
    def validate_duplicate_ids(self, file_paths: List[str]) -> None:
        pass

    @abstractmethod
    def clean_graph(self):
        ...

    @abstractmethod
    def find_items_using_deprecated_items(self, file_paths: List[str]) -> List[dict]:
        pass

    @abstractmethod
    def search(
        self,
        marketplace: MarketplaceVersions = None,
        content_type: Optional[ContentType] = None,
        ids_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        **properties,
    ) -> List[BaseContent]:
        """
        This searches the database for content items and returns a list of them, including their relationships

        Args:
            marketplace (MarketplaceVersions, optional): Marketplace to search by. Defaults to None.
            content_type (Optional[ContentType], optional): The content_type to filter. Defaults to None.
            ids_list (Optional[Iterable[int]], optional): A list of unique IDs to filter. Defaults to None.
            all_level_dependencies (bool, optional): Whether to return all level dependencies. Defaults to False.
            **properties: A key, value filter for the search. For example: `search(object_id="QRadar")`.

        Returns:
            List[BaseContent]: The search results
        """
        if not marketplace and all_level_dependencies:
            raise ValueError(
                "Cannot search for all level dependencies without a marketplace"
            )
        return []

    def from_path(
        self, path: Path, marketplace: Optional[MarketplaceVersions] = None
    ) -> Union[Pack, ContentItem]:
        """This will return a pack or content item from a path with the local changes, enriched with relationships from the graph

        Args:
            path (Path): The path from a content item
            marketplace (Optional[MarketplaceVersions], optional): The marketplace to use. Defaults to None.

        Raises:
            ValueError: If the path cannot be parsed locally
            ValueError: If the path cannot be found in the graph

        Returns:
            Union[Pack, ContentItem]: The content item found
        """
        content_item = BaseContent.from_path(path)
        if not isinstance(content_item, (ContentItem, Pack)):
            raise ValueError(f"Could not parse content_item from {path}")
        # enrich the content_item with the graph
        result = self.search(
            path=content_item.path.relative_to(self.repo_path), marketplace=marketplace
        )
        if not result or not isinstance(result[0], (Pack, ContentItem)):
            raise ValueError(f"Could not find content item in graph from {path}")
        return result[0]

    def marshal_graph(
        self, marketplace: MarketplaceVersions, all_level_dependencies: bool = False
    ) -> ContentDTO:
        """
        This marshals the graph into a ContentDTO object

        Args:
            marketplace (MarketplaceVersions): The marketplace to filter on
            all_level_dependencies (bool, optional): Whether to marshal all level dependencies. Defaults to False.

        Returns:
            ContentDTO: Marshalled object.
        """
        packs = self.search(
            marketplace,
            content_type=ContentType.PACK,
            all_level_dependencies=all_level_dependencies,
        )
        return ContentDTO(packs=packs)

    @abstractmethod
    def create_pack_dependencies(self):
        ...

    @abstractmethod
    def run_single_query(self, query: str, **kwargs) -> Any:
        pass
