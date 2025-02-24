import inspect
from abc import ABC
from collections import defaultdict
from functools import cached_property, lru_cache
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    cast,
)

import demisto_client
from packaging.version import Version
from pydantic import BaseModel, DirectoryPath, Field
from pydantic.main import ModelMetaclass

from demisto_sdk.commands.common.constants import (
    DEFAULT_SUPPORTED_MODULES,
    MARKETPLACE_MIN_VERSION,
    PACKS_FOLDER,
    PACKS_PACK_META_FILE_NAME,
    GitStatuses,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import set_value, write_dict
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    LazyProperty,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.parsers import content_item
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    InvalidContentItemException,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StructureError,
)

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData

CONTENT_TYPE_TO_MODEL: Dict[ContentType, Type["BaseContent"]] = {}
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
            bases: The bases of the class object (e.g., [YAMLContentItem, ContentItem, BaseNode])
            namespace: The namespaces of the class object.
            content_type (ContentType, optional): The type corresponds to the class (e.g., ContentType.INTEGRATIONS)

        Returns:
            BaseNode: The model class.
        """
        super_cls: BaseContentMetaclass = super().__new__(cls, name, bases, namespace)
        # for type checking
        model_cls: Type["BaseContent"] = cast(Type["BaseContent"], super_cls)
        if content_type:
            CONTENT_TYPE_TO_MODEL[content_type] = model_cls
            model_cls.content_type = content_type

        if lazy_properties := {
            attr
            for attr in dir(model_cls)
            if isinstance(getattr(super_cls, attr), LazyProperty)
        }:
            model_cls._lazy_properties = lazy_properties  # type: ignore[attr-defined]

        return model_cls


class BaseNode(ABC, BaseModel, metaclass=BaseContentMetaclass):
    database_id: Optional[str] = Field(None, exclude=True)  # used for the database
    object_id: str = Field(alias="id")
    content_type: ClassVar[ContentType] = Field(include=True)
    source_repo: str = "content"
    node_id: str
    marketplaces: List[MarketplaceVersions] = list(MarketplaceVersions)
    supportedModules: List[str] = DEFAULT_SUPPORTED_MODULES
    relationships_data: Dict[RelationshipType, Set["RelationshipData"]] = Field(
        defaultdict(set), exclude=True, repr=False
    )

    class Config:
        arbitrary_types_allowed = (
            True  # allows having custom classes for properties in model
        )
        orm_mode = True  # allows using from_orm() method
        allow_population_by_field_name = True  # when loading from orm, ignores the aliases and uses the property name
        keep_untouched = (cached_property,)

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
        cached_properties = {
            name
            for name, value in inspect.getmembers(self.__class__)
            if isinstance(value, cached_property)
        }
        json_dct = json.loads(
            self.json(
                exclude={
                    "commands",
                    "database_id",
                }
                | cached_properties
            )
        )
        if "path" in json_dct and Path(json_dct["path"]).is_absolute():
            json_dct["path"] = (
                Path(json_dct["path"]).relative_to(CONTENT_PATH)
            ).as_posix()  # type: ignore
        json_dct["content_type"] = self.content_type
        return json_dct

    def add_relationship(
        self, relationship_type: RelationshipType, relationship: "RelationshipData"
    ) -> None:
        if relationship.content_item_to == self:
            # skip adding circular dependency
            return
        self.relationships_data[relationship_type].add(relationship)


class BaseContent(BaseNode):
    field_mapping: dict = Field({}, exclude=True)
    path: Path
    git_status: Optional[GitStatuses]
    git_sha: Optional[str]
    old_base_content_object: Optional["BaseContent"] = None
    related_content_dict: dict = Field({}, exclude=True)
    structure_errors: List[StructureError] = Field(default_factory=list, exclude=True)

    def _save(
        self,
        path: Path,
        data: dict,
        predefined_keys_to_keep: Optional[Tuple[str, ...]] = None,
        fields_to_exclude: List[str] = [],
    ):
        """Save the class vars into the dict data.

        Args:
            path (Path): The path of the file to save the new data into.
            data (dict): the data dict.
            predefined_keys_to_keep (Optional[Tuple[str]], optional): keys to keep even if they're not defined.
        """
        for key, val in self.field_mapping.items():
            attr = getattr(self, key)
            if key == "docker_image":
                attr = str(attr)
            elif key in fields_to_exclude:
                continue
            elif key == "marketplaces":
                if (
                    MarketplaceVersions.XSOAR_SAAS in attr
                    and MarketplaceVersions.XSOAR in attr
                ):
                    attr.remove(MarketplaceVersions.XSOAR_SAAS)
                if (
                    MarketplaceVersions.XSOAR_ON_PREM in attr
                    and MarketplaceVersions.XSOAR in attr
                ):
                    attr.remove(MarketplaceVersions.XSOAR_ON_PREM)
            if attr or (predefined_keys_to_keep and val in predefined_keys_to_keep):
                set_value(data, val, attr)
        write_dict(path, data, indent=4)

    def __hash__(self):
        return hash(self.path)

    def save(self):
        raise NotImplementedError

    @property
    def ignored_errors(self) -> List[str]:
        raise NotImplementedError

    def ignored_errors_related_files(self, file_path: Path) -> List[str]:
        """Return the errors that should be ignored for the given related file path.

        Args:
            file_path (str): The path of the file we want to get list of ignored errors for.

        Returns:
            list: The list of the ignored error codes.
        """
        raise NotImplementedError

    def dump(
        self,
        path: DirectoryPath,
        marketplace: MarketplaceVersions,
    ) -> None:
        raise NotImplementedError

    def upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        target_demisto_version: Version,
        **kwargs,
    ) -> None:
        # Implemented at the ContentItem/Pack level rather than here
        raise NotImplementedError()

    @staticmethod
    @lru_cache
    def from_path(
        path: Path,
        git_sha: Optional[str] = None,
        raise_on_exception: bool = False,
        metadata_only: bool = False,
    ) -> Optional["BaseContent"]:
        logger.debug(f"Loading content item from {path}")

        if (
            path.is_dir()
            and path.parent.name == PACKS_FOLDER
            or path.name == PACKS_PACK_META_FILE_NAME
        ):  # if the path given is a pack
            try:
                return CONTENT_TYPE_TO_MODEL[ContentType.PACK].from_orm(
                    PackParser(path, git_sha=git_sha, metadata_only=metadata_only)
                )
            except InvalidContentItemException:
                logger.error(f"Could not parse content from {path}")
                return None
        try:
            content_item.MARKETPLACE_MIN_VERSION = "0.0.0"
            content_item_parser = ContentItemParser.from_path(path, git_sha=git_sha)
            content_item.MARKETPLACE_MIN_VERSION = MARKETPLACE_MIN_VERSION

        except (NotAContentItemException, InvalidContentItemException) as e:
            if raise_on_exception:
                raise
            logger.error(
                f"Invalid content path provided: {path}. Please provide a valid content item or pack path. ({type(e).__name__})"
            )
            return None

        model = CONTENT_TYPE_TO_MODEL.get(content_item_parser.content_type)
        if model:
            logger.debug(f"Detected model {model} for {path.name}")
        else:
            logger.error(f"Could not parse content item from {path.name}")
            return None

        try:
            return model.from_orm(content_item_parser)  # type: ignore
        except Exception:
            logger.exception(
                f"Could not parse content item from path {path} using {content_item_parser}"
            )
            return None

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        pass


class UnknownContent(BaseNode):
    """A model for non-existing content items used by existing content items."""

    not_in_repository: bool = True
    node_id: str = ""  # just because it's missing from the db
    object_id: str = ""
    name: str = ""

    def dump(self, _, __): ...

    @property
    def identifier(self):
        return self.object_id or self.name
