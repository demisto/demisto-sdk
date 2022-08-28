
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.common import ContentTypes, Rel

class ContentGraphInterface(ABC):
    @abstractmethod
    def create_indexes_and_constraints(self) -> None:
        pass

    @abstractmethod
    def create_nodes(self, nodes: Dict[ContentTypes, List[Dict[str, Any]]]) -> None:
        pass

    @abstractmethod
    def create_relationships(self, relationships: Dict[Rel, List[Dict[str, Any]]]) -> None:
        pass

    @abstractmethod
    def validate_graph(self) -> None:
        pass
    
    @abstractmethod
    def get_packs_content_items(self, marketplace: MarketplaceVersions):
        pass

    @abstractmethod
    def get_all_integrations_with_commands(self):
        pass

    @abstractmethod
    def delete_all_graph_nodes_and_relationships(self):
        pass
    
    @abstractmethod
    def get_nodes_by_type(self, content_type: ContentTypes) -> Any:
        pass

    @abstractmethod
    def search_nodes(
        self,
        content_type: Optional[ContentTypes] = None,
        **properties,
    ) -> Any:
        pass

    @abstractmethod
    def get_single_node(
        self,
        content_type: Optional[ContentTypes] = None,
        **properties,
    ) -> Any:
        pass

    @abstractmethod
    def get_relationships_by_type(self, relationship: Rel) -> Any:
        pass

    @abstractmethod
    def run_single_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        pass