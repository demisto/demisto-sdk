from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple, Union

import more_itertools
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
    create_dynamic_model,
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
    prettyname: Optional[str] = None
    pretty_predefined: Optional[dict] = Field(None, alias="prettypredefined")
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


HIDDEN_MARKETPLACE_V2_DYNAMIC_MODEL = create_dynamic_model(
    field_name="hidden",
    type_=Optional[bool],
    default=None,
    suffixes=[MarketplaceVersions.MarketplaceV2.value],
)

Argument = create_model(
    model_name="Argument",
    base_models=(
        _Argument,
        NAME_DYNAMIC_MODEL,
        REQUIRED_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        DEFAULT_DYNAMIC_MODEL,
        HIDDEN_MARKETPLACE_V2_DYNAMIC_MODEL,
    ),
)


class BaseOptionalVersionYaml(BaseStrictModel):
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")


class BaseOptionalVersionJson(BaseStrictModel):
    from_version: Optional[str] = Field(None, alias="fromVersion")
    to_version: Optional[str] = Field(None, alias="toVersion")


class Output(BaseStrictModel):
    content_path: Optional[str] = Field(None, alias="contentPath")
    context_path: Optional[str] = Field(None, alias="contextPath")
    description: str
    type: Optional[str] = None


class _Important(BaseModel):
    context_path: str = Field(..., alias="contextPath")
    description: str
    related: Optional[str] = None


Important = create_model(
    model_name="Important", base_models=(_Important, DESCRIPTION_DYNAMIC_MODEL)
)


class ScriptType(StrEnum):
    PWSH = TYPE_PWSH
    PYTHON = TYPE_PYTHON
    JS = TYPE_JS


class StructureError(BaseStrictModel):
    """Used for wrapping Pydantic errors, not part of content."""

    path: Path
    field_name: Tuple[str, ...] = Field(alias="loc")
    error_message: str = Field(alias="msg")
    error_type: str = Field(alias="type")
    ctx: Optional[dict] = None

    def __str__(self):
        field_name = ",".join(more_itertools.always_iterable(self.field_name))
        if self.error_type == "assertion_error":
            error_message = (
                self.error_message
                or f"An assertion error occurred for field {field_name}"
            )
        elif self.error_type == "value_error.extra":
            error_message = f"The field {field_name} is extra and {self.error_message}"
        elif self.error_type == "value_error.missing":
            error_message = f"The field {field_name} is required but missing"
        else:
            error_message = self.error_message or ""
        return f"Structure error ({self.error_type}) in field {field_name} of {self.path.name}: {error_message}"


class _BaseIntegrationScript(BaseStrictModel):
    name: str
    deprecated: Optional[bool] = None
    system: Optional[bool] = None
    tests: Optional[List[str]] = None
    auto_update_docker_image: Optional[bool] = Field(
        None, alias="autoUpdateDockerImage"
    )
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


BaseIntegrationScript = create_model(
    model_name="BaseIntegrationScript",
    base_models=(
        _BaseIntegrationScript,
        NAME_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        BaseOptionalVersionYaml,
    ),
)

REPUTATION = Literal[tuple(range(4))]  # type:ignore[misc]


class ExtractSettings(BaseStrictModel):
    field_cli_name_to_extract_settings: Optional[Any] = Field(
        None, alias="fieldCliNameToExtractSettings"
    )
    mode: Optional[str] = None


class _StrictGenericIncidentType(BaseStrictModel):
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
    reputation_calc: Optional[REPUTATION] = Field(None, alias="reputationCalc")  # type:ignore[valid-type]
    on_change_rep_alg: Optional[REPUTATION] = Field(None, alias="onChangeRepAlg")  # type:ignore[valid-type]
    detached: Optional[bool] = None
    layout: Optional[str] = None
    extract_settings: Optional[ExtractSettings] = Field(None, alias="extractSettings")
    id_: str = Field(..., alias="id")
    version: int


StrictGenericIncidentType = create_model(
    model_name="StrictGenericIncidentType",
    base_models=(
        _StrictGenericIncidentType,
        NAME_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
        BaseOptionalVersionJson,
    ),
)

OPERATORS = Union["Filter", "Or", "And"]


class Filter(BaseStrictModel):
    SEARCH_FIELD: str
    SEARCH_TYPE: str
    SEARCH_VALUE: str


class And(BaseStrictModel):
    AND: Optional[List[OPERATORS]] = None


class Or(BaseStrictModel):
    OR: Optional[List[OPERATORS]] = None


# Forward references to resolve circular dependencies
Filter.update_forward_refs()
And.update_forward_refs()
Or.update_forward_refs()


class AlertsFilter(BaseStrictModel):
    filter: Optional[Union[Or, And]] = None
