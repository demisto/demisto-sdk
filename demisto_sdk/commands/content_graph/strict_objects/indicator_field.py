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
    modified: Optional[str] = None
    name: str
    owner_only: Optional[bool] = Field(None, alias="ownerOnly")
    place_holder: Optional[str] = Field(None, alias="placeholder")
    description: Optional[str] = None
    field_calc_script: Optional[str] = Field(None, alias="fieldCalcScript")
    cli_name: str = Field(..., alias="cliName")
    type_: str = Field(..., alias="type")
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
    item_version: Optional[str] = Field(None, alias="itemVersion")
    propagation_labels: Optional[Any] = Field(None, alias="propagationLabels")
    to_server_version: Optional[str] = Field(None, alias="toServerVersion")
    open_ended: Optional[bool] = Field(None, alias="openEnded")
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    id_: str = Field(..., alias="id")
    version: int


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
