from typing import List, Optional

from pydantic import Extra, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionYaml,
    CommonFields,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    SupportedFeaturesList,
    create_model,
)


class _StrictKnowledge(BaseStrictModel):
    class Config:
        """
        Unknown top-level fields are ignored (not forbidden), so a knowledge item
        carrying a field not yet defined in this schema does not fail ST110.
        """

        extra = Extra.ignore

    supportedFeatures: Optional[SupportedFeaturesList] = None
    common_fields: CommonFields = Field(..., alias="commonfields")  # type:ignore[valid-type]
    name: str
    description: Optional[str] = None
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


StrictKnowledge = create_model(
    model_name="StrictKnowledge",
    base_models=(
        _StrictKnowledge,
        BaseOptionalVersionYaml,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)
