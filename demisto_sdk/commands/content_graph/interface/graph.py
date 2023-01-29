import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import get_content_path
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

json = JSON_Handler()
METADATA_FILE_NAME = "metadata.json"


class ContentGraphInterface(ABC):
    repo_path = Path(get_content_path())  # type: ignore

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
            with (self.import_path / METADATA_FILE_NAME).open() as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    @property
    def commit(self) -> Optional[str]:
        if self.metadata:
            return self.metadata.get("commit")
        return None

    def dump_metadata(self) -> None:
        """Adds metadata to the graph."""
        metadata = {
            "commit": GitUtil().get_current_commit_hash(),
        }
        with open(self.import_path / METADATA_FILE_NAME, "w") as f:
            json.dump(metadata, f)

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
    def import_graph(self, imported_path: Optional[Path] = None) -> None:
        pass

    @abstractmethod
    def export_graph(self, output_path: Optional[Path] = None) -> None:
        pass

    @abstractmethod
    def validate_graph(self) -> None:
        pass

    @abstractmethod
    def clean_graph(self):
        ...

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
