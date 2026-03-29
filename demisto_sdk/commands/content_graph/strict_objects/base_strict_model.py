from pathlib import Path
from typing import Annotated, Any, List, Literal, Optional, Tuple, Union

import more_itertools
from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import (
    TYPE_JS,
    TYPE_PWSH,
    TYPE_PYTHON,
    Auto,
    MarketplaceVersions,
    PlatformSupportedModules,
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
    version: int = Field(
        ...,
        description="Schema version of this content item. Used for conflict detection and migration. Typically -1 for new items.",
    )


CommonFields = create_model(
    model_name="CommonFields",
    base_models=(
        _CommonFields,
        ID_DYNAMIC_MODEL,
    ),
)


class _Argument(BaseStrictModel):
    name: str = Field(
        ...,
        description="Unique name of the argument as it appears in the integration/script YAML. Used in API calls and playbooks.",
    )
    prettyname: Optional[str] = Field(
        None,
        description="Human-readable display name of the argument shown in the UI. If not set, the name field is used.",
    )
    pretty_predefined: Optional[dict] = Field(
        None,
        alias="prettypredefined",
        description="Human-readable labels for predefined argument values. Maps raw values to display labels.",
    )
    required: Optional[bool] = Field(
        None,
        description="When True, this argument must be provided when calling the command. Omitting it causes an error.",
    )
    default: Optional[bool] = Field(
        None,
        description="When True, this argument receives the default input value from the playbook task.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this argument does and what values are expected.",
    )
    auto: Optional[Auto] = Field(
        None,
        description="When set to 'PREDEFINED', the argument value must be one of the predefined values. Enables dropdown selection in the UI.",
    )
    predefined: Optional[List[str]] = Field(
        None,
        description="List of allowed values for this argument when auto='PREDEFINED'. Users can only select from these values.",
    )
    is_array: Optional[bool] = Field(
        None,
        alias="isArray",
        description="When True, this argument accepts a list of values instead of a single value.",
    )
    secret: Optional[bool] = Field(
        None,
        description="When True, the argument value is treated as sensitive and masked in logs and the UI.",
    )
    deprecated: Optional[bool] = Field(
        None,
        description="When True, this argument is deprecated and should not be used in new playbooks.",
    )
    type: Optional[str] = Field(
        None,
        description="Data type of the argument (e.g. 'String', 'Number', 'Boolean', 'Date'). Used for input validation.",
    )
    hidden: Optional[bool] = Field(
        None,
        description="When True, this argument is hidden from the UI but can still be set programmatically.",
    )
    supportedModules: Optional[
        Annotated[List[PlatformSupportedModules], Field(min_length=1, max_length=7)]
    ] = Field(
        None,
        description="Optional list of platform modules that support this argument. Restricts availability to specific modules.",
    )


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
    from_version: Optional[str] = Field(
        None,
        alias="fromversion",
        description="Minimum platform version required to use this content item (e.g. '6.0.0'). Items are not loaded on older platforms.",
    )
    to_version: Optional[str] = Field(
        None,
        alias="toversion",
        description="Maximum platform version this content item is compatible with (e.g. '99.99.99'). Items are not loaded on newer platforms.",
    )


class BaseOptionalVersionJson(BaseStrictModel):
    from_version: Optional[str] = Field(
        None,
        alias="fromVersion",
        description="Minimum platform version required to use this content item (e.g. '6.0.0'). Items are not loaded on older platforms.",
    )
    to_version: Optional[str] = Field(
        None,
        alias="toVersion",
        description="Maximum platform version this content item is compatible with (e.g. '99.99.99'). Items are not loaded on newer platforms.",
    )


class Output(BaseStrictModel):
    content_path: Optional[str] = Field(
        None,
        alias="contentPath",
        description="Path to the content item that produces this output. Used for cross-content-item output references.",
    )
    context_path: Optional[str] = Field(
        None,
        alias="contextPath",
        description="Dot-notation path where this output is stored in the XSOAR context (e.g. 'IP.Address', 'File.MD5'). Used by playbooks to access the output.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this output contains and how to use it.",
    )
    type: Optional[str] = Field(
        None,
        description="Data type of the output (e.g. 'String', 'Number', 'Boolean', 'Date', 'Unknown'). Used for type checking in playbooks.",
    )


class _Important(BaseModel):
    context_path: str = Field(
        ...,
        alias="contextPath",
        description="Context path of the important output to highlight (e.g. 'IP.Address').",
    )
    description: str = Field(
        ...,
        description="Human-readable description of why this output is important.",
    )
    related: Optional[str] = Field(
        None,
        description="Related context path or field name.",
    )


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
    name: str = Field(
        ...,
        description="Unique name of the integration or script. Used as the identifier in playbooks and API calls.",
    )
    deprecated: Optional[bool] = Field(
        None,
        description="When True, this integration/script is deprecated and should not be used in new playbooks.",
    )
    system: Optional[bool] = Field(
        None,
        description="When True, this is a system-provided integration/script that cannot be deleted.",
    )
    tests: Optional[List[str]] = Field(
        None,
        description="List of test playbook names used to test this integration/script. Referenced during CI/CD validation.",
    )
    auto_update_docker_image: Optional[bool] = Field(
        None,
        alias="autoUpdateDockerImage",
        description="When True, the Docker image is automatically updated to the latest version during pack release.",
    )
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = (
        Field(
            None,
            description="Marketplace(s) this integration/script is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
        )
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this integration/script. Restricts availability to specific modules.",
    )


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


class AgentixBase(BaseStrictModel):
    common_fields: CommonFields = Field(  # type:ignore[valid-type]
        ...,
        alias="commonfields",
        description="Common metadata fields shared by all content items, including the unique ID and schema version.",
    )
    tags: Optional[list[str]] = Field(
        None,
        description="Optional list of tags used to categorise and filter this content item in the marketplace.",
    )
    category: Optional[str] = Field(
        None,
        description="Category this content item belongs to (e.g. 'Data Enrichment & Threat Intelligence'). Used for marketplace filtering.",
    )
    name: str = Field(
        ...,
        description="Unique machine-readable name of this content item. Must be unique within the pack.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this content item does. Shown in the UI and used by the AI agent to decide when to invoke it.",
    )
    disabled: bool = Field(
        False,
        description="When True, this content item is disabled and will not be available for use. Defaults to False.",
    )
    internal: Optional[bool] = Field(
        None,
        description="When True, marks this content item as internal and not intended for direct use by end users.",
    )
    from_version: Optional[str] = Field(
        None,
        alias="fromversion",
        description="Minimum platform version required to use this content item (e.g. '8.0.0'). Items are not loaded on older platforms.",
    )
    to_version: Optional[str] = Field(
        None,
        alias="toversion",
        description="Maximum platform version this content item is compatible with (e.g. '99.99.99'). Items are not loaded on newer platforms.",
    )
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = (
        Field(
            None,
            description="Marketplace(s) this content item is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
        )
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        description="Optional list of platform modules that support this content item. Restricts availability to specific modules.",
    )
