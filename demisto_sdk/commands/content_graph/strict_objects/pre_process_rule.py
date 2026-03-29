from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class Period(BaseStrictModel):
    by: Optional[str] = Field(
        None,
        description="Time unit for the deduplication period (e.g. 'hours', 'days', 'minutes').",
    )
    from_value: Optional[int] = Field(
        None,
        alias="fromValue",
        description="Number of time units for the deduplication period. Combined with 'by' to define the full period.",
    )


class _StrictPreProcessRule(BaseStrictModel):
    action: str = Field(
        ...,
        description="Action to take when this rule matches. Must be one of: 'link' (link to existing incident), 'drop' (discard the event), 'create' (create new incident).",
    )
    enabled: bool = Field(
        ...,
        description="When True, this pre-process rule is active and will be evaluated for incoming events.",
    )
    existing_events_filters: List[Any] = Field(
        default_factory=list,
        alias="existingEventsFilters",
        description="Filter conditions applied to existing incidents when searching for duplicates. Used with 'link' action.",
    )
    from_version: str = Field(
        ...,
        alias="fromVersion",
        description="Minimum platform version required to use this pre-process rule (e.g. '6.0.0'). Required field.",
    )
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the pre-process rule. Used internally to reference this rule.",
    )
    index: int = Field(
        ...,
        description="Execution order of this rule relative to other pre-process rules. Lower index = higher priority.",
    )
    item_version: str = Field(
        ...,
        alias="itemVersion",
        description="Version of the pack that contains this rule. Set automatically during pack installation.",
    )
    link_to: str = Field(
        ...,
        alias="linkTo",
        description="Specifies which existing incident to link to when action is 'link'. References a field or expression.",
    )
    locked: bool = Field(
        ...,
        description="When True, this pre-process rule is locked and cannot be modified by users.",
    )
    name: str = Field(
        ...,
        description="Display name of the pre-process rule shown in the UI.",
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description of what this pre-process rule does and when it applies.",
    )
    new_event_filters: List[List[Dict[str, Union[str, Dict[str, Any]]]]] = Field(
        default_factory=list,
        alias="newEventFilters",
        description="Filter conditions applied to incoming events to determine if this rule should fire. Nested list structure supports AND/OR logic.",
    )
    pack_id: str = Field(
        ...,
        alias="packID",
        description="ID of the pack that contains this pre-process rule.",
    )
    period: Optional[Period] = Field(
        None,
        description="Deduplication period configuration. Events matching within this period are considered duplicates.",
    )
    ready_existing_events_filters: List[Any] = Field(
        default_factory=list,
        alias="readyExistingEventsFilters",
        description="Pre-compiled version of existingEventsFilters for runtime evaluation. Set automatically by the platform.",
    )
    ready_new_event_filters: List[Any] = Field(
        default_factory=list,
        alias="readyNewEventFilters",
        description="Pre-compiled version of newEventFilters for runtime evaluation. Set automatically by the platform.",
    )
    script_name: str = Field(
        ...,
        alias="scriptName",
        description="Name of the script to run when this rule matches. The script can modify the event or perform additional logic.",
    )
    search_closed: bool = Field(
        ...,
        alias="searchClosed",
        description="When True, closed incidents are also searched when looking for duplicates to link to.",
    )
    system: bool = Field(
        ...,
        description="When True, this is a system-defined pre-process rule that cannot be deleted.",
    )
    to_server_version: str = Field(
        ...,
        alias="toServerVersion",
        description="Maximum server version this pre-process rule is compatible with.",
    )
    version: int = Field(
        ...,
        description="Schema version of this pre-process rule. Used for conflict detection. Typically -1 for new items.",
    )


StrictPreProcessRule = create_model(
    model_name="StrictPreProcessRule",
    base_models=(
        _StrictPreProcessRule,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
