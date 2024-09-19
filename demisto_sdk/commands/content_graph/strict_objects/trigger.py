from typing import Optional

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
    playbook_id: str
    description: str
    suggestion_reason: str
    alerts_filter: Optional[AlertsFilter] = None


StrictTrigger = create_model(
    model_name="StrictTrigger",
    base_models=(
        _StrictTrigger,
        BaseOptionalVersionJson,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)
