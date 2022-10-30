from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, Union

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (ContentType,
                                                       RelationshipType)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import Command
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO


class ContentGraphInterface(ABC):
    _calculate_dependencies = True

    @abstractmethod
    def create_indexes_and_constraints(self) -> None:
        pass

    @abstractmethod
    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        pass

    @abstractmethod
    def create_relationships(self, relationships: Dict[RelationshipType, List[Dict[str, Any]]]) -> None:
        pass

    @abstractmethod
    def validate_graph(self) -> None:
        pass

    @abstractmethod
    def clean_graph(self):
        ContentGraphInterface._calculate_dependencies = True

    @abstractmethod
    def search(
        self,
        marketplace: MarketplaceVersions = None,
        content_type: Optional[ContentType] = None,
        filter_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        **properties,
    ) -> List[Union[BaseContent, Command]]:
        """
        This searches the database for content items and returns a list of them, including their relationships

        Args:
            marketplace (MarketplaceVersions, optional): Marketplace to search by. Defaults to None.
            content_type (Optional[ContentType], optional): The content_type to filter. Defaults to None.
            filter_list (Optional[Iterable[int]], optional): A list of unique IDs to filter. Defaults to None.
            all_level_dependencies (bool, optional): Whether to return all level dependencies. Defaults to False.
            **properties: A key, value filter for the search. For example: `search(object_id="QRadar")`.

        Returns:
            List[Union[BaseContent, Command]]: The search results
        """
        if not marketplace and all_level_dependencies:
            raise ValueError("Cannot search for all level dependencies without a marketplace")
        if ContentGraphInterface._calculate_dependencies:
            self.create_pack_dependencies()
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
            marketplace, content_type=ContentType.PACK, all_level_dependencies=all_level_dependencies,
        )
        return ContentDTO(packs=packs)

    @abstractmethod
    def create_pack_dependencies(self):
        ContentGraphInterface._calculate_dependencies = True

    @abstractmethod
    def run_single_query(self, query: str, **kwargs) -> Any:
        pass
