from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AlertsFilter,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class StrictCaseLayoutRule(BaseStrictModel):
    rule_id: str
    rule_name: str
    layout_id: str
    from_version: str = Field(alias="fromVersion")
    description: Optional[str] = None
    incidents_filter: Optional[AlertsFilter] = None
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
