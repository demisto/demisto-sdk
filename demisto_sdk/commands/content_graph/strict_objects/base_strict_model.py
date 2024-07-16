from abc import ABC
from typing import Any, List, Optional, Sequence, Union

from pydantic import BaseModel, Extra, Field, validator
from pydantic.fields import FieldInfo

from demisto_sdk.commands.common.constants import (
    TYPE_JS,
    TYPE_PWSH,
    TYPE_PYTHON,
    Auto,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.content_graph.strict_objects.common import create_model

marketplace_suffixes = [marketplace.value for marketplace in MarketplaceVersions]


class BaseStrictModel(BaseModel, ABC):
    class Config:
        """
        This is the definition of not allowing extra fields except those defined by the schema.
        """

        extra = Extra.forbid

    @validator("*")
    def prevent_none(cls, v):
        """
        Validator ensures no None value is entered in a field.
        """
        assert v is not None, f"{v} may not be None"
        return v


def create_dynamic_model(
    field_name: str,
    type_: Any,
    default: Any = ...,
    suffixes: Sequence[str] = tuple(marketplace_suffixes),
    alias: Optional[str] = None,
    include_without_suffix: bool = False,
) -> BaseModel:
    """
    This function creates a sub-model for avoiding duplicate lines of parsing arguments with different suffix.
    (we have fields that are almost identical, except for the suffix.
     for example: description:xsoar, description:marketplacev2, description:xpanse etc.)
    Then the model inherit it for adding those fields to the root.

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
ID_DYNAMIC_MODEL = create_dynamic_model(
    field_name="id",
    type_=Optional[Any],
    default=None,
    include_without_suffix=True,
)


class CommonFields(BaseStrictModel):
    id_: str = Field(..., alias="id")
    version: int
    id_xsoar: str = Field(None, alias="id:xsoar")
    id_marketplacev2: str = Field(None, alias="id:marketplacev2")
    id_xsoar_saas: str = Field(None, alias="id:xsoar_saas")
    id_xsoar_on_prem: str = Field(None, alias="id:xsoar_on_prem")


class Argument(BaseModel):
    __base__ = (
        BaseStrictModel,
        NAME_DYNAMIC_MODEL,
        REQUIRED_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        DEFAULT_DYNAMIC_MODEL,
    )
    name: str
    required: Optional[bool] = None
    default: Optional[bool] = None
    description: str
    auto: Optional[Auto] = None
    predefined: Optional[List[str]] = None
    is_array: Optional[bool] = Field(None, alias="isArray")
    secret: Optional[bool] = None
    deprecated: Optional[bool] = None
    type: Optional[str] = None
    hidden: Optional[bool] = None


class Output(BaseStrictModel):
    content_path: Optional[str] = Field(None, alias="contentPath")
    context_path: Optional[str] = Field(None, alias="contextPath")
    description: str
    type: Optional[str] = None


class Important(BaseModel):
    __base__ = (DESCRIPTION_DYNAMIC_MODEL,)
    # not inheriting from StrictBaseModel since dynamic_models do
    context_path: str = Field(..., alias="contextPath")
    description: str
    related: Optional[str] = None
    description_xsoar: Optional[str] = Field(None, alias="contextPath")
    description_marketplacev2: Optional[str] = Field(
        None, alias="description:marketplacev2"
    )
    description_xpanse: Optional[str] = Field(None, alias="description:xpanse")
    description_xsoar_saas: Optional[str] = Field(None, alias="description:xsoar_saas")
    description_xsoar_on_prem: Optional[str] = Field(
        None, alias="description:xsoar_on_prem"
    )


class ScriptType(StrEnum):
    PWSH = TYPE_PWSH
    PYTHON = TYPE_PYTHON
    JS = TYPE_JS


class StructureError(BaseStrictModel):
    field_name: Optional[tuple] = Field(
        None, alias="loc"
    )  # the api returns here tuple, not str for this key
    error_message: Optional[str] = Field(None, alias="msg")
    error_type: Optional[str] = Field(None, alias="type")
    ctx: Optional[dict] = None


class BaseIntegrationScript(BaseStrictModel):
    __base__ = (NAME_DYNAMIC_MODEL, DEPRECATED_DYNAMIC_MODEL)
    name: str
    deprecated: Optional[bool] = None
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    system: Optional[bool] = None
    tests: Optional[List[str]] = None
    auto_update_docker_image: Optional[bool] = Field(
        None, alias="autoUpdateDockerImage"
    )
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = None
