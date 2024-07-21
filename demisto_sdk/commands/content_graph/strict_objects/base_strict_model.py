from typing import List, Optional, Union

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import (
    TYPE_JS,
    TYPE_PWSH,
    TYPE_PYTHON,
    Auto,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DEFAULT_DYNAMIC_MODEL,
    DEPRECATED_DYNAMIC_MODEL,
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    REQUIRED_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _CommonFields(BaseStrictModel):
    version: int


CommonFields = create_model(
    model_name="CommonFields",
    base_models=(
        _CommonFields,
        ID_DYNAMIC_MODEL,
    ),
)


class _Argument(BaseStrictModel):
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


Argument = create_model(
    model_name="Argument",
    base_models=(
        _Argument,
        NAME_DYNAMIC_MODEL,
        REQUIRED_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        DEFAULT_DYNAMIC_MODEL,
    ),
)


class Output(BaseStrictModel):
    content_path: Optional[str] = Field(None, alias="contentPath")
    context_path: Optional[str] = Field(None, alias="contextPath")
    description: str
    type: Optional[str] = None


class _Important(BaseModel):
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


Important = create_model(
    model_name="Important", base_models=(_Important, DESCRIPTION_DYNAMIC_MODEL)
)


class ScriptType(StrEnum):
    PWSH = TYPE_PWSH
    PYTHON = TYPE_PYTHON
    JS = TYPE_JS


class StructureError(BaseStrictModel):
    field_name: Optional[tuple] = Field(None, alias="loc")
    error_message: Optional[str] = Field(None, alias="msg")
    error_type: Optional[str] = Field(None, alias="type")
    ctx: Optional[dict] = None


class _BaseIntegrationScript(BaseStrictModel):
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


BaseIntegrationScript = create_model(
    model_name="BaseIntegrationScript",
    base_models=(_BaseIntegrationScript, NAME_DYNAMIC_MODEL, DEPRECATED_DYNAMIC_MODEL),
)
