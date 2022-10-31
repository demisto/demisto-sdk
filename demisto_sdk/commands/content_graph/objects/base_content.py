import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Set, Type, cast

from pydantic import BaseModel, DirectoryPath, Field
from pydantic.main import ModelMetaclass

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.relationship import \
        RelationshipData

content_type_to_model: Dict[ContentType, Type["BaseContent"]] = {}


class ContentModelMetaclass(ModelMetaclass):
    def __new__(
        cls, name, bases, namespace, content_type: ContentType = None, **kwargs
    ):
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
        super_cls: ContentModelMetaclass = super().__new__(cls, name, bases, namespace)
        # for type checking
        model_cls: Type["BaseContent"] = cast(Type["BaseContent"], super_cls)
        if content_type:
            content_type_to_model[content_type] = model_cls
            model_cls.content_type = content_type
        return model_cls


class BaseContent(ABC, BaseModel, metaclass=ContentModelMetaclass):
    object_id: str = Field(alias="id")
    content_type: ClassVar[ContentType] = Field(include=True)
    marketplaces: List[MarketplaceVersions] = list(
        MarketplaceVersions
    )  # TODO check if default
    node_id: str
    relationships_data: Set["RelationshipData"] = Field(
        set(), exclude=True, repr=False
    )  # too much data in the repr

    class Config:
        arbitrary_types_allowed = True  # allows having custom classes for properties in model
        orm_mode = True  # allows using from_orm() method
        allow_population_by_field_name = True  # when loading from orm, ignores the aliases and uses the property name

    def to_dict(self) -> Dict[str, Any]:
        """
        This returns a JSON dictionary representation of the class.
        We use it instead of `self.dict()` because sometimes we need only the primitive values.

        Returns:
            Dict[str, Any]: _description_
        """

        json_dct = json.loads(self.json())
        json_dct['content_type'] = self.content_type
        return json_dct

    @abstractmethod
    def dump(self, path: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        pass


class ServerContent(BaseContent):
    not_in_repository: bool = True
    node_id: str = ""  # just because it's missing from the db
    object_id: str = ""

    def dump(self, _, __):
        ...
