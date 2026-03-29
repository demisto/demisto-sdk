from typing import Any, List, Optional, Union

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    REQUIRED_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictIndicatorField(BaseStrictModel):
    modified: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of when this field was last modified. Set automatically by the platform.",
    )
    name: str = Field(
        ...,
        description="Display name of the indicator field shown in the UI. Must be unique within the platform.",
    )
    owner_only: Optional[bool] = Field(
        None,
        alias="ownerOnly",
        description="When True, only the owner of the indicator can edit this field.",
    )
    place_holder: Optional[str] = Field(
        None,
        alias="placeholder",
        description="Placeholder text shown in the field input when it is empty.",
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description of what this field represents and how it should be used.",
    )
    field_calc_script: Optional[str] = Field(
        None,
        alias="fieldCalcScript",
        description="Name of the script used to automatically calculate this field's value. The script runs when the indicator is created or updated.",
    )
    cli_name: str = Field(
        ...,
        alias="cliName",
        description="CLI-friendly name of the field (lowercase, no spaces). Used in API calls and scripts to reference this field.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="Data type of the field. Must be a valid XSOAR field type (e.g. 'shortText', 'longText', 'number', 'boolean', 'date', 'singleSelect', 'multiSelect', 'url', 'markdown').",
    )
    close_form: Optional[bool] = Field(
        None,
        alias="closeForm",
        description="When True, this field appears in the close incident form.",
    )
    edit_form: Optional[bool] = Field(
        None,
        alias="editForm",
        description="When True, this field appears in the edit incident form.",
    )
    required: Optional[bool] = Field(
        None,
        description="When True, this field must be filled in before the indicator can be saved.",
    )
    script: Optional[str] = Field(
        None,
        description="Name of the script to run when this field's value changes. Used for field-level automation.",
    )
    never_set_as_required: Optional[bool] = Field(
        None,
        alias="neverSetAsRequired",
        description="When True, this field can never be marked as required, even by incident type configuration.",
    )
    is_read_only: Optional[bool] = Field(
        None,
        alias="isReadOnly",
        description="When True, this field is read-only and cannot be edited by users.",
    )
    select_values: Optional[Any] = Field(
        None,
        alias="selectValues",
        description="List of allowed values for singleSelect or multiSelect field types. Users can only choose from these values.",
    )
    validation_regex: Optional[str] = Field(
        None,
        alias="validationRegex",
        description="Regular expression pattern that the field value must match. Used for input validation.",
    )
    use_as_kpi: Optional[bool] = Field(
        None,
        alias="useAsKpi",
        description="When True, this field is used as a Key Performance Indicator (KPI) in dashboards and reports.",
    )
    locked: Optional[bool] = Field(
        None,
        description="When True, this field is locked and cannot be modified by users.",
    )
    system: Optional[bool] = Field(
        None,
        description="When True, this is a system-defined field that cannot be deleted.",
    )
    group: Optional[int] = Field(
        None,
        description="Group number for organizing fields in the UI. Fields with the same group number are displayed together.",
    )
    hidden: Optional[bool] = Field(
        None,
        description="When True, this field is hidden from the UI but still accessible via API.",
    )
    columns: Optional[Any] = Field(
        None,
        description="Column definitions for grid-type fields. Defines the structure of the grid.",
    )
    default_rows: Optional[Any] = Field(
        None,
        alias="defaultRows",
        description="Default row data for grid-type fields. Pre-populates the grid when a new indicator is created.",
    )
    threshold: Optional[int] = Field(
        None,
        description="Threshold value for SLA fields. Used to trigger alerts when the SLA is breached.",
    )
    sla: Optional[int] = Field(
        None,
        description="Service Level Agreement time in minutes. Used for SLA tracking and breach detection.",
    )
    case_insensitive: Optional[bool] = Field(
        None,
        alias="caseInsensitive",
        description="When True, field value comparisons are case-insensitive.",
    )
    breach_script: Optional[str] = Field(
        None,
        alias="breachScript",
        description="Name of the script to run when the SLA is breached.",
    )
    associated_types: Optional[Any] = Field(
        None,
        alias="associatedTypes",
        description="List of incident/indicator types this field is associated with. The field appears in layouts for these types.",
    )
    system_associated_types: Optional[Any] = Field(
        None,
        alias="systemAssociatedTypes",
        description="System-defined list of types this field is associated with. Cannot be modified by users.",
    )
    associated_to_all: Optional[bool] = Field(
        None,
        alias="associatedToAll",
        description="When True, this field is associated with all incident/indicator types.",
    )
    unmapped: Optional[bool] = Field(
        None,
        description="When True, this field is not mapped to any incident type and is only accessible via API.",
    )
    content: Optional[bool] = Field(
        None,
        description="When True, this field is a content field that is included in content exports.",
    )
    unsearchable: Optional[bool] = Field(
        None,
        description="When True, this field is excluded from search indexes and cannot be searched.",
    )
    item_version: Optional[str] = Field(
        None,
        alias="itemVersion",
        description="Version of the pack that contains this field. Set automatically during pack installation.",
    )
    propagation_labels: Optional[Any] = Field(
        None,
        alias="propagationLabels",
        description="Labels used for data propagation in multi-tenant environments.",
    )
    to_server_version: Optional[str] = Field(
        None,
        alias="toServerVersion",
        description="Maximum server version this field is compatible with. Field is not loaded on newer server versions.",
    )
    open_ended: Optional[bool] = Field(
        None,
        alias="openEnded",
        description="When True, users can enter custom values in addition to the predefined selectValues.",
    )
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = (
        Field(
            None,
            description="Marketplace(s) this field is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
        )
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this field. Restricts availability to specific modules.",
    )
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the field. Used internally to reference this field from layouts and scripts.",
    )
    version: int = Field(
        ...,
        description="Schema version of this field. Used for conflict detection. Typically -1 for new items.",
    )


StrictIndicatorField = create_model(
    model_name="StrictIndicatorField",
    base_models=(
        _StrictIndicatorField,
        NAME_DYNAMIC_MODEL,
        REQUIRED_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
        BaseOptionalVersionJson,
    ),
)
