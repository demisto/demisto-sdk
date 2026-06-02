from typing import List, Optional, Union

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictCollection(BaseStrictModel):
    id_: str = Field(alias="id")
    name: str
    display: str
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    description: Optional[str] = None
    marketplaces: Optional[Union[MarketplaceVersions, List[MarketplaceVersions]]] = None
    supportedModules: Optional[List[str]] = None


StrictCollection = create_model(
    model_name="StrictCollection",
    base_models=(
        _StrictCollection,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
