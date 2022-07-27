import sys
from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, List, Type, Union

from demisto_sdk.commands.content_graph.parsers import BaseContentParser
import demisto_sdk.commands.content_graph.parsers as parsers
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.common.tools import get_yaml, get_yml_paths_in_dir

UNIFIED_FILES_SUFFIXES = ['.yml']


class NotAContentItem(Exception):
    pass


class ContentItemParser(BaseContentParser):
    """ A class representation of a content item.

    Attributes:
        path (Path):
    """
    def __init__(self, path: Path) -> None:
        self.path: Path = path

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

    @staticmethod
    def from_path(path: Path, marketplaces: List[str]) -> Optional['ContentItemParser']:
        if not ContentItemParser.is_content_item(path):
            return None

        content_type: str = ContentTypes.by_folder(path.parts[-2]).value
        parser_class_name: str = f'{content_type}Parser'
        try:
            parser_class: Type['ContentItemParser'] = getattr(parsers, parser_class_name)
        except (AttributeError, TypeError):
            # parser class does not exist for this content type
            return None
        try:
            return parser_class(path, marketplaces)
        except NotAContentItem:
            # during the parsing we detected this is not a content item
            return None

    def connect_to_pack(self, pack_id: str) -> None:
        parsers.PackSubGraphCreator.add_relationship(self, Rel.IN_PACK, pack_id)

    def add_dependency(self, dependency_id: str, dependency_type: ContentTypes, is_mandatory: bool = True) -> None:
        dependency_node_id = f'{dependency_type.value}:{dependency_id}'
        parsers.PackSubGraphCreator.add_relationship(
            self,
            Rel.DEPENDS_ON,
            dependency_node_id,
            mandatorily=is_mandatory,
            deprecated=self.deprecated,
        )


class YAMLContentItemParser(ContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        self.pack_marketplaces: List[str] = pack_marketplaces
        self.yml_data = YAMLContentItemParser.get_yaml_from_path(path)
        super().__init__(path)

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
            'id': self.node_id,
            'name': self.yml_data.get('name'),
            'deprecated': self.deprecated,
            'fromversion': self.yml_data.get('fromversion'),
            'toversion': self.yml_data.get('toversion'),
            'source': ['github'],  # todo
            'marketplaces': self.marketplaces,
            'file_path': self.path.as_posix(),
        }
        if to_version := yaml_content_item_data['toversion']:
            yaml_content_item_data['id'] += f'_{to_version}'

        return yaml_content_item_data

    @staticmethod
    def get_yaml_from_path(path: Path) -> Dict[str, Union[str, List[str]]]:
        if not path.is_dir():
            yaml_path = path.as_posix()
        else:
            _, yaml_path = get_yml_paths_in_dir(path.as_posix())
        if not yaml_path:
            raise NotAContentItem

        return get_yaml(yaml_path)


class TestableMixin(object):
    def connect_to_tests(self) -> None:
        tests_playbooks: List[str] =  self.yml_data.get('tests', [])
        for test_playbook_id in tests_playbooks:
            if 'no test' not in test_playbook_id.lower():
                parsers.PackSubGraphCreator.add_relationship(self, Rel.TESTED_BY, test_playbook_id)
