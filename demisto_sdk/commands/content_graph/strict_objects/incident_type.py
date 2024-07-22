from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictGenericIncidentType,
)


class StrictIncidentType(StrictGenericIncidentType):  # type:ignore[valid-type,misc]
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None, alias="marketplaces"
    )
