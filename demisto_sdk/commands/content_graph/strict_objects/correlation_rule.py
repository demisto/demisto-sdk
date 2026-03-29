from typing import Any, List, Optional

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
    global_rule_id: str = Field(
        ...,
        description="Globally unique identifier for this correlation rule. Used to reference the rule across the platform.",
    )
    name: str = Field(
        ...,
        description="Display name of the correlation rule shown in the UI. Must be unique within the platform.",
    )
    alert_name: str = Field(
        ...,
        description="Name of the alert generated when this rule fires. Shown as the alert title in the UI.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this correlation rule detects and why it is important.",
    )
    alert_description: str = Field(
        ...,
        description="Description included in the generated alert. Provides context about the detected threat or anomaly.",
    )
    alert_category: str = Field(
        ...,
        description="Category of the generated alert (e.g. 'Malware', 'Lateral Movement', 'Exfiltration'). Used for filtering and reporting.",
    )
    alert_fields: Optional[Any] = Field(
        None,
        description="Additional fields to include in the generated alert. Mapped from the XQL query results.",
    )
    cron_tab: Optional[str] = Field(
        None,
        alias="crontab",
        description="Cron expression defining the schedule for SCHEDULED execution mode (e.g. '0 * * * *' for hourly). Not used in REAL_TIME mode.",
    )
    dataset: str = Field(
        ...,
        description="XDR dataset to query (e.g. 'xdr_data', 'cloud_audit'). Must be a valid dataset name available in the platform.",
    )
    drill_down_query_timeframe: str = Field(
        ...,
        alias="drilldown_query_timeframe",
        description="Time frame for the drill-down investigation query (e.g. '1h', '24h', '7d'). Used when investigating triggered alerts.",
    )
    execution_mode: str = Field(
        ...,
        enum=["REAL_TIME", "SCHEDULED"],
        description="Execution mode of the rule. REAL_TIME: rule evaluates events as they arrive. SCHEDULED: rule runs on a cron schedule.",
    )
    mitre_defs: Optional[Any] = Field(
        None,
        description="MITRE ATT&CK technique and tactic definitions associated with this rule (e.g. T1059, TA0002).",
    )
    search_window: Optional[str] = Field(
        None,
        description="Time window for the XQL query in SCHEDULED mode (e.g. '1h', '24h'). Defines how far back to look for matching events.",
    )
    severity: str = Field(
        ...,
        description="Severity of the generated alert. Must be one of: 'informational', 'low', 'medium', 'high', 'critical'.",
    )
    suppression_enabled: bool = Field(
        ...,
        description="When True, alert suppression is enabled. Prevents duplicate alerts from firing within the suppression window.",
    )
    suppression_duration: Optional[str] = Field(
        None,
        description="Duration of the suppression window (e.g. '1h', '24h'). Alerts are suppressed for this period after the first occurrence.",
    )
    suppression_fields: Optional[str] = Field(
        None,
        description="Comma-separated list of fields used to identify duplicate alerts for suppression purposes.",
    )
    user_defined_category: Optional[str] = Field(
        None,
        description="Custom category defined by the user. Overrides the default alert_category for organizational purposes.",
    )
    user_defined_severity: Optional[str] = Field(
        None,
        description="Custom severity defined by the user. Overrides the default severity for organizational purposes.",
    )
    xql_query: str = Field(
        ...,
        description="XQL (XDR Query Language) query that defines the detection logic. Must be a valid XQL query against the specified dataset.",
    )
    investigation_query_link: Optional[str] = Field(
        None,
        description="URL or XQL query link for investigating triggered alerts. Provides a starting point for threat hunting.",
    )
    mapping_strategy: Optional[str] = Field(
        None,
        description="Strategy for mapping XQL query results to alert fields. Defines how query output is transformed into alert data.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this correlation rule. Restricts availability to specific modules.",
    )


StrictCorrelationRule = create_model(
    model_name="StrictCorrelationRule",
    base_models=(
        _StrictCorrelationRule,
        BaseOptionalVersionYaml,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
    ),
)
