from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AlertsFilter,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class StrictCaseLayoutRule(BaseStrictModel):
    rule_id: str = Field(
        ...,
        description="Unique identifier of the case layout rule. Used internally to reference this rule.",
    )
    rule_name: str = Field(
        ...,
        description="Display name of the case layout rule shown in the UI.",
    )
    layout_id: str = Field(
        ...,
        description="ID of the case layout to apply when this rule matches. Must reference a valid case layout ID.",
    )
    from_version: str = Field(
        ...,
        alias="fromVersion",
        description="Minimum platform version required to use this case layout rule (e.g. '8.3.0'). Required field.",
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description of when this case layout rule applies and what it does.",
    )
    incidents_filter: Optional[AlertsFilter] = Field(
        None,
        description="Filter conditions that determine when this case layout rule is applied. When the filter matches, the associated case layout is used.",
    )
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        description="Marketplace(s) this case layout rule is available in. Restricted to: marketplacev2, platform.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this case layout rule. Restricts availability to specific modules.",
    )
