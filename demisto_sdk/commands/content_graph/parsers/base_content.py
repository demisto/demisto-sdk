from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import List, Optional, Type

import pydantic
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import (
    CONTENT_PATH,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StructureError,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class StrictObjectNotExistException(Exception):
    pass


class BaseContentParser(ABC):
    """An abstract class for all content types.

    Attributes:
        object_id (str): The content object ID.
        content_type (ContentType): The content object type.
        node_id (str): The content object node ID.
    """

    content_type: ContentType

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        # The validate_structure method is called in the first child(JsonContentItem, YamlContentItem)
        self.structure_errors: List[StructureError] = Field(default_factory=list)

    @property
    @abstractmethod
    def raw_data(self) -> dict:
        raise NotImplementedError

    def validate_structure(self) -> List[StructureError]:
        """
        This method just calls the external function with the correct arguments.
        PackParser implements it differently, so we use an external function.
        """
        return validate_structure(self.strict_object, self.raw_data, self.content_type)

    @cached_property
    def field_mapping(self):
        return {}

    @property
    @abstractmethod
    def object_id(self) -> Optional[str]:
        pass

    @property
    def node_id(self) -> str:
        return f"{self.content_type}:{self.object_id}"

    @property
    def source_repo(self) -> Optional[str]:
        return CONTENT_PATH.name

    @staticmethod
    def update_marketplaces_set_with_xsoar_values(marketplaces_set: set) -> set:
        if MarketplaceVersions.XSOAR in marketplaces_set:
            marketplaces_set.add(MarketplaceVersions.XSOAR_SAAS)

        if MarketplaceVersions.XSOAR_ON_PREM in marketplaces_set:
            marketplaces_set.add(MarketplaceVersions.XSOAR)
            marketplaces_set.remove(MarketplaceVersions.XSOAR_ON_PREM)

        return marketplaces_set

    @property
    def strict_object(self) -> Type[BaseStrictModel]:
        raise NotImplementedError


def validate_structure(
    strict_object: Type[BaseStrictModel], raw_data: dict, content_type: ContentType
) -> List[StructureError]:
    """
    The function uses the parsed data and attempts to build a Pydantic (strict) object from it.
    Whenever data is invalid by the schema, we store the error in the 'structure_errors' attribute,
    It will fail validation (ST110).
    """
    try:
        strict_object(**raw_data)
    except pydantic.error_wrappers.ValidationError as e:
        return [StructureError(**error) for error in e.errors()]
    except StrictObjectNotExistException:
        logger.debug(
            f"Since {content_type} is not a content item, it has no suitable strict object"
        )
    return []
