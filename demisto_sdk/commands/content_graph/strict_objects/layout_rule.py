from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AlertsFilter,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictLayoutRule(BaseStrictModel):
    rule_id: str = Field(
        ...,
        description="Unique identifier of the layout rule. Used internally to reference this rule.",
    )
    rule_name: str = Field(
        ...,
        description="Display name of the layout rule shown in the UI.",
    )
    layout_id: str = Field(
        ...,
        description="ID of the layout (layout-container) to apply when this rule matches. Must reference a valid layout ID.",
    )
    from_version: str = Field(
        ...,
        alias="fromVersion",
        description="Minimum platform version required to use this layout rule (e.g. '6.5.0'). Required field.",
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description of when this layout rule applies and what it does.",
    )
    alerts_filter: Optional[AlertsFilter] = Field(
        None,
        description="Filter conditions that determine when this layout rule is applied. When the filter matches, the associated layout is used.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this layout rule. Restricts availability to specific modules.",
    )
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        description="Marketplace(s) this layout rule is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
    )


StrictLayoutRule = create_model(
    model_name="StrictLayoutRule",
    base_models=(_StrictLayoutRule, DESCRIPTION_DYNAMIC_MODEL),
)
