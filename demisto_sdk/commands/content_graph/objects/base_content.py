import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Set, Type, cast

from pydantic import BaseModel, DirectoryPath, Field
from pydantic.main import ModelMetaclass

import demisto_sdk.commands.content_graph.parsers.content_item
from demisto_sdk.commands.common.constants import MARKETPLACE_MIN_VERSION, MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser
from demisto_sdk.commands.content_graph.parsers.pack import PackParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData

logger = logging.getLogger('demisto-sdk')

content_type_to_model: Dict[ContentType, Type["BaseContent"]] = {}


class BaseContentMetaclass(ModelMetaclass):
    def __new__(cls, name, bases, namespace, content_type: ContentType = None, **kwargs):
        """This method is called before every creation of a ContentItem *class* (NOT class instances!).
        If `content_type` is passed as an argument of the class, we add a mapping between the content type
        and the model class object.

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
        return model_cls


class BaseContent(ABC, BaseModel, metaclass=BaseContentMetaclass):
    object_id: str = Field(alias="id")
    content_type: ClassVar[ContentType] = Field(include=True)
    node_id: str
    marketplaces: List[MarketplaceVersions] = list(MarketplaceVersions)

    relationships_data: Dict[RelationshipType, Set["RelationshipData"]] = Field(defaultdict(set), exclude=True, repr=False)

    class Config:
        arbitrary_types_allowed = True  # allows having custom classes for properties in model
        orm_mode = True  # allows using from_orm() method
        allow_population_by_field_name = True  # when loading from orm, ignores the aliases and uses the property name

    def __getstate__(self):
        """Needed to for the object to be pickled correctly (to use multiprocessing)"""
        state = self.__dict__.copy()

        # This object cannot be pickled
        del state["relationships_data"]
        return state

    def __setstate__(self, state) -> None:
        """Needed to for the object to be pickled correctly (to use multiprocessing)"""
        self.__dict__.update(state)

    @property
    def normalize_name(self) -> str:
        # if has name attribute, return it, otherwise return the object id
        return self.object_id

    def to_dict(self) -> Dict[str, Any]:
        """
        This returns a JSON dictionary representation of the class.
        We use it instead of `self.dict()` because sometimes we need only the primitive values.

        Returns:
            Dict[str, Any]: _description_
        """

        json_dct = json.loads(self.json())
        json_dct["content_type"] = self.content_type
        return json_dct

    @staticmethod
    def from_path(path: Path) -> Optional["BaseContent"]:
        logger.info(f'Loading content item from path: {path}')
        if path.is_dir() and path.parent.name == 'Packs':  # if the path given is a pack
            return content_type_to_model[ContentType.PACK].from_orm(PackParser(path))
        content_item_parser = ContentItemParser.from_path(path)

        if not content_item_parser:
            # This is a workaround because `create-content-artifacts` still creates deprecated content items
            demisto_sdk.commands.content_graph.parsers.content_item.MARKETPLACE_MIN_VERSION = '0.0.0'
            content_item_parser = ContentItemParser.from_path(path)
            demisto_sdk.commands.content_graph.parsers.content_item.MARKETPLACE_MIN_VERSION = MARKETPLACE_MIN_VERSION

        if not content_item_parser:  # if we still can't parse the content item
            logger.error(f"Could not parse content item from path: {path}")
            return None

        model = content_type_to_model.get(content_item_parser.content_type)
        logger.info(f'Loading content item from path: {path} as {model}')
        if not model:
            logger.error(f"Could not parse content item from path: {path}")
            return None
        try:
            return model.from_orm(content_item_parser)
        except Exception as e:
            logger.error(f"Could not parse content item from path: {path}: {e}. Parser class: {content_item_parser}")
            return None

    @abstractmethod
    def dump(self, path: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        pass


class ServerContent(BaseContent):
    not_in_repository: bool = True
    node_id: str = ""  # just because it's missing from the db
    object_id: str = ""

    def dump(self, _, __):
        ...
