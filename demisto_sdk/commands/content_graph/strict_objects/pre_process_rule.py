from typing import Any, Dict, List, Optional, Union

from pydantic import Field, root_validator

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SCRIPT_ID_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class Period(BaseStrictModel):
    by: Optional[str] = None
    from_value: Optional[int] = Field(None, alias="fromValue")


class _StrictPreProcessRule(BaseStrictModel):
    @root_validator(pre=True)
    def handle_legacy_script_id(cls, values):
        """
        Handle legacy 'scriptID' field (with capital D) by mapping it to 'scriptId'.
        This ensures backward compatibility with older PreProcessRule files.
        """
        if "scriptID" in values and "scriptId" not in values:
            values["scriptId"] = values.pop("scriptID")
        return values

    action: str
    enabled: bool
    existing_events_filters: List[Any] = Field(
        default_factory=list, alias="existingEventsFilters"
    )
    from_version: str = Field(alias="fromVersion")
    id_: str = Field(alias="id")
    index: int
    item_version: str = Field(alias="itemVersion")
    link_to: str = Field(alias="linkTo")
    locked: bool
    name: str
    description: Optional[str] = None
    new_event_filters: List[List[Dict[str, Union[str, Dict[str, Any]]]]] = Field(
        default_factory=list, alias="newEventFilters"
    )
    pack_id: str = Field(alias="packID")
    period: Optional[Period] = None
    ready_existing_events_filters: List[Any] = Field(
        default_factory=list, alias="readyExistingEventsFilters"
    )
    ready_new_event_filters: List[Any] = Field(
        default_factory=list, alias="readyNewEventFilters"
    )
    script_name: str = Field(alias="scriptName")
    search_closed: bool = Field(alias="searchClosed")
    system: bool
    to_server_version: str = Field(alias="toServerVersion")
    version: int


StrictPreProcessRule = create_model(
    model_name="StrictPreProcessRule",
    base_models=(
        _StrictPreProcessRule,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        SCRIPT_ID_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
