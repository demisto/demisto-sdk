import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Dict, Optional, List, Type

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
