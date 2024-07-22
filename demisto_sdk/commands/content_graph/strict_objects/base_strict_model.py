from enum import Enum
from typing import Any, List, Optional, Union

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


class Enum0123(Enum):
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3


class ExtractSettings(BaseStrictModel):
    field_cli_name_to_extract_settings: Optional[Any] = Field(
        None, alias="fieldCliNameToExtractSettings"
    )
    mode: Optional[str] = None


class _StrictGenericIncidentType(BaseStrictModel):
    id_: str = Field(..., alias="id")
    version: int
    vc_should_ignore: Optional[bool] = Field(None, alias="vcShouldIgnore")
    sort_values: Optional[Any] = Field(None, alias="sortValues")
    locked: Optional[bool] = None
    name: str
    prev_name: Optional[str] = Field(None, alias="prevName")
    color: str
    sla: Optional[int] = None
    sla_reminder: Optional[int] = Field(None, alias="slaReminder")
    playbook_id: Optional[str] = Field(None, alias="playbookId")
    hours: Optional[int] = None
    days: Optional[int] = None
    weeks: Optional[int] = None
    hours_r: Optional[int] = Field(None, alias="hoursR")
    days_r: Optional[int] = Field(None, alias="daysR")
    weeks_r: Optional[int] = Field(None, alias="weeksR")
    system: Optional[bool] = None
    readonly: Optional[bool] = None
    default: Optional[bool] = None
    autorun: Optional[bool] = None
    pre_processing_script: Optional[str] = Field(None, alias="preProcessingScript")
    closure_script: Optional[str] = Field(None, alias="closureScript")
    disabled: Optional[bool] = None
    reputation_calc: Optional[Enum0123] = Field(None, alias="reputationCalc")
    on_change_rep_alg: Optional[Enum0123] = Field(None, alias="onChangeRepAlg")
    detached: Optional[bool] = None
    from_version: Optional[str] = Field(None, alias="fromVersion")
    to_version: Optional[str] = Field(None, alias="toVersion")
    layout: Optional[str] = None
    extract_settings: Optional[ExtractSettings] = Field(None, alias="extractSettings")


StrictGenericIncidentType = create_model(
    model_name="_StrictGenericIncidentType",
    base_models=(
        _StrictGenericIncidentType,
        NAME_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
    ),
)
