from abc import ABC
from typing import Any, Optional, Sequence

import pydantic
from pydantic import BaseModel, Extra
from pydantic.fields import FieldInfo

from demisto_sdk.commands.common.constants import MarketplaceVersions

marketplace_suffixes = tuple((marketplace.value for marketplace in MarketplaceVersions))


class BaseStrictModel(BaseModel, ABC):
    class Config:
        """
        This is the definition of not allowing extra fields except those defined by the schema.
        """

        extra = Extra.forbid

    # TODO - When editing all 968 yml files in content, turn on this validator
    # @validator("*")
    # def prevent_none(cls, v):
    #     """
    #     Validator ensures no None value is entered in a field.
    #     There is a difference between an empty and missing field.
    #     Optional means a field can be left out of the schema, but if it does exist, it has to have a value - not None.
    #     """
    #     # The assertion is caught by pydantic and converted to a pydantic.ValidationError


def create_model(model_name: str, base_models: tuple, **kwargs) -> BaseModel:
    """
    Wrapper for pydantic.create_model so type:ignore[call-overload] appears only once.
    """
    return pydantic.create_model(
        __model_name=model_name, __base__=base_models, **kwargs
    )  # type:ignore[call-overload]


def create_dynamic_model(
    field_name: str,
    type_: Any,
    default: Any = ...,
    suffixes: Sequence[str] = marketplace_suffixes,
    alias: Optional[str] = None,
    include_without_suffix: bool = False,
) -> BaseModel:
    """
    This function creates a sub-model for avoiding duplicate lines of parsing arguments with different suffix.
    (we have fields that are almost identical, except for the suffix.
     for example: description:xsoar, description:marketplacev2, description:xpanse etc.)
    Then the strict models inherit it, thus adding those fields to the root.

    This is a better way than declaring on those fields manually in the root object, in this way:
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(None, alias="description:marketplacev2")
    """
    fields = {
        f"{field_name}_{suffix}": (
            type_,
            FieldInfo(default, alias=f"{alias or field_name}:{suffix}"),
        )
        for suffix in suffixes
    }
    if include_without_suffix:
        fields[field_name] = (type_, FieldInfo(default, alias=alias or field_name))

    return create_model(
        model_name=f"Dynamic{field_name.title()}Model",
        base_models=(BaseStrictModel,),
        **fields,
    )


DESCRIPTION_DYNAMIC_MODEL = create_dynamic_model(
    field_name="description", type_=Optional[str], default=None
)
NAME_DYNAMIC_MODEL = create_dynamic_model(
    field_name="name", type_=Optional[str], default=None
)
DEPRECATED_DYNAMIC_MODEL = deprecated_dynamic_model = create_dynamic_model(
    field_name="deprecated", type_=Optional[bool], default=None
)
REQUIRED_DYNAMIC_MODEL = create_dynamic_model(
    field_name="required", type_=Optional[bool], default=None
)
DEFAULT_DYNAMIC_MODEL = create_dynamic_model(
    field_name="defaultValue",
    type_=Optional[Any],
    default=None,
    include_without_suffix=True,
)
# field name here defaultvalue vs defaultValue
DEFAULT_DYNAMIC_MODEL_LOWER_CASE = create_dynamic_model(
    field_name="defaultvalue",
    type_=Optional[Any],
    default=None,
    include_without_suffix=True,
)
ID_DYNAMIC_MODEL = create_dynamic_model(
    field_name="id",
    type_=Optional[Any],
    default=None,
    include_without_suffix=True,
)
