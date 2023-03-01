import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set, Type, cast

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    MARKETPLACE_MIN_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import (
    UNIFIED_FILES_SUFFIXES,
    ContentType,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser

logger = logging.getLogger("demisto-sdk")


class NotAContentItemException(Exception):
    pass


class IncorrectParserException(Exception):
    def __init__(self, correct_parser: Type["ContentItemParser"], **kwargs) -> None:
        self.correct_parser = correct_parser
        self.kwargs = kwargs
        super().__init__()


class ParserMetaclass(ABCMeta):
    def __new__(
        cls, name, bases, namespace, content_type: ContentType = None, **kwargs
    ):
        """This method is called before every creation of a ContentItemParser *class* (NOT class instances!).
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
        super_cls: ParserMetaclass = super().__new__(cls, name, bases, namespace)
        # for type checking
        parser_cls: Type["ContentItemParser"] = cast(
            Type["ContentItemParser"], super_cls
        )
        if content_type:
            ContentItemParser.content_type_to_parser[content_type] = parser_cls
            parser_cls.content_type = content_type
        return parser_cls


class ContentItemParser(BaseContentParser, metaclass=ParserMetaclass):
    """A content item parser.

    Static Attributes:
        content_type_to_parser (Dict[ContentType, Type[ContentItemParser]]):
            A mapping between content types and parsers.
    Attributes:
        relationships (Relationships): The relationships collections of the content item.
    """

    content_type_to_parser: Dict[ContentType, Type["ContentItemParser"]] = {}

    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions] = list(MarketplaceVersions),
    ) -> None:
        self.pack_marketplaces: List[MarketplaceVersions] = pack_marketplaces
        super().__init__(path)
        self.relationships: Relationships = Relationships()

    @staticmethod
    def from_path(
        path: Path,
        pack_marketplaces: List[MarketplaceVersions] = list(MarketplaceVersions),
    ) -> Optional["ContentItemParser"]:
        """Tries to parse a content item by its path.
        If during the attempt we detected the file is not a content item, `None` is returned.

        Returns:
            Optional[ContentItemParser]: The parsed content item.
        """
        logger.debug(f"Parsing content item {path}")
        if not ContentItemParser.is_content_item(path):
            if ContentItemParser.is_content_item(path.parent):
                path = path.parent
            else:
                return None
        content_type: ContentType = ContentType.by_path(path)
        if parser_cls := ContentItemParser.content_type_to_parser.get(content_type):
            try:
                return ContentItemParser.parse(
                    parser_cls,
                    path,
                    pack_marketplaces,
                )
            except IncorrectParserException as e:
                return ContentItemParser.parse(
                    e.correct_parser, path, pack_marketplaces, **e.kwargs
                )
        return None

    @staticmethod
    def parse(
        parser_cls: Type["ContentItemParser"],
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        **kwargs,
    ) -> Optional["ContentItemParser"]:
        try:
            parser = parser_cls(path, pack_marketplaces, **kwargs)
            logger.debug(f"Parsed {parser.node_id}")
            return parser
        except NotAContentItemException:
            logger.debug(f"Skipping {path}")
            return None

    @property
    @abstractmethod
    def name(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def display_name(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def deprecated(self) -> bool:
        pass

    @property
    @abstractmethod
    def description(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def marketplaces(self) -> List[MarketplaceVersions]:
        pass

    @property
    @abstractmethod
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
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
        return path.is_dir() and path.parent.name in ContentType.folders()

    @staticmethod
    def is_unified_file(path: Path) -> bool:
        if path.suffix in UNIFIED_FILES_SUFFIXES:
            if path.parent.name in ContentType.folders():
                return path.parent.parent.name not in ContentType.folders()
            if path.parent.parent.name in ContentType.folders():
                return (
                    ContentType.by_path(path) in ContentType.threat_intel_report_types()
                )
        return False

    @staticmethod
    def is_content_item(path: Path) -> bool:
        """Determines whether a file path is of a content item, by one of the following conditions:
        1. If this is a directory
        2. If it's a unified file

        Args:
            path (Path): The file path

        Returns:
            bool: True iff the file path is of a content item.
        """
        return ContentItemParser.is_package(path) or ContentItemParser.is_unified_file(
            path
        )

    def should_skip_parsing(self) -> bool:
        """Returns true if any of the minimal conditions for parsing is not met.

        Returns:
            bool: Whether or not this content item should be parsed.
        """
        return not all(
            [
                self.is_above_marketplace_min_version(),
            ]
        )

    def is_above_marketplace_min_version(self) -> bool:
        return Version(self.toversion) >= Version(MARKETPLACE_MIN_VERSION)

    def add_relationship(
        self,
        relationship: RelationshipType,
        target: str,
        target_type: ContentType,
        **kwargs,
    ) -> None:
        """Adds a single relationship to the collection of the content item relationships.

        Args:
            relationship (Relationship): The relationship type.
            target (str): The identifier of the target content object (e.g, its node_id).
            kwargs: Additional information about the relationship.
        """
        self.relationships.add(
            relationship,
            source_id=self.object_id,
            source_type=self.content_type,
            source_fromversion=self.fromversion,
            source_marketplaces=self.marketplaces,
            target=target,
            target_type=target_type,
            **kwargs,
        )

    def add_to_pack(self, pack_id: Optional[str]) -> None:
        """Creates an IN_PACK relationship between the content item and its pack.

        Args:
            pack_id (Optional[str]): The pack id.
        """
        if not pack_id:
            raise ValueError(f"{self.node_id}: pack ID must have a value.")
        self.add_relationship(RelationshipType.IN_PACK, pack_id, ContentType.PACK)

    def add_dependency_by_id(
        self,
        dependency_id: str,
        dependency_type: ContentType,
        is_mandatory: bool = True,
    ) -> None:
        """Creates a USES_BY_ID relationship between the content item and a given dependency.

        Args:
            dependency_id (str): The dependency id.
            dependency_type (ContentType): The dependency content type.
            is_mandatory (bool, optional): Whether or not the dependency is mandatory. Defaults to True.
        """
        self.add_relationship(
            RelationshipType.USES_BY_ID,
            target=dependency_id,
            target_type=dependency_type,
            mandatorily=is_mandatory,
        )

    def add_dependency_by_name(
        self,
        dependency_name: str,
        dependency_type: ContentType,
        is_mandatory: bool = True,
    ) -> None:
        """Creates a USES_BY_NAME relationship between the content item and a given dependency.

        Args:
            dependency_name (str): The dependency name.
            dependency_type (ContentType): The dependency content type.
            is_mandatory (bool, optional): Whether or not the dependency is mandatory. Defaults to True.
        """
        self.add_relationship(
            RelationshipType.USES_BY_NAME,
            target=dependency_name,
            target_type=dependency_type,
            mandatorily=is_mandatory,
        )

    def add_command_or_script_dependency(
        self, dependency_id: str, is_mandatory: bool = True
    ) -> None:
        """Creates a USES_COMMAND_OR_SCRIPT relationship between the content item and a given dependency.

        Args:
            dependency_id (str): The dependency id.
            is_mandatory (bool, optional): Whether or not the dependency is mandatory. Defaults to True.
        """
        self.add_relationship(
            RelationshipType.USES_COMMAND_OR_SCRIPT,
            target=dependency_id,
            target_type=ContentType.COMMAND_OR_SCRIPT,
            mandatorily=is_mandatory,
        )
