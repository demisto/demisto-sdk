from typing import Any, Optional, Type, Union

import pydantic
from pydantic import BaseModel, Extra, Field
from pydantic.fields import FieldInfo

from demisto_sdk.commands.common.constants import (
    TYPE_JS,
    TYPE_PWSH,
    TYPE_PYTHON,
    Auto,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.StrEnum import StrEnum

marketplace_suffixes = [marketplace.value for marketplace in MarketplaceVersions]


def create_dynamic_model(
    field_name: str,
    type_: Type,
    default: Any = ...,
    suffixes: list[str] = marketplace_suffixes,
    alias: Optional[str] = None,
):
    """
    This function creates a sub-model for avoiding duplicate lines of parsing arguments with different suffix.
    (we have fields that are almost identical, except for the suffix.
     for example: description:xsoar, description:marketplacev2, description:xpanse etc.)
    Then the model inherit it for adding those fields to the root.

    This is a better way than declaring on those fields manually in the root object, in this way:
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(None, alias="description:marketplacev2")
    """
    return pydantic.create_model(
        f"Dynamic{field_name.title()}Model",
        **{
            f"{field_name}_{suffix}": (
                type_,
                FieldInfo(default, alias=f"{alias or field_name}:{suffix}"),
            )
            for suffix in suffixes
        },
        __base__=BaseStrictModel,
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


class BaseStrictModel(BaseModel):
    class Config:
        """
        This is the definition of not allowing extra fields except those defined by the schema.
        """

        extra = Extra.forbid


class CommonFields(BaseStrictModel):
    id_: str = Field(..., alias="id")
    version: int
    id_xsoar: str = Field(None, alias="id:xsoar")
    id_marketplacev2: str = Field(None, alias="id:marketplacev2")
    id_xsoar_saas: str = Field(None, alias="id:xsoar_saas")
    id_xsoar_on_prem: str = Field(None, alias="id:xsoar_on_prem")


class Argument(BaseStrictModel):
    name: str
    required: Optional[bool] = None
    default: Optional[bool] = None
    description: str
    auto: Optional[Auto] = None
    predefined: Optional[list[str]] = None
    is_array: Optional[bool] = Field(None, alias="isArray")
    default_value: Optional[Any] = Field(None, alias="defaultValue")
    secret: Optional[bool] = None
    deprecated: Optional[bool] = None
    type: Optional[str] = None
    hidden: Optional[bool] = None
    name_xsoar: Optional[str] = Field(None, alias="name:xsoar")
    name_marketplacev2: Optional[str] = Field(None, alias="name:marketplacev2")
    name_xpanse: Optional[str] = Field(None, alias="name:xpanse")
    name_xsoar_saas: Optional[str] = Field(None, alias="name:xsoar_saas")
    name_xsoar_on_prem: Optional[str] = Field(None, alias="name:xsoar_on_prem")
    required_xsoar: Optional[bool] = Field(None, alias="required:xsoar")
    required_marketplacev2: Optional[bool] = Field(None, alias="required:marketplacev2")
    required_xsoar_saas: Optional[bool] = Field(None, alias="required:xsoar_saas")
    required_xsoar_on_prem: Optional[bool] = Field(None, alias="required:xsoar_on_prem")
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(
        None, alias="description:marketplacev2"
    )
    description_xpanse: Optional[str] = Field(None, alias="description:xpanse")
    description_xsoar_saas: Optional[str] = Field(None, alias="description:xsoar_saas")
    description_xsoar_on_prem: Optional[str] = Field(
        None, alias="description:xsoar_on_prem"
    )
    default_value_xsoar: Optional[Any] = Field(None, alias="defaultValue:xsoar")
    default_value_marketplace_v2: Optional[Any] = Field(
        None, alias="defaultValue:marketplacev2"
    )
    default_value_xpanse: Optional[Any] = Field(None, alias="defaultValue:xpanse")
    default_value_xsoar_saas: Optional[Any] = Field(
        None, alias="defaultValue:xsoar_saas"
    )
    default_value_xsoar_on_prem: Optional[Any] = Field(
        None, alias="defaultValue:xsoar_on_prem"
    )
    deprecated_xsoar: Optional[bool] = Field(None, alias="deprecated:xsoar")
    deprecated_marketplace_v2: Optional[bool] = Field(
        None, alias="deprecated:marketplacev2"
    )
    deprecated_xpanse: Optional[bool] = Field(None, alias="deprecated:xpanse")
    deprecated_xsoar_saas: Optional[bool] = Field(None, alias="deprecated:xsoar_saas")
    deprecated_xsoar_on_prem: Optional[bool] = Field(
        None, alias="deprecated:xsoar_on_prem"
    )


class Output(BaseStrictModel):
    content_path: Optional[str] = Field(None, alias="contentPath")
    context_path: Optional[str] = Field(None, alias="contextPath")
    description: str
    type: Optional[str] = None


dynamic_models_for_important: tuple = (DESCRIPTION_DYNAMIC_MODEL,)


class Important(*dynamic_models_for_important):
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


class SturctureError(BaseStrictModel):
    field_name: Optional[tuple] = Field(
        None, alias="loc"
    )  # the api returns here tuple, not str for this key
    error_message: Optional[str] = Field(None, alias="msg")
    error_type: Optional[str] = Field(None, alias="type")
    ctx: Optional[dict] = None


dynamic_models: tuple = (
    NAME_DYNAMIC_MODEL,
    DEPRECATED_DYNAMIC_MODEL,
)


class BaseIntegrationScript(*dynamic_models):
    # not inheriting from StrictBaseModel since dynamic_models do
    name: str
    deprecated: Optional[bool] = None
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    system: Optional[bool] = None
    tests: Optional[list[str]] = None
    auto_update_docker_image: Optional[bool] = Field(
        None, alias="autoUpdateDockerImage"
    )
    marketplaces: Union[MarketplaceVersions, list[MarketplaceVersions]] = None
