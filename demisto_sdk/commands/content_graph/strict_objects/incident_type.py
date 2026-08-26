from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictGenericIncidentType,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
    SupportedFeaturesList,
    create_model,
)


class _StrictIncidentType(BaseStrictModel):
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None, alias="marketplaces"
    )
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    supportedFeatures: Optional[SupportedFeaturesList] = Field(
        None, alias="supportedFeatures"
    )


StrictIncidentType = create_model(
    model_name="StrictIncidentType",
    base_models=(_StrictIncidentType, StrictGenericIncidentType),
)
