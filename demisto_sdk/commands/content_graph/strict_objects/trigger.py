from typing import Optional

from pydantic import Field, root_validator

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AlertsFilter,
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictTrigger(BaseStrictModel):
    trigger_id: str = Field(
        ...,
        description="Unique identifier of the trigger. Used internally to reference this trigger.",
    )
    trigger_name: str = Field(
        ...,
        description="Display name of the trigger shown in the UI.",
    )
    playbook_id: Optional[str] = Field(
        None,
        description="ID of the playbook to run when this trigger fires. Mutually exclusive with automation_id/automation_type.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this trigger does and when it fires.",
    )
    suggestion_reason: str = Field(
        ...,
        description="Explanation of why this trigger is suggested for the associated alert type. Shown to users in the trigger recommendation UI.",
    )
    alerts_filter: Optional[AlertsFilter] = Field(
        None,
        description="Filter conditions that determine which alerts activate this trigger. When the filter matches, the playbook or automation runs.",
    )
    automation_type: Optional[str] = Field(
        None,
        description="Type of automation to run. Must be 'command' or 'playbook'. Required when automation_id is set. Mutually exclusive with playbook_id.",
    )
    automation_id: Optional[str] = Field(
        None,
        description="ID of the automation (command or playbook) to run. Required when automation_type is set. Mutually exclusive with playbook_id.",
    )
    supportedModules: Optional[list[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this trigger. Restricts availability to specific modules.",
    )
    issilent: Optional[bool] = Field(
        default=False,
        description="When True, the trigger runs silently without creating visible activity in the incident timeline. Defaults to False.",
    )
    grouping_element: Optional[str] = Field(
        None,
        description="Field used to group related alerts together when this trigger fires.",
    )
    is_auto_enabled: Optional[bool] = Field(
        None,
        description="When True, this trigger is automatically enabled when the associated pack is installed.",
    )

    @root_validator
    def validate_automation_playbook_logic(cls, values):
        automation_id = values.get("automation_id")
        automation_type = values.get("automation_type")
        playbook_id = values.get("playbook_id")

        if automation_type is not None and automation_type not in [
            "command",
            "playbook",
        ]:
            raise ValueError("automation_type must be one of: command, playbook.")

        # Check if automation fields are provided together
        if bool(automation_id) != bool(automation_type):
            raise ValueError(
                "automation_id and automation_type must be provided together."
            )

        # Check mutual exclusivity
        has_automation = automation_id and automation_type
        has_playbook = bool(playbook_id)

        if has_automation and has_playbook:
            raise ValueError("Cannot provide both automation fields and playbook_id.")

        if not has_automation and not has_playbook:
            raise ValueError("Must provide either automation fields or playbook_id.")

        return values


StrictTrigger = create_model(
    model_name="StrictTrigger",
    base_models=(
        _StrictTrigger,
        BaseOptionalVersionJson,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)
