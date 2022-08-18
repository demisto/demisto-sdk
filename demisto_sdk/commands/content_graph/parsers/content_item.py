from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, List, Union, TYPE_CHECKING

from demisto_sdk.commands.common.tools import (
    get_files_in_dir,
    get_json, get_yaml,
    get_yml_paths_in_dir
)
from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_TO_VERSION, MarketplaceVersions
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, UNIFIED_FILES_SUFFIXES
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class NotAContentItem(Exception):
    pass


class ContentItemParser(BaseContentParser):
    """ A class representation of a content item.

    Attributes:
        path (Path):
    """
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path)
        self.pack: 'PackParser' = pack

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def deprecated(self) -> bool:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def marketplaces(self) -> List[MarketplaceVersions]:
        pass

    @property
    @abstractmethod
    def fromversion(self) -> str:
        pass

    @property
    @abstractmethod
    def toversion(self) -> str:
        pass

    @staticmethod
    def is_package(path: Path) -> bool:
        return path.is_dir()

    @staticmethod
    def is_unified_file(path: Path) -> bool:
        return path.suffix in UNIFIED_FILES_SUFFIXES

    @staticmethod
    def is_content_item(path: Path) -> bool:
        return ContentItemParser.is_package(path) or ContentItemParser.is_unified_file(path)

    @abstractmethod
    def add_to_pack(self) -> None:
        pass

    def add_relationship(
        self,
        relationship: Rel,
        target: str,
        **kwargs,
    ) -> None:
        relationship_data: Dict[str, Any] = {
            'source_node_id': self.node_id,
            'source_fromversion': self.fromversion,
            'source_marketplaces': self.marketplaces,
            'target': target,
        }
        relationship_data.update(kwargs)
        self.pack.relationships.setdefault(relationship, []).append(relationship_data)

    def add_dependency(self, dependency_id: str, dependency_type: Optional[ContentTypes] = None, is_mandatory: bool = True) -> None:
        if dependency_type is None:  # and self.content_type == ContentTypes.SCRIPT:
            relationship = Rel.USES_COMMAND_OR_SCRIPT
            target = dependency_id
        else:
            relationship = Rel.USES
            target = f'{dependency_type}:{dependency_id}'

        self.add_relationship(
            relationship,
            target=target,
            mandatorily=is_mandatory,
        )


class YAMLContentItemParser(ContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        self.yml_data: Dict[str, Any] = self.get_yaml()

    @property
    def name(self) -> str:
        return self.yml_data.get('name')

    @property
    def deprecated(self) -> bool:
        return self.yml_data.get('deprecated', False)

    @property
    def description(self) -> str:
        return self.yml_data.get('description', '')

    @property
    def fromversion(self) -> str:
        return self.yml_data.get('fromversion')

    @property
    def toversion(self) -> str:
        return self.yml_data.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)

    @property
    def marketplaces(self) -> List[str]:
        if not (marketplaces := self.yml_data.get('marketplaces', [])):
            return self.pack.marketplaces
        return marketplaces

    def connect_to_tests(self) -> None:
        tests_playbooks: List[str] =  self.yml_data.get('tests', [])
        for test_playbook_id in tests_playbooks:
            if 'no test' not in test_playbook_id.lower():
                tpb_node_id = f'{ContentTypes.TEST_PLAYBOOK}:{test_playbook_id}'
                self.add_relationship(
                    Rel.TESTED_BY,
                    target=tpb_node_id,
                )

    def get_yaml(self) -> Dict[str, Union[str, List[str]]]:
        if not self.path.is_dir():
            yaml_path = self.path.as_posix()
        else:
            _, yaml_path = get_yml_paths_in_dir(self.path.as_posix())
        if not yaml_path:
            raise NotAContentItem

        self.path = Path(yaml_path)
        return get_yaml(self.path.as_posix())


class JSONContentItemParser(ContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        self.json_data: Dict[str, Any] = self.get_json()
        self.pack: 'PackParser' = pack

    @property
    def object_id(self) -> str:
        return self.json_data['id']

    @property
    def name(self) -> str:
        return self.json_data.get('name')

    @property
    def deprecated(self) -> bool:
        return self.json_data.get('deprecated', False)

    @property
    def description(self) -> str:
        return self.json_data.get('description', '')

    @property
    def fromversion(self) -> str:
        return self.json_data.get('fromVersion')

    @property
    def toversion(self) -> str:
        return self.json_data.get('toVersion', DEFAULT_CONTENT_ITEM_TO_VERSION)

    @property
    def marketplaces(self) -> List[str]:
        if not (marketplaces := self.json_data.get('marketplaces', [])):
            return self.pack.marketplaces
        return marketplaces
    
    def get_json(self) -> Dict[str, Any]:
        if self.path.is_dir():
            json_files_in_dir = get_files_in_dir(self.path.as_posix(), ['json'], False)
            if len(json_files_in_dir) != 1:
                raise NotAContentItem(f'Directory {self.path} must have a single JSON file.')
            self.path = Path(json_files_in_dir[0])
        return get_json(self.path.as_posix())
