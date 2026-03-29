from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictIndicatorType(BaseStrictModel):
    modified: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of when this indicator type was last modified. Set automatically by the platform.",
    )
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the indicator type. Used internally to reference this type from scripts and integrations.",
    )
    version: int = Field(
        ...,
        description="Schema version of this indicator type. Used for conflict detection. Typically -1 for new items.",
    )
    sort_values: Optional[Any] = Field(
        None,
        alias="sortValues",
        description="Internal field used for sorting indicator types in the UI. Not typically set manually.",
    )
    commit_message: Optional[str] = Field(
        None,
        alias="commitMessage",
        description="Commit message describing the changes made to this indicator type. Used for version control tracking.",
    )
    should_publish: Optional[bool] = Field(
        None,
        alias="shouldPublish",
        description="When True, this indicator type should be published to the marketplace.",
    )
    should_commit: Optional[bool] = Field(
        None,
        alias="shouldCommit",
        description="When True, changes to this indicator type should be committed to version control.",
    )
    regex: str = Field(
        ...,
        description="Regular expression pattern used to automatically detect and extract this indicator type from text. Must be a valid Python regex.",
    )
    details: str = Field(
        ...,
        description="Display name of the indicator type shown in the UI (e.g. 'IP Address', 'Domain', 'URL').",
    )
    prev_details: Optional[str] = Field(
        None,
        alias="prevDetails",
        description="Previous display name of this indicator type. Used for migration when the name changes.",
    )
    reputation_script_name: Optional[str] = Field(
        None,
        alias="reputationScriptName",
        description="Name of the script used to calculate the reputation of indicators of this type.",
    )
    reputation_command: Optional[str] = Field(
        None,
        alias="reputationCommand",
        description="Integration command used to enrich indicators of this type (e.g. 'ip', 'domain', 'url').",
    )
    enhancement_script_names: Optional[Any] = Field(
        None,
        alias="enhancementScriptNames",
        description="List of script names used to enhance (enrich) indicators of this type with additional context.",
    )
    system: Optional[bool] = Field(
        None,
        description="When True, this is a system-defined indicator type that cannot be deleted.",
    )
    locked: Optional[bool] = Field(
        None,
        description="When True, this indicator type is locked and cannot be modified by users.",
    )
    disabled: Optional[bool] = Field(
        None,
        description="When True, this indicator type is disabled and will not be used for automatic extraction.",
    )
    file: Optional[bool] = Field(
        None,
        description="When True, this indicator type represents a file indicator (e.g. file hash).",
    )
    update_after: Optional[int] = Field(
        None,
        alias="updateAfter",
        description="Number of hours after which the indicator should be re-enriched. Used for automatic refresh.",
    )
    merge_context: Optional[bool] = Field(
        None,
        alias="mergeContext",
        description="When True, context data from multiple enrichment sources is merged rather than overwritten.",
    )
    format_script: Optional[str] = Field(
        None,
        alias="formatScript",
        description="Name of the script used to format/normalize the indicator value before storage.",
    )
    context_path: Optional[str] = Field(
        None,
        alias="contextPath",
        description="Context path where enrichment data for this indicator type is stored (e.g. 'IP', 'Domain').",
    )
    context_value: Optional[str] = Field(
        None,
        alias="contextValue",
        description="Context field name that contains the indicator value within the context path.",
    )
    excluded_brands: Optional[Any] = Field(
        None,
        alias="excludedBrands",
        description="List of integration brand names excluded from enriching this indicator type.",
    )
    default_mapping: Optional[Any] = Field(
        None,
        alias="defaultMapping",
        description="Default field mapping applied when creating indicators of this type.",
    )
    manual_mapping: Optional[Any] = Field(
        None,
        alias="manualMapping",
        description="Manual field mapping overrides for this indicator type.",
    )
    file_hashes_priority: Optional[Any] = Field(
        None,
        alias="fileHashesPriority",
        description="Priority order for file hash types (e.g. SHA256 > SHA1 > MD5). Used when multiple hash types are available.",
    )
    expiration: Optional[int] = Field(
        None,
        description="Number of days after which indicators of this type expire and are removed from the system.",
    )
    layout: Optional[str] = Field(
        None,
        description="Name of the layout used to display indicators of this type in the UI.",
    )
    legacy_names: Optional[List[str]] = Field(
        None,
        alias="legacyNames",
        description="List of previous names for this indicator type. Used for backward compatibility when the type is renamed.",
    )
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        description="Marketplace(s) this indicator type is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this indicator type. Restricts availability to specific modules.",
    )


StrictIndicatorType = create_model(
    model_name="StrictIndicatorType",
    base_models=(
        _StrictIndicatorType,
        BaseOptionalVersionJson,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
