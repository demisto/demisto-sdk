import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple, Union

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_file,
    sha1_dir,
    write_dict,
)
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
    BaseNode,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO


class DeprecatedItemUsage(NamedTuple):
    deprecated_item_id: str
    content_items_using_deprecated: List[BaseNode]


class ContentGraphInterface(ABC):
    repo_path = CONTENT_PATH  # type: ignore
    METADATA_FILE_NAME = "metadata.json"
    DEPENDS_ON_FILE_NAME = "depends_on.json"
    _depends_on = None

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
            return get_file(
                self.import_path / self.METADATA_FILE_NAME, raise_on_error=True
            )
        except FileNotFoundError:
            return None

    @property
    def commit(self) -> Optional[str]:
        if self.metadata:
            return self.metadata.get("commit")
        return None

    @property
    def content_parser_latest_hash(self) -> Optional[str]:
        if self.metadata:
            return self.metadata.get("content_parser_latest_hash")
        return None

    @property
    def schema(self) -> Optional[dict]:
        if self.metadata:
            return self.metadata.get("schema")
        return None

    def dump_metadata(self, override_commit: bool = True) -> None:
        """Adds metadata to the graph."""
        metadata = {
            "commit": (
                GitUtil().get_current_commit_hash() if override_commit else self.commit
            ),
            "content_parser_latest_hash": self._get_latest_content_parser_hash(),
            "schema": self.get_schema(),
        }

        write_dict(self.import_path / self.METADATA_FILE_NAME, data=metadata)

    def dump_depends_on(self) -> None:
        """Adds depends_on.json to the graph import dir."""
        if self._depends_on:
            write_dict(
                self.import_path / self.DEPENDS_ON_FILE_NAME,
                data=self._depends_on,
                indent=4,
                sort_keys=True,
            )

    def _get_latest_content_parser_hash(self) -> Optional[str]:
        parsers_path = Path(__file__).parent.parent / "parsers"
        parsers_sha1 = sha1_dir(parsers_path)
        logger.debug(f"Content parser hash: {parsers_sha1}")
        return parsers_sha1

    def _has_infra_graph_been_changed(self) -> bool:
        if not self.content_parser_latest_hash:
            logger.warning("The content parser hash is missing.")
        elif self.content_parser_latest_hash != self._get_latest_content_parser_hash():
            logger.warning("The content parser has been changed.")
            return True
        return False

    def zip_import_dir(self, output_file: Path) -> None:
        shutil.make_archive(str(output_file), "zip", self.import_path)

    @abstractmethod
    def get_schema(self) -> dict:
        pass

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
    def remove_non_repo_items(self) -> None:
        pass

    @abstractmethod
    def import_graph(
        self,
        imported_path: Optional[Path] = None,
        download: bool = False,
        fail_on_error: bool = False,
    ) -> bool:
        pass

    @abstractmethod
    def export_graph(
        self,
        output_path: Optional[Path] = None,
        override_commit: bool = True,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    ) -> None:
        pass

    @abstractmethod
    def get_unknown_content_uses(self, file_paths: List[str]) -> List[BaseNode]:
        pass

    @abstractmethod
    def get_duplicate_pack_display_name(
        self, file_paths: List[str]
    ) -> List[Tuple[str, List[str]]]:
        pass

    @abstractmethod
    def find_uses_paths_with_invalid_fromversion(
        self, file_paths: List[str], for_supported_versions=False
    ) -> List[BaseNode]:
        pass

    @abstractmethod
    def find_uses_paths_with_invalid_toversion(
        self, file_paths: List[str], for_supported_versions=False
    ) -> List[BaseNode]:
        pass

    @abstractmethod
    def find_uses_paths_with_invalid_marketplaces(
        self, pack_ids: List[str]
    ) -> List[BaseNode]:
        pass

    @abstractmethod
    def find_core_packs_depend_on_non_core_packs(
        self,
        pack_ids: List[str],
        marketplace: MarketplaceVersions,
        core_pack_list: List[str],
    ) -> List[BaseNode]:
        pass

    @abstractmethod
    def validate_duplicate_ids(
        self, file_paths: List[str]
    ) -> List[Tuple[BaseNode, List[BaseNode]]]:
        pass

    @abstractmethod
    def clean_graph(self): ...

    @abstractmethod
    def find_items_using_deprecated_items(
        self, file_paths: List[str]
    ) -> List[DeprecatedItemUsage]:
        pass

    @abstractmethod
    def get_relationships_by_path(
        self,
        path: Path,
        relationship_type: RelationshipType,
        content_type: ContentType,
        depth: int,
        marketplace: MarketplaceVersions,
        retrieve_sources: bool,
        retrieve_targets: bool,
        mandatory_only: bool,
        include_tests: bool,
        include_deprecated: bool,
        include_hidden: bool,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        pass

    @abstractmethod
    def search(
        self,
        marketplace: Union[MarketplaceVersions, str] = None,
        content_type: ContentType = ContentType.BASE_NODE,
        ids_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        **properties,
    ) -> List[BaseNode]:
        """
        This searches the database for content items and returns a list of them, including their relationships

        Args:
            marketplace (MarketplaceVersions, optional): Marketplace to search by. Defaults to None.
            content_type (ContentType]): The content_type to filter. Defaults to ContentType.BASE_NODE.
            ids_list (Optional[Iterable[int]], optional): A list of unique IDs to filter. Defaults to None.
            all_level_dependencies (bool, optional): Whether to return all level dependencies. Defaults to False.
            **properties: A key, value filter for the search. For example: `search(object_id="QRadar")`.

        Returns:
            List[BaseNode]: The search results
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
    def create_pack_dependencies(self): ...

    @abstractmethod
    def run_single_query(self, query: str, **kwargs) -> Any:
        pass

    @abstractmethod
    def find_packs_with_invalid_dependencies(
        self, pack_ids: List[str]
    ) -> List[BaseNode]:
        pass

    @abstractmethod
    def get_api_module_imports(self, api_module: str) -> List[IntegrationScript]:
        pass

    @abstractmethod
    def is_alive(self): ...
