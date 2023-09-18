from abc import ABC, abstractmethod
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Type,
    cast,
)

import demisto_client
from packaging.version import Version
from pydantic import BaseModel, DirectoryPath, Field
from pydantic.main import ModelMetaclass

import demisto_sdk.commands.content_graph.parsers.content_item
from demisto_sdk.commands.common.constants import (
    MARKETPLACE_MIN_VERSION,
    PACKS_FOLDER,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    LazyProperty,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    InvalidContentItemException,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.pack import PackParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData

content_type_to_model: Dict[ContentType, Type["BaseContent"]] = {}
json = JSON_Handler()


class BaseContentMetaclass(ModelMetaclass):
    def __new__(
        cls, name, bases, namespace, content_type: ContentType = None, **kwargs
    ):
        """This method is called before every creation of a ContentItem *class* (NOT class instances!).
        If `content_type` is passed as an argument of the class, we add a mapping between the content type
        and the model class object.

        In case there are lazy properties in the class model, will add them as a class member so we would be able
        to load them during graph creation

        After all the model classes are created, `content_type_to_model` has a full mapping between content types
        and models, and only then we are ready to determine which model class to use based on a content item's type.

        Args:
            name: The class object name (e.g., Integration)
            bases: The bases of the class object (e.g., [YAMLContentItem, ContentItem, BaseContent])
            namespace: The namespaces of the class object.
            content_type (ContentType, optional): The type corresponds to the class (e.g., ContentType.INTEGRATIONS)

        Returns:
            BaseContent: The model class.
        """
        super_cls: BaseContentMetaclass = super().__new__(cls, name, bases, namespace)
        # for type checking
        model_cls: Type["BaseContent"] = cast(Type["BaseContent"], super_cls)
        if content_type:
            content_type_to_model[content_type] = model_cls
            model_cls.content_type = content_type

        if lazy_properties := {
            attr
            for attr in dir(model_cls)
            if isinstance(getattr(super_cls, attr), LazyProperty)
        }:
            model_cls._lazy_properties = lazy_properties  # type: ignore[attr-defined]
        return model_cls


class BaseContent(ABC, BaseModel, metaclass=BaseContentMetaclass):
    database_id: Optional[str] = Field(None, exclude=True)  # used for the database
    object_id: str = Field(alias="id")
    content_type: ClassVar[ContentType] = Field(include=True)
    source_repo: str = "content"
    node_id: str
    marketplaces: List[MarketplaceVersions] = list(MarketplaceVersions)

    relationships_data: Dict[RelationshipType, Set["RelationshipData"]] = Field(
        defaultdict(set), exclude=True, repr=False
    )

    class Config:
        arbitrary_types_allowed = (
            True  # allows having custom classes for properties in model
        )
        orm_mode = True  # allows using from_orm() method
        allow_population_by_field_name = True  # when loading from orm, ignores the aliases and uses the property name

    def __getstate__(self):
        """Needed to for the object to be pickled correctly (to use multiprocessing)"""
        if "relationships_data" not in self.__dict__:
            # if we don't have relationships, we can use the default __getstate__ method
            return super().__getstate__()

        dict_copy = self.__dict__.copy()
        # This avoids circular references when pickling store only the first level relationships.
        relationships_data_copy = dict_copy["relationships_data"].copy()
        dict_copy["relationships_data"] = defaultdict(set)
        for _, relationship_data in relationships_data_copy.items():
            for r in relationship_data:
                # override the relationships_data of the content item to avoid circular references
                r: RelationshipData  # type: ignore[no-redef]
                r_copy = r.copy()
                content_item_to_copy = r_copy.content_item_to.copy()
                r_copy.content_item_to = content_item_to_copy
                content_item_to_copy.relationships_data = defaultdict(set)
                dict_copy["relationships_data"][r.relationship_type].add(r_copy)

        return {
            "__dict__": dict_copy,
            "__fields_set__": self.__fields_set__,
        }

    @property
    def normalize_name(self) -> str:
        # if has name attribute, return it, otherwise return the object id
        return self.object_id

    def __add_lazy_properties(self):
        """
        This method would load the lazy properties into the model by calling their property methods.
        Lazy properties are not loaded into the model until they are called directly.
        """
        if hasattr(self, "_lazy_properties"):
            for _property in self._lazy_properties:  # type: ignore[attr-defined]
                getattr(self, _property)

    def to_dict(self) -> Dict[str, Any]:
        """
        This function is used to create the graph nodes, we use this method when creating the graph.
        when creating the graph we want to load the lazy properties into the model.

        We use it instead of `self.dict()` because sometimes we need only the primitive values.

        Returns:
            Dict[str, Any]: JSON dictionary representation of the class.
        """
        self.__add_lazy_properties()

        json_dct = json.loads(self.json(exclude={"commands", "database_id"}))
        if "path" in json_dct and Path(json_dct["path"]).is_absolute():
            json_dct["path"] = (Path(json_dct["path"]).relative_to(CONTENT_PATH)).as_posix()  # type: ignore
        json_dct["content_type"] = self.content_type

        return json_dct

    @staticmethod
    @lru_cache
    def from_path(path: Path) -> Optional["BaseContent"]:
        logger.debug(f"Loading content item from path: {path}")
        if (
            path.is_dir() and path.parent.name == PACKS_FOLDER
        ):  # if the path given is a pack
            try:
                return content_type_to_model[ContentType.PACK].from_orm(
                    PackParser(path)
                )
            except InvalidContentItemException:
                logger.error(f"Could not parse content from {str(path)}")
                return None
        try:
            content_item_parser = ContentItemParser.from_path(path)
        except NotAContentItemException:
            # This is a workaround because `create-content-artifacts` still creates deprecated content items
            demisto_sdk.commands.content_graph.parsers.content_item.MARKETPLACE_MIN_VERSION = (
                "0.0.0"
            )
            try:
                content_item_parser = ContentItemParser.from_path(path)
            except NotAContentItemException:
                logger.error(
                    f"Invalid content path provided: {str(path)}. Please provide a valid content item or pack path."
                )
                return None
            demisto_sdk.commands.content_graph.parsers.content_item.MARKETPLACE_MIN_VERSION = (
                MARKETPLACE_MIN_VERSION
            )
        except InvalidContentItemException:
            logger.error(
                f"Invalid content path provided: {str(path)}. Please provide a valid content item or pack path."
            )
            return None

        model = content_type_to_model.get(content_item_parser.content_type)
        logger.debug(f"Loading content item from path: {path} as {model}")
        if not model:
            logger.error(f"Could not parse content item from path: {path}")
            return None
        try:
            return model.from_orm(content_item_parser)
        except Exception as e:
            logger.error(
                f"Could not parse content item from path: {path}: {e}. Parser class: {content_item_parser}"
            )
            return None

    @abstractmethod
    def dump(
        self,
        path: DirectoryPath,
        marketplace: MarketplaceVersions,
    ) -> None:
        pass

    def upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        target_demisto_version: Version,
        **kwargs,
    ) -> None:
        # Implemented at the ContentItem/Pack level rather than here
        raise NotImplementedError()

    def add_relationship(
        self, relationship_type: RelationshipType, relationship: "RelationshipData"
    ) -> None:
        if relationship.content_item_to == self:
            # skip adding circular dependency
            return
        self.relationships_data[relationship_type].add(relationship)


class UnknownContent(BaseContent):
    """A model for non-existing content items used by existing content items."""

    not_in_repository: bool = True
    node_id: str = ""  # just because it's missing from the db
    object_id: str = ""
    name: str = ""

    def dump(self, _, __):
        ...

    @property
    def identifier(self):
        return self.object_id or self.name
