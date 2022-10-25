from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_content_path
from demisto_sdk.commands.content_graph.common import (ContentType,
                                                       RelationshipType)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO


class ContentGraphInterface(ABC):
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
    def validate_graph(self) -> None:
        pass

    @abstractmethod
    def clean_graph(self):
        pass

    @abstractmethod
    def match(
        self,
        marketplace: MarketplaceVersions,
        content_type: Optional[ContentType] = None,
        filter_list: Optional[Iterable[int]] = None,
        is_nested: bool = False,
        **properties,
    ) -> List[BaseContent]:
        pass

    def marshal_graph(self, marketplace: MarketplaceVersions, dependencies: bool):
        if dependencies:
            self.create_pack_dependencies()
        packs = self.match(marketplace, content_type=ContentType.PACK)
        return ContentDTO(path=get_content_path(), packs=packs)

    @abstractmethod
    def create_pack_dependencies(self):
        pass

    @abstractmethod
    def run_single_query(self, query: str, **kwargs) -> Any:
        pass
