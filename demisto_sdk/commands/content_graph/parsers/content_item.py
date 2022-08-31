import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Dict, Optional, List, Type

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_display_name
from demisto_sdk.commands.content_graph.common import ContentType, Relationship, UNIFIED_FILES_SUFFIXES, Relationships
from demisto_sdk.commands.content_graph.parsers import *
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser


logger = logging.getLogger('demisto-sdk')


class NotAContentItemException(Exception):
    pass


class IncorrectParserException(Exception):
    def __init__(self, correct_parser: 'ContentItemParser', **kwargs) -> None:
        self.correct_parser = correct_parser
        self.kwargs = kwargs
        super().__init__()


class ParserMetaclass(ABCMeta):
    def __new__(cls, name, bases, namespace, content_type: ContentType = None, **kwargs):
        """ This method is called before every creation of a ContentItemParser *class* (NOT class instances!).
        If `content_type` is passed as an argument of the class, we add a mapping between the content type
        and the parser class object.
        
        After all the parser classes are created, `content_type_to_parser` has a full mapping between content types
        and parsers, and only then we are ready to determine which parser class to use based on a content item's type.

        Args:
            name: The class object name (e.g., IntegrationParser)
            bases: The bases of the class object (e.g., [YAMLContentItemParser, ContentItemParser, BaseContentParser])
            namespace: The namespaces of the class object.
            content_type (ContentType, optional): The type corresponds to the class (e.g., ContentType.INTEGRATIONS)

        Returns:
            ContentItemParser: The parser class.
        """
        parser_cls: Type['ContentItemParser'] = super().__new__(cls, name, bases, namespace)
        if content_type:
            ContentItemParser.content_type_to_parser[content_type] = parser_cls
            parser_cls.content_type: ContentType = content_type
        return parser_cls


class ContentItemParser(BaseContentParser, metaclass=ParserMetaclass):
    """ A content item parser.

    Static Attributes:
        content_type_to_parser (Dict[ContentType, Type[ContentItemParser]]):
            A mapping between content types and parsers.
    
    Attributes:
        relationships (Relationships): The relationships collections of the content item.
    """
    content_type_to_parser: Dict[ContentType, Type['ContentItemParser']] = {}

    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        self.pack_marketplaces: List[MarketplaceVersions] = pack_marketplaces
        super().__init__(path)
        self.relationships: Relationships = Relationships()

    @staticmethod
    def from_path(path: Path, pack_marketplaces: List[MarketplaceVersions]) -> Optional['ContentItemParser']:
        """ Tries to parse a content item by its path.
        If during the attempt we detected the file is not a content item, `None` is returned.

        Returns:
            Optional[ContentItemParser]: The parsed content item.
        """
        if not ContentItemParser.is_content_item(path):
            return None

        content_type: ContentType = ContentType.by_folder(path.parts[-2])
        if parser_cls := ContentItemParser.content_type_to_parser.get(content_type):
            try:
                return ContentItemParser.parse(
                    parser_cls,
                    path,
                    pack_marketplaces,
                )
            except IncorrectParserException as e:
                return ContentItemParser.parse(
                    e.correct_parser,
                    path,
                    pack_marketplaces,
                    **e.kwargs
                )
        return None

    @staticmethod
    def parse(
        parser_cls: Type['ContentItemParser'],
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        **kwargs
    ) -> Optional['ContentItemParser']:
        try:
            parser = parser_cls(path, pack_marketplaces, **kwargs)
            logger.info(f'Parsed {parser.node_id}')
            return parser
        except NotAContentItemException:
            logger.debug(f'Skipping {path}')
            return None

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def display_name(self) -> str:
        return get_display_name(self.path)

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
        relationship: Relationship,
        target: str,
        **kwargs,
    ) -> None:
        """ Adds a single relationship to the collection of the content item relationships.

        Args:
            relationship (Relationship): The relationship type.
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
        self.add_relationship(Relationship.IN_PACK, pack)

    def add_dependency(
        self,
        dependency_id: str,
        dependency_type: Optional[ContentType] = None,
        is_mandatory: bool = True
    ) -> None:
        """ Creates a USES relationship between the content item and a given dependency.

        If the dependency type is unknown (happens only when the content item is a script and the
        dependency is a command or script) a USES_COMMAND_OR_SCRIPT relationship is created.

        Args:
            dependency_id (str): The dependency identifier (node_id or object_id).
            dependency_type (Optional[ContentType], optional): The dependency type. Defaults to None.
            is_mandatory (bool, optional): Whether or not the dependency is mandatory. Defaults to True.
        """
        if dependency_type is None:
            relationship = Relationship.USES_COMMAND_OR_SCRIPT
            target = dependency_id
        else:
            relationship = Relationship.USES
            target = f'{dependency_type}:{dependency_id}'

        self.add_relationship(
            relationship,
            target=target,
            mandatorily=is_mandatory,
        )
