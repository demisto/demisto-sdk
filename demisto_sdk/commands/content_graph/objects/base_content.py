import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, cast

from pydantic import BaseModel, DirectoryPath, Field
from pydantic.main import ModelMetaclass

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType

content_type_to_model: Dict[ContentType, Type['BaseContent']] = {}


class ContentModelMetaclass(ModelMetaclass):
    def __new__(cls, name, bases, namespace, content_type: ContentType = None, **kwargs):
        """ This method is called before every creation of a ContentItem *class* (NOT class instances!).
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
            ContentItem: The model class.
        """
        super_cls: ContentModelMetaclass = super().__new__(cls, name, bases, namespace)
        # for type checking
        model_cls: Type['BaseContent'] = cast(Type['BaseContent'], super_cls)
        if content_type:
            content_type_to_model[content_type] = model_cls
            model_cls.content_type = content_type
        return model_cls


class BaseContent(ABC, BaseModel, metaclass=ContentModelMetaclass):
    object_id: str = Field(alias='id')
    content_type: ContentType
    marketplaces: List[MarketplaceVersions]
    node_id: str

    class Config:
        arbitrary_types_allowed = True  # allows having custom classes for properties in model
        orm_mode = True  # allows using from_orm() method
        allow_population_by_field_name = True  # when loading from orm, ignores the aliases and uses the property name

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.json())

    @abstractmethod
    def dump(self, path: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        pass
