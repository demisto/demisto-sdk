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
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StructureError,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


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
        raise NotImplementedError  # to be implemented in inheriting classes

    def validate_structure(self) -> List[StructureError]:
        """
        This method just calls the external function with the correct arguments.
        Some parsers may implement it differently (e.g. running on multiple files per parser), see Pack and ModelingRules as examples.
        """
        return validate_structure(self.strict_object, self.raw_data, self.path)

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
        raise NotImplementedError  # implemented in inheriting classes


def validate_structure(
    strict_object: Type[BaseStrictModel], raw_data: dict, path: Path
) -> List[StructureError]:
    """
    The function uses the parsed data and attempts to build a Pydantic (strict) object from it.
    Whenever the data and schema mismatch, we store the error using the 'structure_errors' attribute,
    which will be read during the ST110 validation run.
    """
    try:
        strict_object(**raw_data)
    except pydantic.error_wrappers.ValidationError as e:
        return [StructureError(path=path, **error) for error in e.errors()]
    return []
