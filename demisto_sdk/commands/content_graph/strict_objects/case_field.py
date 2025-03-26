from typing import Any, List, Literal, Optional, Union

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    IncidentFieldType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
    create_model,
)


class AliasesTypes(StrEnum):
    TAGS_SELECT = "tagsSelect"
    INTERNAL = "internal"


class StrictAliases(BaseStrictModel):
    cli_name: str = Field(alias="cliName")
    name: str
    type: Union[IncidentFieldType, AliasesTypes]


class _StrictCaseField(BaseStrictModel):
    id_: str = Field(alias="id")
    version: Optional[int] = None
    modified: Optional[str] = None
    name: str
    pretty_name: Optional[str] = Field(None, alias="prettyName")
    owner_only: Optional[bool] = Field(None, alias="ownerOnly")
    description: Optional[str] = None
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
    item_version: Optional[str] = Field(None, alias="itemVersion")
    propagation_labels: Optional[Any] = Field(None, alias="propagationLabels")
    to_server_version: Optional[str] = Field(None, alias="toServerVersion")
    open_ended: Optional[bool] = Field(None, alias="openEnded")
    template: Optional[str] = None
    marketplaces: Literal[
        MarketplaceVersions.MarketplaceV2, MarketplaceVersions.PLATFORM
    ] = Field(default_factory=list)
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    aliases: Optional[List[StrictAliases]] = Field(None, alias="Aliases")
    alias_to: Optional[str] = Field(None, alias="aliasTo")


StrictCaseField = create_model(
    model_name="StrictCaseField",
    base_models=(
        _StrictCaseField,
        BaseOptionalVersionJson,
    ),
)
