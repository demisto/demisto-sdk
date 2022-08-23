import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, List, Type, Union

from demisto_sdk.commands.common.tools import (
    get_files_in_dir,
    get_json, get_yaml,
    get_yml_paths_in_dir
)
from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_FROM_VERSION, DEFAULT_CONTENT_ITEM_TO_VERSION
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, UNIFIED_FILES_SUFFIXES, Relationships
from demisto_sdk.commands.content_graph.parsers import *
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser


logger = logging.getLogger('demisto-sdk')

class NotAContentItem(Exception):
    pass


class IncorrectParser(Exception):
    def __init__(self, correct_parser: 'ContentItemParser', **kwargs) -> None:
        self.correct_parser = correct_parser
        self.kwargs = kwargs
        super().__init__()


class ParserMeta(ABCMeta):
    def __new__(cls, name, bases, namespace, content_type: ContentTypes = None, **kwargs):
        """ This method is called before every creation of a ContentItemParser *class* (NOT class instances!).
        If `content_type` is passed as an argument of the class, we add a mapping between the content type
        and the parser class object.
        
        After all the parser classes are created, `content_type_to_parser` has a full mapping between content types
        and parsers, and only then we are ready to determine which parser class to use based on a content item's type.

        Args:
            name: The class object name (e.g., IntegrationParser)
            bases: The bases of the class object (e.g., [YAMLContentItemParser, ContentItemParser, BaseContentParser])
            namespace: The namespaces of the class object.
            content_type (ContentTypes, optional): The type corresponds to the class (e.g., ContentTypes.INTEGRATIONS)

        Returns:
            ContentItemParser: The parser class.
        """
        parser_cls = super().__new__(cls, name, bases, namespace)
        if content_type:
            ContentItemParser.content_type_to_parser[content_type] = parser_cls
            # parser_cls.content_type: ContentTypes = content_type  # todo: consider self.content_type replacing with this
        return parser_cls


class ContentItemParser(BaseContentParser, metaclass=ParserMeta):
    """ A content item parser.

    Static Attributes:
        content_type_to_parser (Dict[ContentTypes, Type[ContentItemParser]]): 
            A mapping between content types and parsers.
    
    Attributes:
        relationships (Relationships): The relationships collections of the content item.
    """
    content_type_to_parser: Dict[ContentTypes, Type['ContentItemParser']] = {}

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.relationships: Relationships = Relationships()

    @staticmethod
    def from_path(path: Path) -> Optional['ContentItemParser']:
        """ Tries to parse a content item by its path.
        If during the attempt we detected the file is not a content item, `None` is returned.

        Returns:
            Optional[ContentItemParser]: The parsed content item.
        """
        if not ContentItemParser.is_content_item(path):
            return None

        content_type: ContentTypes = ContentTypes.by_folder(path.parts[-2])
        if parser := ContentItemParser.content_type_to_parser.get(content_type):
            try:
                logger.info(f'Parsed {parser.node_id}')
                return parser(path)
            except IncorrectParser as e:
                return e.correct_parser(path, **e.kwargs)
            except NotAContentItem:
                logger.debug(f'Skipping {path}')
                pass
        return None

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
    def marketplaces(self) -> List[str]:
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
        """ Determines whether a file path is of a content item, by one of the following conditions:
        1. If this is a directory
        2. If it's a unified file

        Args:
            path (Path): The file path

        Returns:
            bool: True iff the file path is of a content item.
        """
        return ContentItemParser.is_package(path) or ContentItemParser.is_unified_file(path)

    def add_relationship(
        self,
        relationship: Rel,
        target: str,
        **kwargs,
    ) -> None:
        """ Adds a single relationship to the collection of the content item relationships.

        Args:
            relationship (Rel): The relationship type.
            target (str): The identifier of the target content object (e.g, its node_id).
            kwargs: Additional information about the relationship.
        """
        self.relationships.add(
            relationship,
            source=self.node_id,
            source_fromversion=self.fromversion,
            source_marketplaces=self.marketplaces,
            target=target,
            **kwargs
        )

    def add_to_pack(self, pack: str) -> None:
        """ Creates an IN_PACK relationship between the content item and its pack.

        Args:
            pack (str): The pack node_id.
        """
        self.add_relationship(Rel.IN_PACK, pack)

    def add_dependency(
        self,
        dependency_id: str,
        dependency_type: Optional[ContentTypes] = None,
        is_mandatory: bool = True
    ) -> None:
        """ Creates a USES relationship between the content item and a given dependency.

        If the dependency type is unknown (happens only when the content item is a script and the
        dependency is a command or script) a USES_COMMAND_OR_SCRIPT relationship is created.

        Args:
            dependency_id (str): The dependency identifier (node_id or object_id).
            dependency_type (Optional[ContentTypes], optional): The dependency type. Defaults to None.
            is_mandatory (bool, optional): Whether or not the dependency is mandatory. Defaults to True.
        """
        if dependency_type is None:
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
    def __init__(self, path: Path) -> None:
        super().__init__(path)
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
        return self.yml_data.get('fromversion') or DEFAULT_CONTENT_ITEM_FROM_VERSION

    @property
    def toversion(self) -> str:
        return self.yml_data.get('toversion') or DEFAULT_CONTENT_ITEM_TO_VERSION

    @property
    def marketplaces(self) -> List[str]:
        return self.yml_data.get('marketplaces', [])

    def connect_to_tests(self) -> None:
        """ Iterates over the test playbooks registered to this content item,
        and creates a TESTED_BY relationship between the content item to each of them.
        """
        tests_playbooks: List[str] = self.yml_data.get('tests', [])
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
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.json_data: Dict[str, Any] = self.get_json()

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
        return self.json_data.get('fromVersion') or DEFAULT_CONTENT_ITEM_FROM_VERSION

    @property
    def toversion(self) -> str:
        return self.json_data.get('toVersion') or DEFAULT_CONTENT_ITEM_TO_VERSION

    @property
    def marketplaces(self) -> List[str]:
        return self.json_data.get('marketplaces', [])

    def get_json(self) -> Dict[str, Any]:
        if self.path.is_dir():
            json_files_in_dir = get_files_in_dir(self.path.as_posix(), ['json'], False)
            if len(json_files_in_dir) != 1:
                raise NotAContentItem(f'Directory {self.path} must have a single JSON file.')
            self.path = Path(json_files_in_dir[0])
        return get_json(self.path.as_posix())
