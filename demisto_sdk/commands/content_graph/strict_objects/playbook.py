from typing import Any, Dict, List, Optional

from pydantic import Field, constr

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    FORM_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    KEY_DYNAMIC_MODEL,
    LEFT_DYNAMIC_MODEL,
    MESSAGE_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    PLAYBOOK_INPUT_QUERY_DYNAMIC_MODEL,
    REQUIRED_DYNAMIC_MODEL,
    RIGHT_DYNAMIC_MODEL,
    SCRIPT_ARGUMENTS_LOWER_CASE_DYNAMIC_MODEL,
    SCRIPT_ARGUMENTS_UPPER_CASE_DYNAMIC_MODEL,
    SCRIPT_ID_DYNAMIC_MODEL,
    VALUE_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)

TASKS_REGEX = r"^[0-9]+(:?(" + "|".join(MarketplaceVersions) + "))?$"


class ContentItemFields(BaseStrictModel):
    propagation_labels: Optional[Any] = Field(None, alias="propagationLabels")


class ContentItemExportableFields(BaseStrictModel):
    content_item_fields: Optional[ContentItemFields] = Field(
        None, alias="contentitemfields"
    )


class ElasticCommonFields(BaseStrictModel):
    type: Optional[Dict[Any, Any]]  # Allow empty


class _PlaybookOutput(BaseStrictModel):
    context_path: str = Field(alias="contextPath")
    type: Optional[str] = None
    description: str


