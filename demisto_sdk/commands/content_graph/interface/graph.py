
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.common import ContentType, Relationship
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Command
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook


class ContentGraphInterface(ABC):

    @abstractmethod
    def is_graph_alive(self):
        pass

    @abstractmethod
    def create_indexes_and_constraints(self) -> None:
        pass

    @abstractmethod
    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        pass

    @abstractmethod
    def create_relationships(self, relationships: Dict[Relationship, List[Dict[str, Any]]]) -> None:
        pass

    @abstractmethod
    def validate_graph(self) -> None:
        pass

    @abstractmethod
    def get_packs(self,
                  marketplace: MarketplaceVersions,
                  **properties) -> List[Pack]:
        pass

    @abstractmethod
    def clean_graph(self):
        pass

    @abstractmethod
    def search_nodes(
        self,
        marketplace: MarketplaceVersions,
        content_type: Optional[ContentType] = None,
        **properties,
    ) -> List[BaseContent]:
        pass

    @abstractmethod
    def get_single_node(
        self,
        marketplace: MarketplaceVersions,
        content_type: Optional[ContentType] = None,
        **properties,
    ) -> BaseContent:
        pass

    @abstractmethod
    def get_relationships_by_type(self, relationship: Relationship) -> Any:
        pass

    @abstractmethod
    def get_all_level_dependencies(self, marketplace: MarketplaceVersions) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_first_level_dependencies(self, marketplace: MarketplaceVersions) -> Dict[str, Dict[str, Any]]:
        pass

    @abstractmethod
    def create_pack_dependencies(self):
        pass

    @abstractmethod
    def get_all_content_item_tests(self, marketplace: MarketplaceVersions, content_type: ContentType) -> Dict[str, List[TestPlaybook]]:
        pass

    @abstractmethod
    def run_single_query(self, query: str, **kwargs) -> Any:
        pass
