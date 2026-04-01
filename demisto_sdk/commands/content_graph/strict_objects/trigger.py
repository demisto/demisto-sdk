from typing import Optional

from pydantic import Field, model_validator

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
    trigger_id: str
    trigger_name: str
    playbook_id: Optional[str] = None
    description: str
    suggestion_reason: str
    alerts_filter: Optional[AlertsFilter] = None
    automation_type: Optional[str] = None
    automation_id: Optional[str] = None
    supportedModules: Optional[list[str]] = Field(None, alias="supportedModules")
    issilent: Optional[bool] = Field(default=False)
    grouping_element: Optional[str] = None
    is_auto_enabled: Optional[bool] = None

    @model_validator(mode="after")
    def validate_automation_playbook_logic(self):
        automation_id = self.automation_id
        automation_type = self.automation_type
        playbook_id = self.playbook_id

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

        return self


StrictTrigger = create_model(
    model_name="StrictTrigger",
    base_models=(
        _StrictTrigger,
        BaseOptionalVersionJson,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)
