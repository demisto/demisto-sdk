
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.common import ContentType, Relationship


class ContentGraphInterface(ABC):
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
    def get_packs_content_items(self, marketplace: MarketplaceVersions):
        pass

    @abstractmethod
    def get_all_integrations_with_commands(self):
        pass
    
    @abstractmethod
    def get_node_by_path(self, path: Path, marketplace: MarketplaceVersions):
        pass
    
    @abstractmethod
    def clean_graph(self):
        pass
    
    @abstractmethod
    def get_nodes_by_type(self, content_type: ContentType) -> Any:
        pass

    @abstractmethod
    def search_nodes(
        self,
        content_type: Optional[ContentType] = None,
        **properties,
    ) -> Any:
        pass

    @abstractmethod
    def get_single_node(
        self,
        content_type: Optional[ContentType] = None,
        **properties,
    ) -> Any:
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
    def run_single_query(self, query: str, **kwargs) -> Any:
        pass
