from typing import Any, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    REQUIRED_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictGenericField(BaseStrictModel):
    id: str
    version: Optional[int] = None
    modified: Optional[str] = None
    name: str
    owner_only: Optional[bool] = Field(None, alias="ownerOnly")
    placeholder: Optional[str] = None
    description: Optional[str] = None
    field_calc_script: Optional[str] = Field(None, alias="fieldCalcScript")
    cli_name: str = Field(alias="cliName")
    type_: str = Field(alias="type")
    close_form: Optional[bool] = Field(None, alias="closeForm")
    edit_form: Optional[bool] = Field(None, alias="editForm")
    required: Optional[bool] = None
    script: Optional[str] = None
    never_set_as_required: Optional[bool] = Field(None, alias="neverSetAsRequired")
    is_read_only: Optional[bool] = Field(None, alias="isReadOnly")
    select_values: Optional[Any] = Field(None, alias="selectValues")
    validation_regex: Optional[str] = Field(None, alias="validationRegex")
    use_as_kpi: Optional[bool] = Field(None, alias="useAsKpi")
    locked: Optional[bool] = None
    system: Optional[bool] = None
    run_script_after_inc_update: Optional[bool] = Field(
        None, alias="runScriptAfterIncUpdate"
    )
    group: Optional[int] = None
    hidden: Optional[bool] = None
    columns: Optional[Any] = None
    default_rows: Optional[Any] = Field(None, alias="defaultRows")
    threshold: Optional[int] = None
    sla: Optional[int] = None
    case_insensitive: Optional[bool] = Field(None, alias="caseInsensitive")
    breach_script: Optional[str] = Field(None, alias="breachScript")
    associated_types: Optional[Any] = Field(None, alias="associatedTypes")
    system_associated_types: Optional[Any] = Field(None, alias="systemAssociatedTypes")
    associated_to_all: Optional[bool] = Field(None, alias="associatedToAll")
    unmapped: Optional[bool] = None
    content: Optional[bool] = None
    unsearchable: Optional[bool] = None
    extract_indicator_types_ids: Optional[Any] = Field(
        None, alias="extractIndicatorTypesIDs"
    )
    is_extracting_specific_indicator_types: Optional[bool] = Field(
        None, alias="isExtractingSpecificIndicatorTypes"
    )
    item_version: Optional[str] = Field(None, alias="itemVersion")
    propagation_labels: Optional[Any] = Field(None, alias="propagationLabels")
    to_server_version: Optional[str] = Field(None, alias="toServerVersion")
    definition_id: str = Field(alias="definitionId")
    generic_module_id: str = Field(alias="genericModuleId")
    template: Optional[str] = None
    open_ended: Optional[bool] = Field(None, alias="openEnded")


StrictGenericField = create_model(
    model_name="StrictGenericField",
    base_models=(
        _StrictGenericField,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        REQUIRED_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
