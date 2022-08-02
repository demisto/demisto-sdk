from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, List, Union

from demisto_sdk.commands.common.tools import (
    get_current_repo,
    get_files_in_dir,
    get_json, get_yaml,
    get_yml_paths_in_dir
)
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, UNIFIED_FILES_SUFFIXES, MarketplaceVersions
import demisto_sdk.commands.content_graph.parsers.base_content as base_content


class NotAContentItem(Exception):
    pass


class ContentItemParser(base_content.BaseContentParser):
    """ A class representation of a content item.

    Attributes:
        path (Path):
    """
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.relationships: Dict[Rel, List[Dict[str, Any]]] = {}

    @property
    @abstractmethod
    def content_item_id(self) -> str:
        pass

    @property
    @abstractmethod
    def content_type(self) -> ContentTypes:
        pass

    @property
    def node_id(self) -> str:
        return f'{self.content_type}:{self.content_item_id}'

    @property
    @abstractmethod
    def marketplaces(self) -> List[str]:
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

    def add_relationship(self, rel_type: Rel, target_id: str, **kwargs: Dict[str, Any]) -> None:
        relationship: Dict[str, Any] = {
            'from': self.node_id,
            'to': target_id,
        }
        relationship.update(kwargs)
        self.relationships.setdefault(rel_type, []).append(relationship)

    def add_dependency(self, dependency_id: str, dependency_type: Optional[ContentTypes] = None, is_mandatory: bool = True) -> None:
        if dependency_type is not None:
            self.add_relationship(
                Rel.USES,
                dependency_id,
                target_label=dependency_type.value,
                mandatorily=is_mandatory,
            )
        else:
            self.add_relationship(
                Rel.USES_COMMAND_OR_SCRIPT,
                dependency_id,
                mandatorily=is_mandatory,
            )


class YAMLContentItemParser(ContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path)
        self.pack_marketplaces: List[str] = pack_marketplaces
        self.yml_data = self.get_yaml()

    @property
    def deprecated(self) -> bool:
        return self.yml_data.get('deprecated', False)
    
    @property
    def marketplaces(self) -> List[str]:
        if not (marketplaces := self.yml_data.get('marketplaces', [])):
            return self.pack_marketplaces
        return marketplaces

    def get_data(self) -> Dict[str, Any]:
        yaml_content_item_data = {
            'node_id': self.node_id,
            'id': self.content_item_id,
            'name': self.yml_data.get('name'),
            'deprecated': self.deprecated,
            'fromversion': self.yml_data.get('fromversion'),
            'toversion': self.yml_data.get('toversion', ''),
            'source': list(get_current_repo()),
            'in_xsoar': MarketplaceVersions.XSOAR.value in self.marketplaces,
            'in_xsiam': MarketplaceVersions.MarketplaceV2.value in self.marketplaces,
            'file_path': self.path.as_posix(),
        }
        if to_version := yaml_content_item_data['toversion']:
            yaml_content_item_data['node_id'] += f'_{to_version}'

        return yaml_content_item_data

    def connect_to_tests(self) -> None:
        tests_playbooks: List[str] =  self.yml_data.get('tests', [])
        for test_playbook_id in tests_playbooks:
            if 'no test' not in test_playbook_id.lower():
                self.add_relationship(Rel.TESTED_BY, test_playbook_id)

    def get_yaml(self) -> Dict[str, Union[str, List[str]]]:
        if not self.path.is_dir():
            yaml_path = self.path.as_posix()
        else:
            _, yaml_path = get_yml_paths_in_dir(self.path.as_posix())
        if not yaml_path:
            raise NotAContentItem

        return get_yaml(yaml_path)


class JSONContentItemParser(ContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path)
        self.pack_marketplaces: List[str] = pack_marketplaces
        self.json_data: Dict[str, Any] = self.get_json()

    @property
    def content_item_id(self) -> str:
        return self.json_data.get('id')

    @property
    def deprecated(self) -> bool:
        return self.json_data.get('deprecated', False)
    
    @property
    def marketplaces(self) -> List[str]:
        if not (marketplaces := self.json_data.get('marketplaces', [])):
            return self.pack_marketplaces
        return marketplaces

    def get_data(self) -> Dict[str, Any]:
        json_content_item_data = {
            'node_id': self.node_id,
            'id': self.content_item_id,
            'name': self.json_data.get('name'),
            'deprecated': self.deprecated,
            'fromversion': self.json_data.get('fromVersion'),
            'toversion': self.json_data.get('toVersion', ''),
            'source': list(get_current_repo()),
            'in_xsoar': MarketplaceVersions.XSOAR.value in self.marketplaces,
            'in_xsiam': MarketplaceVersions.MarketplaceV2.value in self.marketplaces,
            'file_path': self.path.as_posix(),
        }
        if to_version := json_content_item_data['toversion']:
            json_content_item_data['node_id'] += f'_{to_version}'

        return json_content_item_data
    
    def get_json(self) -> Dict[str, Any]:
        if self.path.is_dir():
            json_files_in_dir = get_files_in_dir(self.path.as_posix(), ['json'], False)
            if len(json_files_in_dir) != 1:
                raise NotAContentItem(f'Directory {self.path} must have a single JSON file.')
            self.path = Path(json_files_in_dir[0])
        return get_json(self.path.as_posix())
