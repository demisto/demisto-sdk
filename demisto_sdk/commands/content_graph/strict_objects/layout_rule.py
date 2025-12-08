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
    rule_id: str
    rule_name: str
    layout_id: str
    from_version: str = Field(
        alias="fromVersion"
    )  # not using the base because it's required
    description: Optional[str] = None
    alerts_filter: Optional[AlertsFilter] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    marketplaces: Optional[List[MarketplaceVersions]] = None


StrictLayoutRule = create_model(
    model_name="StrictLayoutRule",
    base_models=(_StrictLayoutRule, DESCRIPTION_DYNAMIC_MODEL),
)
