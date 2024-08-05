from typing import Any, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionYaml,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictCorrelationRule(BaseStrictModel):
    global_rule_id: str
    name: str  # not included in NAME_DYNAMIC_MODEL
    alert_name: str
    description: str
    alert_description: str
    alert_category: str
    alert_fields: Optional[Any] = None
    cron_tab: Optional[str] = Field(None, alias="crontab")
    dataset: str
    drill_down_query_timeframe: str = Field(..., alias="drilldown_query_timeframe")
    execution_mode: str = Field(..., enum=["REAL_TIME", "SCHEDULED"])
    mitre_defs: Optional[Any] = None
    search_window: Optional[str] = None
    severity: str
    suppression_enabled: bool
    suppression_duration: Optional[str] = None
    suppression_fields: Optional[str] = None
    user_defined_category: Optional[str] = None
    user_defined_severity: Optional[str] = None
    xql_query: str
    investigation_query_link: Optional[str] = None
    mapping_strategy: Optional[str] = None


StrictCorrelationRule = create_model(
    model_name="StrictCorrelationRule",
    base_models=(
        _StrictCorrelationRule,
        BaseOptionalVersionYaml,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
    ),
)