PlaybookOutput = create_model(
    model_name="PlaybookOutput",
    base_models=(
        _PlaybookOutput,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)


class _OutputsSectionPlaybook(BaseStrictModel):
    name: str
    description: str
    outputs: List[str]


OutputsSectionPlaybook = create_model(
    model_name="OutputsSectionPlaybook",
    base_models=(
        _OutputsSectionPlaybook,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)


class _PlaybookInput(BaseStrictModel):
    key: str
    value: Any
    description: str
    required: Optional[bool] = None
    playbook_input_query: Any = Field(None, alias="playbookInputQuery")


InputPlaybook = create_model(
    model_name="InputPlaybook",
    base_models=(
        _PlaybookInput,
        KEY_DYNAMIC_MODEL,
        VALUE_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        REQUIRED_DYNAMIC_MODEL,
        PLAYBOOK_INPUT_QUERY_DYNAMIC_MODEL,
    ),
)


class _PlaybookInputsSection(BaseStrictModel):
    name: str
    description: str
    inputs: List[str]


InputsSectionPlaybook = create_model(
    model_name="InputsSectionPlaybook",
    base_models=(
        _PlaybookInputsSection,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)


class TimerTriggers(BaseStrictModel):
    field_name: Optional[str] = Field(None, alias="fieldname")
    action: Optional[str] = None


class _ArgFilter(BaseStrictModel):
    operator: str
    ignore_case: Optional[bool] = Field(None, alias="ignorecase")


ArgFilter = create_model(
    model_name="ArgFilter",
    base_models=(_ArgFilter, RIGHT_DYNAMIC_MODEL, LEFT_DYNAMIC_MODEL),
)


class ArgFilters(BaseStrictModel):
    __root__: List[ArgFilter]  # type:ignore[valid-type]


class Condition(BaseStrictModel):
    label: str
    condition: List[ArgFilters]


class EvidenceDataDescription(BaseStrictModel):
    simple: Optional[str] = None


class EvidenceData(BaseStrictModel):
    description: Optional[EvidenceDataDescription] = None
    custom_fields: Optional[Dict[str, Any]] = Field(None, alias="customfields")
    occurred: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None


class _SubTaskPlaybook(BaseStrictModel):
    id: str
    version: int
    name: str
    playbookName: Optional[str] = None
    playbookId: Optional[str] = None
    description: str
    scriptName: Optional[str] = None
    script: Optional[str] = None
    tags: Optional[List[str]] = None
    type: Optional[str] = None
    iscommand: bool
    elastic_common_fields: Optional[ElasticCommonFields] = Field(
        None, alias="elasticcommonfields"
    )
    brand: str
    is_system_task: Optional[bool] = Field(None, alias="issystemtask")
    cloned_from: Optional[str] = Field(None, alias="clonedfrom")


SubTaskPlaybook = create_model(
    model_name="SubTaskPlaybook",
    base_models=(
        _SubTaskPlaybook,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
    ),
)


class _Loop(BaseStrictModel):
    iscommand: Optional[bool]
    built_in_condition: Optional[List[ArgFilters]] = Field(
        None, alias="builtincondition"
    )
    exit_condition: Optional[str] = Field(None, alias="exitCondition")
    max: Optional[int] = None
    wait: Optional[int] = None
    for_each: Optional[bool] = Field(None, alias="forEach")


Loop = create_model(
    model_name="Loop",
    base_models=(
        _Loop,
        SCRIPT_ID_DYNAMIC_MODEL,
        SCRIPT_ARGUMENTS_LOWER_CASE_DYNAMIC_MODEL,
        SCRIPT_ARGUMENTS_UPPER_CASE_DYNAMIC_MODEL,
    ),
)


class _TaskPlaybook(BaseStrictModel):
    id: str
    task_id: str = Field(alias="taskid")
    type: str = Field(
        ...,
        enum=[
            "regular",
            "playbook",
            "condition",
            "start",
            "title",
            "section",
            "standard",
            "collection",
        ],
    )
    default_assignee_complex: Optional[Dict] = Field(
        None, alias="defaultassigneecomplex"
    )
    sla: Optional[Dict]
    sla_reminder: Optional[Dict] = Field(None, alias="slareminder")
    quiet_mode: Optional[int] = Field(None, alias="quietmode")
    restricted_completion: Optional[bool] = Field(None, alias="restrictedcompletion")
    timer_triggers: Optional[List[TimerTriggers]] = Field(None, alias="timertriggers")
    ignore_worker: Optional[bool] = Field(None, alias="ignoreworker")
    skip_unavailable: Optional[bool] = Field(None, alias="skipunavailable")
    is_oversize: Optional[bool] = Field(None, alias="isoversize")
    is_auto_switched_to_quiet_mode: Optional[bool] = Field(
        None, alias="isautoswitchedtoquietmode"
    )
    quiet: Optional[bool] = None
    evidence_data: Optional[EvidenceData] = Field(None, alias="evidencedata")
    task: SubTaskPlaybook  # type:ignore[valid-type]
    note: Optional[bool] = None
    next_tasks: Optional[Dict[constr(regex=r".+"), List[str]]] = Field(  # type:ignore[valid-type]
        None, alias="nexttasks"
    )
    loop: Optional[Loop]  # type:ignore[valid-type]
    conditions: Optional[List[Condition]]
    view: str
    results: Optional[List[str]]
    continue_on_error: Optional[bool] = Field(None, alias="continueonerror")
    continue_on_error_type: Optional[str] = Field(None, alias="continueonerrortype")
    reputation_calc: Optional[int] = Field(None, alias="reputationcalc")
    separate_context: Optional[bool] = Field(None, alias="separatecontext")
    field_mapping: Optional[List[Dict]] = Field(None, alias="fieldMapping")


TaskPlaybook = create_model(
    model_name="TaskPlaybook",
    base_models=(
        _TaskPlaybook,
        FORM_DYNAMIC_MODEL,
        MESSAGE_DYNAMIC_MODEL,
        SCRIPT_ARGUMENTS_LOWER_CASE_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
    ),
)


class StrictPlaybook(BaseStrictModel):
    content_item_exportable_fields: Optional[ContentItemExportableFields] = Field(
        None, alias="contentitemexportablefields"
    )
    beta: Optional[bool] = None
    elastic_common_fields: Optional[ElasticCommonFields] = Field(
        None, alias="elasticcommonfields"
    )
    id_: str = Field(alias="id")
    version: int
    source_playbook_id: Optional[str] = Field(None, alias="sourceplaybookid")
    name: str
    description: str
    hidden: Optional[bool] = None
    deprecated: Optional[bool] = None
    start_task_id: str = Field(alias="starttaskid")
    view: str
    content_item_fields: Optional[ContentItemFields] = Field(
        None, alias="contentitemfields"
    )
    outputs: Optional[List[PlaybookOutput]] = None  # type:ignore[valid-type]
    output_sections: Optional[List[OutputsSectionPlaybook]] = Field(  # type:ignore[valid-type]
        None, alias="outputSections"
    )
    inputs: Optional[List[InputPlaybook]] = None  # type:ignore[valid-type]
    inputSections: Optional[List[InputsSectionPlaybook]] = None  # type:ignore[valid-type]
    tags: Optional[List[str]] = None
    tasks: Dict[constr(regex=TASKS_REGEX), TaskPlaybook]  # type:ignore[valid-type]
    system: Optional[bool] = None
    from_version: str = Field(alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    quiet: Optional[bool] = None
    tests: Optional[List[str]] = None
    role_name: Optional[List[str]] = Field(None, alias="rolename")
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    is_silent: Optional[bool] = Field(alias="issilent")
