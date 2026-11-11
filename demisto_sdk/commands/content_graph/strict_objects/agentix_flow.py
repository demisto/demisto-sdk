from typing import Any, List, Optional, Union

from pydantic import Extra, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
    SupportedFeaturesList,
)


class StrictAgentixFlow(BaseStrictModel):
    """Strict-validation model for an ``AgentixFlow`` content item.

    Unlike the other Agentix types, a flow has a top-level ``id`` and
    ``version`` and no ``commonfields`` block, so it does not inherit
    ``AgentixBase``. The remaining ``AgentixBase`` fields are redeclared here
    and must be kept in sync with it by hand. ``definition`` is passed through
    without deep validation.
    """

    class Config:
        """
        Unknown top-level fields are ignored (not forbidden), so a flow carrying
        a field not yet defined in this schema does not fail ST110.
        """

        extra = Extra.ignore

    id_: str = Field(..., alias="id")
    version: int
    supportedFeatures: Optional[SupportedFeaturesList] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None
    name: str
    description: str
    disabled: bool = False
    internal: Optional[bool] = None
    exclude_from_tightly_coupled: Optional[bool] = Field(
        None, alias="excludefromtightlycoupled"
    )
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = None
    supportedModules: Optional[List[str]] = None
    definition: Optional[Any] = None
